# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Builds iMIP-ready iCalendar payloads for event invitation emails.

Reuses the JSCalendar -> VEVENT conversion from Calendar Exchange so invites and the
export feature stay in sync. The only extra work here is wrapping the components in a
VCALENDAR with the right iTIP METHOD (REQUEST for invites/updates, CANCEL for removals).
"""
# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations

from datetime import UTC, datetime

from frappe.utils import cint
from icalendar import Calendar

from suite.calendar.doctype.calendar_exchange.calendar_exchange import (
    _build_components,
    _parse_local_datetime,
    jscalendar_to_vevent,
)

PRODID = "-//Frappe Mail//Calendar Invite//EN"


def build_event_ics(
    event: dict,
    method: str = "REQUEST",
    recurrence_id: str | None = None,
    attendee_email: str | None = None,
) -> str:
    """Returns the iCalendar text for a JSCalendar event using the given iTIP method.

    When `recurrence_id` is set, a single occurrence (tagged with RECURRENCE-ID) is emitted
    instead of the whole series — used to cancel one instance of a recurring event.

    Pass `attendee_email` for a REPLY: RFC 5546 requires the reply to carry exactly the
    responding ATTENDEE, so every other one is dropped from the components.
    """

    cal = Calendar()
    cal.add("prodid", PRODID)
    cal.add("version", "2.0")
    cal.add("method", method)

    if recurrence_id:
        component = _instance_component(event, recurrence_id, method)
        if attendee_email:
            _only_attendee(component, attendee_email)
        _stamp_outgoing(component, method)
        cal.add_component(component)
    else:
        for component in _build_components(event):
            if method == "CANCEL":
                _mark_cancelled(component)
            if attendee_email:
                _only_attendee(component, attendee_email)
            _stamp_outgoing(component, method)
            cal.add_component(component)

    # RFC 5545 requires a VTIMEZONE for every TZID referenced; without it a receiving client
    # can't resolve the zone and reads the wall clock in its own (e.g. a 10:00 IST meeting
    # lands at 10:00 EST in Outlook).
    cal.add_missing_timezones()

    return cal.to_ical().decode("utf-8")


def _stamp_outgoing(component, method: str) -> None:
    """Stamps an outgoing iTIP component with a send-time DTSTAMP and the right SEQUENCE.

    DTSTAMP on a scheduling message marks when the message itself was produced (now), not the
    event's last-modified time — clients use it to order re-sends. For a CANCEL we force
    SEQUENCE one past the stored value so it strictly supersedes the REQUEST it cancels; plain
    REQUESTs keep the sequence the organizer already bumped on the stored event.
    """

    if "dtstamp" in component:
        del component["dtstamp"]
    component.add("dtstamp", datetime.now(UTC))

    if method == "CANCEL":
        bumped = cint(component.get("sequence")) + 1
        if "sequence" in component:
            del component["sequence"]
        component.add("sequence", bumped)


def _instance_component(event: dict, recurrence_id: str, method: str):
    """Builds a single-occurrence VEVENT carrying RECURRENCE-ID (no RRULE/overrides)."""

    base = {k: v for k, v in event.items() if k not in ("recurrenceRule", "recurrenceOverrides")}
    # RFC 5545: an instance component's DTSTART is that occurrence's start, not the series'.
    base["start"] = recurrence_id
    component = jscalendar_to_vevent(base)

    instance_dt = _parse_local_datetime(recurrence_id, event.get("timeZone"))
    if instance_dt:
        component.add("recurrence-id", instance_dt.date() if event.get("showWithoutTime") else instance_dt)

    if method == "CANCEL":
        _mark_cancelled(component)

    return component


def _only_attendee(component, email: str) -> None:
    """Keeps only the given address's ATTENDEE property (with its params — PARTSTAT et al)."""

    attendees = component.get("attendee")
    if attendees is None:
        return
    if not isinstance(attendees, list):
        attendees = [attendees]

    email = email.lower()
    kept = [a for a in attendees if str(a).lower().replace("mailto:", "") == email]

    del component["attendee"]
    for attendee in kept:
        component.add("attendee", attendee)


def _mark_cancelled(component) -> None:
    """Forces STATUS:CANCELLED so recipients' clients remove the event on a CANCEL."""

    if "status" in component:
        del component["status"]
    component.add("status", "CANCELLED")

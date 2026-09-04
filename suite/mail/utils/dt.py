#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime as parsedate
from zoneinfo import ZoneInfo

import frappe
from frappe import _
from frappe.utils import (
    convert_utc_to_system_timezone,
    get_datetime,
    get_datetime_str,
    get_system_timezone,
)

from suite.utils.dt import convert_to_utc, parse_iso_datetime

# The one timestamp shape the mail APIs accept and return, matching what Stalwart speaks.
UTC_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def to_utc_z(value: datetime | str | None) -> str | None:
    """Formats a value as the ``2026-07-28T09:02:30Z`` UTC timestamp the mail APIs return.

    Aware values (Stalwart's timestamps, or the ``...Z`` an API was called with) are converted;
    naive ones are read as system time, which is how Frappe stores datetimes in the database.

    Distinct from ``suite.utils.dt.to_iso8601_z``, which reads a naive value as UTC — wrong for a
    value that came out of a Frappe field.
    """

    if not value:
        return None

    return convert_to_utc(value).strftime(UTC_DATETIME_FORMAT)


def from_utc_z(value: str | None) -> str | None:
    """Converts a ``...Z`` timestamp an API was called with to the system-time string Frappe stores.

    Only for values written to Frappe datetime fields; Stalwart's own fields stay in UTC.
    """

    if not value:
        return None

    return get_datetime_str(parse_iso_datetime(value, as_str=False))


def normalize_utc_z(value: datetime | str | None) -> str | None:
    """Normalizes a wire timestamp to the ``...Z`` UTC format the mail APIs speak.

    For values that are already on the wire: Stalwart's ``2026-03-23T20:03:40-05:00`` offset form,
    its ``...Z`` form, or a ``...Z`` value an API was called with. Naive values are read as UTC —
    unlike ``to_utc_z``, which reads a naive value as system time (a Frappe DB field).
    """

    if not value:
        return None

    dt = get_datetime(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    return dt.astimezone(UTC).strftime(UTC_DATETIME_FORMAT)


def to_user_timezone(value: datetime | str) -> datetime:
    """Converts a UTC wire timestamp to the session user's time zone for server-rendered text.

    Only for strings baked into content (quoted-reply headers, digests) where the browser can't
    do the conversion; API responses stay UTC. Falls back to the system time zone when the user
    hasn't set one.
    """

    dt = get_datetime(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    time_zone = None
    if frappe.session.user:
        time_zone = frappe.db.get_value("User", frappe.session.user, "time_zone")

    return dt.astimezone(ZoneInfo(time_zone or get_system_timezone()))


def parsedate_to_datetime(date_header: str) -> datetime:
    """Returns datetime object from parsed date header."""

    # email.utils.parsedate_to_datetime raises ValueError on an unparsable header rather than
    # returning None, so the guard below only works if we catch it - otherwise a malformed Date
    # on an inbound or imported message escapes as a traceback instead of this validation error.
    try:
        utc_dt = parsedate(date_header)
    except ValueError:
        utc_dt = None

    if not utc_dt:
        frappe.throw(_("Invalid date format: {0}").format(date_header))

    return convert_utc_to_system_timezone(utc_dt)

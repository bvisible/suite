import json

import frappe
from frappe import _
from mail.client.doctype.calendar.calendar import fetch_calendars
from mail.client.doctype.calendar_event.calendar_event import (
	fetch_calendar_events,
	get_master_events_by_uids,
	update_calendar_event,
)
from mail.client.doctype.calendar_event.calendar_event import (
	get_calendar_events as get_calendar_events_by_ids,
)


@frappe.whitelist()
def get_calendars(account: str) -> list[dict[str, str]]:
	"""Returns a list of the specified account's calendars."""

	calendars = fetch_calendars(account)

	return [{key: cal[key] for key in ["name", "_name"]} for cal in calendars]


@frappe.whitelist()
def get_calendar_events(account: str, from_date: str, to_date: str, time_zone: str) -> list[dict]:
	"""Fetches calendar events between from_date and to_date for the specified account."""

	events = fetch_calendar_events(
		account,
		{"after": from_date, "before": to_date},
		limit=999,
		time_zone=time_zone,
		expand_recurrences=True,
	)[0]

	uids = {event["uid"] for event in events}
	masters = get_master_events_by_uids(account, list(uids))
	master_map = {
		uid: {
			"recurrence_rule": json.loads(master["recurrence_rule"]),
			"master_id": master["id"],
			"master_start": master["start"],
			"master_duration": master["duration"],
		}
		for uid, master in masters.items()
	}

	for event in events:
		event.update(master_map.get(event["uid"], {}))

	return events


@frappe.whitelist()
def edit_calendar_event(account: str, id: str, **kwargs) -> None:
	event = get_calendar_events_by_ids(account, [id])[0]

	def resolve(key):
		return kwargs[key] if key in kwargs else event[key]

	calendar_ids = (
		kwargs["calendar_ids"]
		if "calendar_ids" in kwargs
		else [calendar["calendar_id"] for calendar in event["calendars"]]
	)

	update_calendar_event(
		account,
		id,
		event["uid"],
		event["organizer"],
		calendar_ids,
		resolve("status"),
		resolve("draft"),
		resolve("title"),
		resolve("start"),
		resolve("duration"),
		resolve("time_zone"),
		json.loads(resolve("recurrence_rule")),
		resolve("show_without_time"),
		resolve("privacy"),
		resolve("free_busy_status"),
		resolve("description"),
		resolve("locations"),
		resolve("links"),
		resolve("participants"),
		resolve("alerts"),
		resolve("use_default_alerts"),
		kwargs.get("send_scheduling_messages", False),
	)

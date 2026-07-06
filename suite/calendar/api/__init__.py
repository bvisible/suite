from __future__ import annotations
import json

import frappe
from frappe import _

from suite.mail.doctype.calendar.calendar import fetch_calendars
from suite.mail.doctype.calendar_event.calendar_event import (
	fetch_calendar_events,
	get_master_events_by_uids,
	update_calendar_event,
)
from suite.mail.doctype.calendar_event.calendar_event import (
	get_calendar_events as get_calendar_events_by_ids,
)


@frappe.whitelist()
def get_calendars(account: str) -> list[dict]:
	"""Returns the account's calendars with the display + permission info the UI
	needs to render swatches, toggles and the manage/share actions.

	//// Neoffice: upstream returned only {name, _name}, so the SPA sidebar had
	no colour, no visibility flag and no way to know if the user may manage or
	share a calendar. fetch_calendars already builds all of this via
	format_calendar — just surface the useful subset (and raise the page limit
	so every calendar is returned, not the first 10). ////
	"""

	fields = (
		"name",
		"_name",
		"id",
		"color",
		"description",
		"visible",
		"default",
		"subscribed",
		"share_with",
		"may_admin",
		"may_write_all",
		"may_delete",
	)
	calendars = fetch_calendars(account, limit=100)
	return [{key: cal.get(key) for key in fields} for cal in calendars]


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

	enrich_events_with_master_data(account, events)
	enrich_participants_with_avatars(events)

	return events


def enrich_events_with_master_data(account: str, events: list[dict]) -> None:
	"""Attaches recurrence/master info to each event in-place."""

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


def enrich_participants_with_avatars(events: list[dict]) -> None:
	"""Attaches user_image to each participant in-place."""
	unique_emails = list(
		dict.fromkeys(
			participant["email"]
			for event in events
			for participant in event["participants"]
			if participant.get("email")
		)
	)
	if not unique_emails:
		return

	user_data = frappe.db.get_all(
		"User", filters={"name": ["in", list(unique_emails)]}, fields=["name", "user_image"]
	)
	user_images = {u.name: u.user_image for u in user_data if u.user_image}
	avatar_map = {email: user_images.get(email) or get_avatar_url(email) for email in unique_emails}

	for event in events:
		for participant in event["participants"]:
			email = participant.get("email")
			if email in avatar_map:
				participant["user_image"] = avatar_map[email]


def get_avatar_url(email: str) -> str:
	"""Returns the avatar URL for the given email."""

	return f"/api/method/suite.mail.api.mail.get_avatar?email={email}"


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

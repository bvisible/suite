# //// Neoffice — added file (no upstream equivalent): the dates of the ERP, shown in the calendar as calendars of
# //// their own, read-only (maintenance#1428).
# ////
# //// Why: the calendar showed only its own events, so a task with a due date, a reminder, a booking or a leave
# //// lived somewhere else, or nowhere. They are not events and are not copied into the calendar: nothing to keep in
# //// step (a task done, moved or reassigned is right at the next look), the rights of the person apply as they are,
# //// and it works with a mail server (Stalwart) and without one (the calendar kept in Neoffice, local.py).
# ////
# //// How: an app puts a small provider behind the `suite_calendar_sources` hook (a module, below). The two calls the
# //// screen makes add what it says: `get_calendars` the sources as calendars (id `erp:<source>`, `virtual`,
# //// `read_only`, switched by the person), `get_calendar_events` the entries of the sources that are on, in the
# //// shape of an event. Suite does not know what a task is; the app does. Nothing here touches the mail server.
# ////
# //// The provider's module offers (user is always the person reading, entries are read with their rights):
# ////   calendar_sources(user)  -> [{id, title, palette, icon, enabled, scoped, description?}]
# ////   calendar_scope(user)    -> "mine" | "all"
# ////   calendar_entries(user, source, start, end, scope) -> [{id, title, start, end, all_day, doctype, name,
# ////                              route, status?, late?, meta?}]   (start, end: the site's wall clock; a day entry
# ////                              gives its first and its LAST day, both included)
# ////   set_calendar_source_enabled(user, source, enabled)
# ////   set_calendar_scope(user, scope)
# //// Remove this file with the hook once the calendar of the base desk is gone for good and nothing else uses it.
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import frappe
from frappe import _
from frappe.utils import cint, get_system_timezone, now_datetime

HOOK = "suite_calendar_sources"
PREFIX = "erp:"
SCOPES = ("mine", "all")

# A source shows at most this many entries in one period: a month of invoices must not weigh on the screen.
MAX_PER_SOURCE = 300
# An entry with an hour and no end is a hand's width, not a point.
DEFAULT_MINUTES = 30
# A failing source says so once in a while, not at every look at the calendar.
FAILURE_KEY = "suite_calendar_source_failed:{0}"
FAILURE_SILENCE = 600


def is_virtual(calendar_id: str | None) -> bool:
    return str(calendar_id or "").startswith(PREFIX)


def _providers() -> list:
    providers = []
    for path in frappe.get_hooks(HOOK) or []:
        try:
            providers.append(frappe.get_module(path))
        except Exception:
            frappe.log_error(
                "Calendar sources: a provider cannot be loaded", f"{path}\n{frappe.get_traceback()}"
            )
    return providers


def applies_to(account: str | None) -> bool:
    """Only a desk user's own calendar account gets them: the local account, or the personal mail account. Not
    another person's account that a System Manager may open, not a shared one, never a portal user."""

    user = frappe.session.user
    if not account or not user or user == "Guest":
        return False
    if frappe.db.get_value("User", user, "user_type") != "System User":
        return False

    from suite.calendar.local import is_local_account

    if is_local_account(account):
        return frappe.db.get_value("Local Calendar Account", account, "user") == user
    try:
        from suite.mail.doctype.user_account.user_account import get_user_personal_jmap_account

        return get_user_personal_jmap_account(user) == account
    except Exception:
        return False


def _require_own(account: str) -> None:
    if not applies_to(account):
        frappe.throw(_("Not permitted"), frappe.PermissionError)


def _sources(provider, user: str) -> list[dict]:
    try:
        return list(provider.calendar_sources(user) or [])
    except Exception:
        _failed("sources", "Calendar sources: a provider cannot list its sources")
        return []


def _failed(source: str, title: str) -> None:
    """A source that fails costs its own entries, never the calendar. Said once in a while, with the cause."""
    key = FAILURE_KEY.format(source)
    if frappe.cache.get_value(key):
        return
    frappe.cache.set_value(key, 1, expires_in_sec=FAILURE_SILENCE)
    frappe.log_error(title, f"source={source}\n{frappe.get_traceback()}")


def virtual_calendars(account: str) -> list[dict]:
    """The sources as calendars, in the shape `get_calendars` gives the screen."""
    if not applies_to(account):
        return []

    user = frappe.session.user
    calendars = []
    for provider in _providers():
        scope = _scope(provider, user)
        for source in _sources(provider, user):
            calendars.append(
                {
                    "name": f"{account}|{PREFIX}{source['id']}",
                    "_name": source.get("title") or source["id"],
                    "id": f"{PREFIX}{source['id']}",
                    "color": None,
                    "description": source.get("description") or "",
                    "visible": 1 if source.get("enabled") else 0,
                    "default": 0,
                    "subscribed": 1,
                    "share_with": [],
                    "may_admin": 0,
                    "may_write_all": 0,
                    "may_delete": 0,
                    # What the screen reads to treat them apart from the person's own calendars.
                    "virtual": 1,
                    "read_only": 1,
                    "palette": source.get("palette") or "",
                    "icon": source.get("icon") or "",
                    "scoped": 1 if source.get("scoped") else 0,
                    "scope": scope,
                }
            )
    return calendars


def _scope(provider, user: str) -> str:
    try:
        scope = provider.calendar_scope(user)
    except Exception:
        _failed("scope", "Calendar sources: a provider cannot tell its scope")
        return "mine"
    return scope if scope in SCOPES else "mine"


def _window(from_date: str, to_date: str) -> tuple[datetime, datetime]:
    """The period the screen asks for (UTC) as the wall clock of the site, which is how the ERP keeps its dates."""
    zone = ZoneInfo(get_system_timezone())

    def local(value: str) -> datetime:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=ZoneInfo("UTC"))
        return moment.astimezone(zone).replace(tzinfo=None)

    return local(from_date), local(to_date)


def virtual_events(account: str, from_date: str, to_date: str) -> list[dict]:
    """The entries of the sources that are on, in the shape of the events `get_calendar_events` gives the screen."""
    if not applies_to(account):
        return []

    user = frappe.session.user
    start, end = _window(from_date, to_date)
    zone = get_system_timezone()
    events = []
    for provider in _providers():
        scope = _scope(provider, user)
        for source in _sources(provider, user):
            if not source.get("enabled"):
                continue
            try:
                entries = list(provider.calendar_entries(user, source["id"], start, end, scope) or [])
            except Exception:
                _failed(source["id"], f"Calendar sources: {source['id']} cannot be read"[:140])
                continue
            events.extend(_event(account, source, entry, zone) for entry in entries[:MAX_PER_SOURCE])
    return events


def _event(account: str, source: dict, entry: dict, zone: str) -> dict:
    calendar_id = f"{PREFIX}{source['id']}"
    # "|" separates an account from an id in a name; nothing else is special in an id.
    event_id = f"{calendar_id}:{str(entry['id']).replace('|', '¦')}"
    start, duration, all_day = _timing(entry)
    moment = now_datetime().strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "name": f"{account}|{event_id}",
        "account": account,
        "id": event_id,
        "uid": event_id,
        "recurrence_id": None,
        "organizer": "",
        "calendars": [
            {
                "calendar": f"{account}|{calendar_id}",
                "calendar_id": calendar_id,
                "calendar_name": source.get("title") or source["id"],
                "color": None,
            }
        ],
        "status": "Confirmed",
        "draft": 0,
        "title": entry.get("title") or "",
        "start": start,
        "duration": duration,
        "time_zone": zone,
        "recurrence_id_time_zone": "",
        "recurrence_rule": "{}",
        "show_without_time": 1 if all_day else 0,
        "privacy": "",
        "free_busy_status": "",
        "description": entry.get("meta") or "",
        "locations": [],
        "links": [],
        "participants": [],
        "alerts": [],
        "use_default_alerts": 0,
        "created_utc": moment,
        "updated_utc": moment,
        "origin": False,
        "may_invite_self": 0,
        "may_invite_others": 0,
        "hide_attendees": 0,
        "creation": moment,
        "modified": moment,
        "sequence": 0,
        # What the screen reads to treat them apart: read-only, where to open the document, how it stands.
        "virtual": 1,
        "read_only": 1,
        "source": source["id"],
        "palette": source.get("palette") or "",
        "doctype": entry.get("doctype") or "",
        "docname": entry.get("name") or "",
        "route": entry.get("route") or "",
        "doc_status": entry.get("status") or "",
        "late": 1 if entry.get("late") else 0,
        "meta": entry.get("meta") or "",
    }


def _timing(entry: dict) -> tuple[str, str, bool]:
    """(wall clock start, ISO 8601 duration, whole days?) of an entry: a day entry is midnight to midnight, its end
    the midnight after its last day, the way the screen reads an all-day event."""
    all_day = bool(entry.get("all_day"))
    start = entry["start"]
    end = entry.get("end")
    if all_day:
        first = _as_date(start)
        last = max(_as_date(end), first) if end else first
        return f"{first.isoformat()}T00:00:00", f"P{(last - first).days + 1}D", True

    begin = _as_datetime(start)
    finish = _as_datetime(end) if end else begin
    if finish <= begin:
        finish = begin + timedelta(minutes=DEFAULT_MINUTES)
    return begin.strftime("%Y-%m-%dT%H:%M:%S"), _iso_duration(finish - begin), False


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)).date()


def _as_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    return datetime.fromisoformat(str(value)).replace(tzinfo=None)


def _iso_duration(delta: timedelta) -> str:
    seconds = int(delta.total_seconds())
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, seconds = divmod(rest, 60)
    out = "P"
    if days:
        out += f"{days}D"
    if hours or minutes or seconds:
        out += "T"
        if hours:
            out += f"{hours}H"
        if minutes:
            out += f"{minutes}M"
        if seconds:
            out += f"{seconds}S"
    return out if out != "P" else "PT0S"


def set_visibility(account: str, calendar_id: str, visible) -> None:
    """The switch of a source, kept by the app that provides it (the mail server knows nothing of it)."""
    _require_own(account)
    user = frappe.session.user
    source_id = str(calendar_id)[len(PREFIX) :]
    for provider in _providers():
        if any(source["id"] == source_id for source in _sources(provider, user)):
            provider.set_calendar_source_enabled(user, source_id, bool(cint(visible)))
            return
    frappe.throw(_("This calendar does not exist."))


@frappe.whitelist()
def set_calendar_scope(account: str, scope: str) -> None:
    """Whose dates the sources show: only the person's own, or everything they may read. One choice for all."""
    _require_own(account)
    if scope not in SCOPES:
        frappe.throw(_("Choose which dates to show: yours, or all of them."))
    user = frappe.session.user
    for provider in _providers():
        if hasattr(provider, "set_calendar_scope"):
            provider.set_calendar_scope(user, scope)

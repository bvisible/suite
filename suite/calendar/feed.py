# //// Neoffice — added file (no upstream equivalent): the person's agenda as an iCal address that Google,
# //// Outlook and Apple subscribe to (maintenance#1428).
# ////
# //// Why: a calendar kept in Neoffice (or in the mail server of a client who has none) cannot be reached by the
# //// calendar of a phone, and the dates of the ERP (a task, a booking, a leave) are in no mail server at all. An
# //// address that publishes what the person sees on the calendar page - their events and the sources of the ERP they
# //// switched on - lets any calendar application show it, read-only. It is the way "everything that has a date"
# //// reaches a phone without a mail server.
# ////
# //// How: one secret address per person, revocable. Its token is not stored: it is computed from the person and a
# //// version number kept in a default of their own (HMAC with the site's encryption key), so the address can be
# //// shown again at any time, and a new version makes the old address worth nothing. The address answers without a
# //// session, as the person: the same two calls the calendar page makes (get_calendars, get_calendar_events with
# //// the dates of the ERP), month after month around today, written as iCalendar.
# ////
# //// Limits, said on the screen: read-only (a change made in Google is not sent back), and the provider decides how
# //// often it reads (Google: every few hours, up to a day). Whoever holds the address reads the agenda: it is a
# //// secret, like Google's own "secret address in iCal format". Remove this file with the calendar sources hook once
# //// the mail server's CalDAV reaches every client.
from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, get_system_timezone, get_url, getdate, now_datetime
from frappe.utils.password import get_encryption_key
from icalendar import Calendar, Event, vDuration

PREF_KEY = "suite_calendar_feed"
PRODID = "-//Neoffice//Suite Calendar Feed//EN"
TOKEN = re.compile(r"[0-9a-f]{48}")
# What the address publishes: a month back to a year ahead, read in chunks (the mail server answers at most 999
# events a call).
DAYS_BEFORE = 31
DAYS_AFTER = 366
CHUNK_DAYS = 90
# A reader that polls every few minutes costs the server once in a while: what was built is kept for this long.
CACHE_SECONDS = 300
# One address is read a few times an hour by one provider; a hundred an hour is a script.
RATE_LIMIT = 100


# ───────────────────────────── the address ──────────────────────────────


def _mac(*parts: str) -> str:
    """HMAC-SHA256 with the site's encryption key, one purpose per call so that no part can stand for another."""
    message = "\x1f".join(("suite-calendar-feed", *parts)).encode()
    return hmac.new(get_encryption_key().encode(), message, hashlib.sha256).hexdigest()


def _token(user: str, version: int) -> str:
    # 64 bits to find the person among those who have an address, 128 bits of signature to prove it.
    return _mac("user", user)[:16] + _mac("signature", user, str(version))[:32]


def _state(user: str) -> dict:
    raw = frappe.db.get_value("DefaultValue", {"parent": user, "defkey": PREF_KEY}, "defvalue")
    return _read_state(raw)


def _read_state(raw) -> dict:
    try:
        data = json.loads(raw) if raw else {}
    except Exception:
        data = {}
    return {"enabled": 1 if cint(data.get("enabled")) else 0, "version": max(cint(data.get("version")), 1)}


def _save(user: str, state: dict) -> None:
    frappe.defaults.set_user_default(PREF_KEY, json.dumps(state), user=user)


def user_for(token) -> str | None:
    """The person an address belongs to, or None: a token that is not one, a person without an address, an address
    that was revoked or replaced, a person who is no longer a desk user."""
    token = str(token or "")
    if not TOKEN.fullmatch(token):
        return None
    wanted = token[:16]
    for user, raw in frappe.db.get_values("DefaultValue", {"defkey": PREF_KEY}, ["parent", "defvalue"]):
        state = _read_state(raw)
        if not state["enabled"] or not hmac.compare_digest(_mac("user", user)[:16], wanted):
            continue
        if not hmac.compare_digest(_token(user, state["version"]), token):
            return None
        if frappe.db.get_value("User", user, ["enabled", "user_type"]) != (1, "System User"):
            return None
        return user
    return None


def feed_url(user: str) -> str:
    return get_url(f"/api/method/suite.calendar.feed.calendar_feed?t={_token(user, _state(user)['version'])}")


# ───────────────────────────── the person manages it ──────────────────────────────


def _require_desk_user() -> str:
    user = frappe.session.user
    if not user or user == "Guest" or frappe.db.get_value("User", user, "user_type") != "System User":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    return user


def _answer(user: str) -> dict:
    state = _state(user)
    return {"enabled": bool(state["enabled"]), "url": feed_url(user) if state["enabled"] else ""}


@frappe.whitelist()
def get_calendar_feed() -> dict:
    """Whether the person shares their agenda, and the address when they do."""
    return _answer(_require_desk_user())


@frappe.whitelist()
def enable_calendar_feed() -> dict:
    user = _require_desk_user()
    _save(user, {**_state(user), "enabled": 1})
    return _answer(user)


@frappe.whitelist()
def regenerate_calendar_feed() -> dict:
    """A new address: the one that was given stops working, wherever it was pasted."""
    user = _require_desk_user()
    _save(user, {"enabled": 1, "version": _state(user)["version"] + 1})
    frappe.cache.delete_value(_cache_key(user))
    return _answer(user)


@frappe.whitelist()
def disable_calendar_feed() -> dict:
    user = _require_desk_user()
    _save(user, {**_state(user), "enabled": 0})
    frappe.cache.delete_value(_cache_key(user))
    return _answer(user)


# ───────────────────────────── what the address answers ──────────────────────────────


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(key="t", limit=RATE_LIMIT, seconds=3600, ip_based=False)
def calendar_feed(t: str = ""):
    """The iCalendar text of the person the address belongs to. Nothing is said of why an address is refused."""
    user = user_for(t)
    if not user:
        raise frappe.DoesNotExistError
    frappe.local.response.filename = "neoffice.ics"
    frappe.local.response.filecontent = _ics_of(user)
    frappe.local.response.content_type = "text/calendar; charset=utf-8"
    frappe.local.response.display_content_as = "inline"
    frappe.local.response.type = "download"


def _cache_key(user: str) -> str:
    return f"suite_calendar_feed:{user}"


def _ics_of(user: str) -> bytes:
    cached = frappe.cache.get_value(_cache_key(user))
    if cached:
        return cached
    built = build_ics(user)
    frappe.cache.set_value(_cache_key(user), built, expires_in_sec=CACHE_SECONDS)
    return built


def _account_of(user: str) -> str | None:
    """The person's calendar account: their mailbox's, else the one kept in Neoffice (never made here)."""
    from suite.calendar.local import get_local_account
    from suite.mail.doctype.user_account.user_account import get_user_personal_jmap_account

    try:
        personal = get_user_personal_jmap_account(user)
    except Exception:
        personal = None
    return personal or get_local_account(user, create=False)


def _as(user: str):
    """Act as the person for the two calls below, as a scheduled job reaches a mailbox as its owner: the user, and
    Suite's per-request memo of the connection emptied on the way in and out."""
    from contextlib import contextmanager

    @contextmanager
    def acting():
        memo = getattr(frappe.local, "request_cache", None)
        if memo is not None:
            memo.clear()
        previous = frappe.session.user
        frappe.set_user(user)
        try:
            yield
        finally:
            frappe.set_user(previous)
            memo = getattr(frappe.local, "request_cache", None)
            if memo is not None:
                memo.clear()

    return acting()


def _windows(today: date):
    first = today - timedelta(days=DAYS_BEFORE)
    last = today + timedelta(days=DAYS_AFTER)
    start = first
    while start < last:
        end = min(start + timedelta(days=CHUNK_DAYS), last)
        yield (
            datetime(start.year, start.month, start.day).strftime("%Y-%m-%dT%H:%M:%SZ"),
            datetime(end.year, end.month, end.day).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        start = end


def build_ics(user: str) -> bytes:
    """What the person sees on the calendar page, as iCalendar: the calendars they show, around today."""
    from suite.calendar.api import get_calendar_events, get_calendars

    account = _account_of(user)
    time_zone = frappe.db.get_value("User", user, "time_zone") or get_system_timezone()
    events, shown = [], set()
    if account:
        with _as(user):
            calendars = get_calendars(account, erp_dates=1)
            shown = {calendar["id"] for calendar in calendars if calendar.get("visible")}
            seen = set()
            for from_date, to_date in _windows(getdate()):
                for event in get_calendar_events(account, from_date, to_date, time_zone, erp_dates=1):
                    key = (event.get("id"), event.get("start"))
                    if key not in seen:
                        seen.add(key)
                        events.append(event)
    name = frappe.db.get_value("User", user, "full_name") or user
    return render_ics(events, shown, name=name, time_zone=time_zone)


# ───────────────────────────── iCalendar ──────────────────────────────

_DURATION = re.compile(r"^P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$")
_STATUS = {"confirmed": "CONFIRMED", "tentative": "TENTATIVE", "cancelled": "CANCELLED"}


def parse_duration(text) -> timedelta:
    found = _DURATION.match(str(text or ""))
    if not found:
        return timedelta(0)
    weeks, days, hours, minutes, seconds = (int(part or 0) for part in found.groups())
    return timedelta(weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds)


def render_ics(events: list[dict], shown: set[str], name: str, time_zone: str) -> bytes:
    """The events whose calendar is shown, as a feed. Pure: no database, no session (tested as such)."""
    host = frappe.utils.get_url().split("://", 1)[-1].split("/", 1)[0] or "neoffice"
    calendar = Calendar()
    calendar.add("prodid", PRODID)
    calendar.add("version", "2.0")
    calendar.add("calscale", "GREGORIAN")
    calendar.add("method", "PUBLISH")
    calendar.add("x-wr-calname", _("Agenda of {0}").format(name))
    calendar.add("x-wr-timezone", time_zone)
    # How often a reader may come back: an hour. The providers decide for themselves, and say so on the screen.
    calendar.add("refresh-interval", vDuration(timedelta(hours=1)), parameters={"VALUE": "DURATION"})
    calendar.add("x-published-ttl", vDuration(timedelta(hours=1)))
    stamp = now_datetime().astimezone(UTC)
    for event in events:
        in_shown = [c for c in event.get("calendars") or [] if c.get("calendar_id") in shown]
        if shown is not None and not in_shown:
            continue
        component = _vevent(event, in_shown, host, time_zone, stamp)
        if component is not None:
            calendar.add_component(component)
    calendar.add_missing_timezones()
    return calendar.to_ical()


def _vevent(event: dict, calendars: list[dict], host: str, default_zone: str, stamp: datetime):
    start_text = str(event.get("start") or "")
    if not start_text:
        return None
    component = Event()
    # An occurrence of a repeating event is a day of its own in a feed: the same address twice would be one event.
    uid = str(event.get("uid") or event.get("id"))
    if event.get("recurrence_id") or event.get("master_id"):
        uid = f"{uid}-{re.sub(r'[^0-9T]', '', start_text)}"
    component.add("uid", f"{uid}@{host}")
    component.add("dtstamp", stamp)

    duration = parse_duration(event.get("duration"))
    if cint(event.get("show_without_time")):
        first = date.fromisoformat(start_text[:10])
        component.add("dtstart", first)
        component.add("dtend", first + max(timedelta(days=duration.days), timedelta(days=1)))
    else:
        try:
            zone = ZoneInfo(event.get("time_zone") or default_zone)
        except Exception:  # a zone name this server does not know: the reader's own
            zone = ZoneInfo(default_zone)
        begin = datetime.fromisoformat(start_text).replace(tzinfo=zone)
        component.add("dtstart", begin)
        component.add("dtend", begin + (duration if duration > timedelta(0) else timedelta(minutes=30)))

    component.add("summary", str(event.get("title") or ""))
    lines = [line for line in (str(event.get("description") or ""), str(event.get("meta") or "")) if line]
    if cint(event.get("late")):
        lines.append(_("Late"))
    if lines:
        component.add("description", "\n".join(dict.fromkeys(lines)))
    places = [str(place.get("name") or place.get("description") or "") for place in event.get("locations") or []]
    places = [place for place in places if place]
    if places:
        component.add("location", ", ".join(places))
    if event.get("route"):
        component.add("url", get_url(str(event["route"])))
    status = _STATUS.get(str(event.get("status") or "").lower())
    if status:
        component.add("status", status)
    names = [str(c.get("calendar_name")) for c in calendars if c.get("calendar_name")]
    if names:
        component.add("categories", names)
    # The dates of the ERP do not block anybody's time; a real event does, unless it says it is free.
    if cint(event.get("virtual")) or str(event.get("free_busy_status") or "").lower() == "free":
        component.add("transp", "TRANSPARENT")
    return component

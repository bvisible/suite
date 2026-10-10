# //// Neoffice — added file (no upstream equivalent): the calendar of a desk user who has no mailbox (maintenance#1387).
# ////
# //// Upstream keeps every calendar and every event on the mail server (Stalwart), through JMAP: without a mailbox
# //// there was no calendar at all. On a site without Stalwart, and for Administrator everywhere, a desk user found
# //// « Aucun compte de calendrier pour le moment ». Here a Local Calendar Account answers the few JMAP calls of the
# //// calendar itself (Calendar/get|set, CalendarEvent/get|set|query, ParticipantIdentity/get) on objects kept in
# //// Frappe (Local Calendar, Local Calendar Event), shaped as the mail server shapes them. The JMAP services, the
# //// Calendar doctypes and the screens of the calendar run unchanged on top of it. Any other JMAP call raises
# //// NotImplementedError, so that one an upstream merge adds is seen. The plan: Obsidian, Neoffice/Suite-Adoption/15.
from __future__ import annotations

import copy
import json as jsonlib
import re
from datetime import UTC, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import frappe
from dateutil import rrule
from frappe import _
from frappe.utils import get_system_timezone

LOCAL_PREFIX = "local-"
STATE = "local"
UTC = UTC
MAX_OCCURRENCES = 2000  # occurrences unrolled for one series in one call: a rule without an end stops here
DEFAULT_COLOR = "#D68A59"
CAPABILITIES = {
    "urn:ietf:params:jmap:core": {"maxObjectsInGet": 1000, "maxObjectsInSet": 500, "maxCallsInRequest": 16},
    "urn:ietf:params:jmap:calendars": {},
}
# The owner may do everything here but answer invitations: RSVP needs a mail account.
RIGHTS = {
    "mayReadFreeBusy": True,
    "mayReadItems": True,
    "mayWriteAll": True,
    "mayWriteOwn": True,
    "mayUpdatePrivate": True,
    "mayRSVP": False,
    "mayAdmin": True,
    "mayDelete": True,
}


# --- the account ------------------------------------------------------------------------------------------------


def is_local_account(account: str | None) -> bool:
    return (
        bool(account)
        and str(account).startswith(LOCAL_PREFIX)
        and bool(frappe.db.exists("Local Calendar Account", account))
    )


def get_local_account(user: str | None = None, create: bool = True) -> str | None:
    """The local calendar account of a desk user who has no mail account, made on first use. A portal (Website)
    user gets none: the informational page stays. A user with a mail account gets none either: the mail server's
    calendar is the calendar."""

    user = user or frappe.session.user
    if not user or user == "Guest":
        return None
    if frappe.db.get_value("User", user, "user_type") != "System User":
        return None
    if frappe.db.exists("User Account", {"user": user}):
        return None

    account = frappe.db.get_value("Local Calendar Account", {"user": user})
    if account or not create:
        return account

    # Two requests of a first visit can both get here. The user's row is the lock: the second one waits for the
    # first to commit, then a locking read, which sees committed rows, finds the account the first one made.
    frappe.db.get_value("User", user, "name", for_update=True)
    if account := frappe.db.get_value("Local Calendar Account", {"user": user}, for_update=True):
        return account
    doc = frappe.get_doc({"doctype": "Local Calendar Account", "user": user})
    doc.insert(ignore_permissions=True)
    return doc.name


def mailbox_possible(user: str) -> bool:
    """Whether a mailbox can be made for this user here (Stalwart configured, a desk user with an e-mail, not
    Administrator): the calendar guard then tries that first (suite.mail.events.ensure_personal_mail_account)."""

    from suite.mail.events import _should_provision_mail

    try:
        return bool(_should_provision_mail(frappe.get_doc("User", user)))
    except Exception:
        return False


@frappe.whitelist()
def ensure_local_calendar_account() -> str | None:
    """The calendar guard's way out when no mailbox could be made: the session user's local calendar account
    (None for a portal user, or one who has a mail account)."""

    return get_local_account(frappe.session.user, create=True)


def local_account_user(
    account: str,
    allow_system_manager: bool = True,
    raise_exception: bool = False,
    ignore_permissions: bool = False,
) -> str | None:
    """The owner of a local account, under the same rules as a mail account's (get_user_for_jmap_account)."""

    from suite.utils.user import is_administrator, is_system_manager

    owner = frappe.db.get_value("Local Calendar Account", account, "user")
    if not owner:
        if raise_exception:
            frappe.throw(_("Calendar account {0} does not exist.").format(frappe.bold(account)))
        return None

    user = frappe.session.user
    if (
        user == owner
        or ignore_permissions
        or is_administrator(user)
        or (allow_system_manager and is_system_manager(user))
    ):
        return owner

    if raise_exception:
        frappe.throw(
            _("Calendar account {0} does not belong to the user {1}.").format(
                frappe.bold(account), frappe.bold(user)
            )
        )
    return None


def get_local_connection(account: str, ignore_permissions: bool = False) -> LocalJMAPConnection | None:
    """The connection for a local account (its owner checked), or None when the account is a mail account."""

    if not is_local_account(account):
        return None

    user = local_account_user(account, raise_exception=True, ignore_permissions=ignore_permissions)
    return LocalJMAPConnection(account, user)


def suggest_colleagues(text: str, limit: int = 10) -> list[dict]:
    """The participants a local calendar suggests: the site's enabled desk users whose name or e-mail matches."""

    pattern = f"%{text}%"
    users = frappe.get_all(
        "User",
        filters={"enabled": 1, "user_type": "System User", "name": ["not in", ["Administrator", "Guest"]]},
        or_filters={"full_name": ["like", pattern], "email": ["like", pattern]},
        fields=["full_name", "email", "user_image"],
        order_by="full_name asc",
        limit=limit,
    )
    return [
        {"name": user.full_name or None, "email": user.email, "user_image": user.user_image}
        for user in users
        if user.email
    ]


# --- times ------------------------------------------------------------------------------------------------------

_DURATION = re.compile(
    r"^(?P<sign>[-+])?P(?:(?P<w>\d+)W)?(?:(?P<d>\d+)D)?(?:T(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+(?:\.\d+)?)S)?)?$"
)


def parse_duration(value: str | None) -> timedelta:
    """An ISO 8601 duration as JSCalendar writes them (P1D, PT1H30M, -PT10M); zero when absent."""

    if not value:
        return timedelta(0)
    match = _DURATION.match(str(value).strip())
    if not match:
        raise ValueError(f"Not a duration: {value}")
    parts = match.groupdict()
    delta = timedelta(
        weeks=int(parts["w"] or 0),
        days=int(parts["d"] or 0),
        hours=int(parts["h"] or 0),
        minutes=int(parts["m"] or 0),
        seconds=float(parts["s"] or 0),
    )
    return -delta if parts["sign"] == "-" else delta


def zone_of(name: str | None, fallback: str | None = None) -> ZoneInfo:
    """The zone of an event; a floating one (no zone) is read in the owner's zone."""

    for candidate in (name, fallback, get_system_timezone(), "UTC"):
        if candidate:
            try:
                return ZoneInfo(candidate)
            except Exception:
                continue
    return ZoneInfo("UTC")


def parse_local(value: str, tz: ZoneInfo | None = None) -> datetime:
    """A JSCalendar LocalDateTime ("2026-10-12T09:00:00") as a naive wall-clock time. A UTC time ("…Z"), which
    the calendar sometimes writes for an end of series, is brought to the wall clock of `tz`."""

    text = str(value).strip()
    if text.endswith("Z"):
        moment = datetime.fromisoformat(text[:-1]).replace(tzinfo=UTC)
        return moment.astimezone(tz or UTC).replace(tzinfo=None)
    return datetime.fromisoformat(text).replace(tzinfo=None)


def format_local(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%S")


def to_utc(local: datetime, tz: ZoneInfo) -> datetime:
    return local.replace(tzinfo=tz).astimezone(UTC)


def parse_utc(value: str) -> datetime:
    """A JMAP UTCDate ("2026-10-12T07:00:00Z") as an aware datetime."""

    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    moment = datetime.fromisoformat(text)
    return (moment if moment.tzinfo else moment.replace(tzinfo=UTC)).astimezone(UTC)


def _naive_utc(moment: datetime | None) -> datetime | None:
    return moment.astimezone(UTC).replace(tzinfo=None) if moment else None


# --- series -----------------------------------------------------------------------------------------------------

_FREQUENCY = {
    "yearly": rrule.YEARLY,
    "monthly": rrule.MONTHLY,
    "weekly": rrule.WEEKLY,
    "daily": rrule.DAILY,
    "hourly": rrule.HOURLY,
    "minutely": rrule.MINUTELY,
    "secondly": rrule.SECONDLY,
}
_WEEKDAY = {
    "mo": rrule.MO,
    "tu": rrule.TU,
    "we": rrule.WE,
    "th": rrule.TH,
    "fr": rrule.FR,
    "sa": rrule.SA,
    "su": rrule.SU,
}
_RULE_LISTS = {
    "byMonthDay": "bymonthday",
    "byYearDay": "byyearday",
    "byWeekNo": "byweekno",
    "byHour": "byhour",
    "byMinute": "byminute",
    "bySecond": "bysecond",
    "bySetPosition": "bysetpos",
}


def rule_of(event: dict, start: datetime, tz: ZoneInfo) -> rrule.rrule:
    """The JSCalendar recurrenceRule of an event as a dateutil rule, on wall-clock times."""

    rule = event["recurrenceRule"]
    frequency = _FREQUENCY[str(rule.get("frequency") or "").lower()]
    arguments = {"dtstart": start, "interval": int(rule.get("interval") or 1)}
    if rule.get("firstDayOfWeek"):
        arguments["wkst"] = _WEEKDAY[str(rule["firstDayOfWeek"]).lower()]
    if rule.get("byDay"):
        arguments["byweekday"] = [
            _WEEKDAY[str(day["day"]).lower()](int(day["nthOfPeriod"]))
            if day.get("nthOfPeriod")
            else _WEEKDAY[str(day["day"]).lower()]
            for day in rule["byDay"]
        ]
    if rule.get("byMonth"):
        arguments["bymonth"] = [int(str(month).rstrip("L")) for month in rule["byMonth"]]
    for source, target in _RULE_LISTS.items():
        if rule.get(source):
            arguments[target] = [int(value) for value in rule[source]]
    if rule.get("count"):
        arguments["count"] = int(rule["count"])
    elif rule.get("until"):
        arguments["until"] = parse_local(rule["until"], tz)
    return rrule.rrule(frequency, **arguments)


def _recurrence_key(local_start: datetime) -> str:
    return format_local(local_start)


def instance_id(base_id: str, recurrence_id: str) -> str:
    """The id of one occurrence of a series: "<id>.<its start, digits only>"."""

    return f"{base_id}.{re.sub(r'[^0-9T]', '', recurrence_id)}"


def split_id(id: str) -> tuple[str, str | None]:
    """(the event's id, the occurrence's recurrence id or None)."""

    base, _, stamp = str(id).partition(".")
    if not stamp:
        return base, None
    try:
        return base, format_local(datetime.strptime(stamp, "%Y%m%dT%H%M%S"))
    except ValueError:
        return str(id), None


def make_instance(event: dict, recurrence_id: str, patch: dict | None) -> dict:
    """One occurrence: the series' properties, its own exception applied, without the rule and the exceptions."""

    instance = copy.deepcopy(event)
    instance.pop("recurrenceRule", None)
    instance.pop("recurrenceOverrides", None)
    for key, value in (patch or {}).items():
        if key != "excluded":
            instance[key] = value
    instance["start"] = (patch or {}).get("start") or recurrence_id
    # A series being stored has no id yet: its span is measured before it gets one (span_of).
    base_id = event.get("id") or ""
    instance["id"] = instance_id(base_id, recurrence_id)
    instance["baseEventId"] = base_id
    instance["recurrenceId"] = recurrence_id
    instance["recurrenceIdTimeZone"] = event.get("timeZone")
    return instance


def occurrences(
    event: dict, after: datetime | None, before: datetime | None, fallback_tz: str | None
) -> list[dict]:
    """The occurrences of a series that overlap [after, before) (UTC), exceptions applied and excluded ones left out.
    Without bounds, the first MAX_OCCURRENCES."""

    tz = zone_of(event.get("timeZone"), fallback_tz)
    start = parse_local(event["start"], tz)
    duration = parse_duration(event.get("duration"))
    overrides = event.get("recurrenceOverrides") or {}

    starts: list[datetime] = []
    if event.get("recurrenceRule"):
        rule = rule_of(event, start, tz)
        if after or before:
            # The wall-clock window, widened by the duration and a day each side for the zone's offset.
            low = (
                (after.astimezone(tz).replace(tzinfo=None) if after else start) - duration - timedelta(days=1)
            )
            high = (
                before.astimezone(tz).replace(tzinfo=None) if before else low + timedelta(days=3660)
            ) + timedelta(days=1)
            for moment in rule.xafter(low, inc=True):
                if moment > high or len(starts) >= MAX_OCCURRENCES:
                    break
                starts.append(moment)
        else:
            for moment in rule:
                if len(starts) >= MAX_OCCURRENCES:
                    break
                starts.append(moment)
    else:
        starts.append(start)

    keys = {_recurrence_key(moment) for moment in starts}
    # An exception for a time the rule does not give is an added occurrence.
    keys |= {key for key, patch in overrides.items() if not (patch or {}).get("excluded")}

    result = []
    for key in sorted(keys):
        patch = overrides.get(key)
        if (patch or {}).get("excluded"):
            continue
        instance = make_instance(event, key, patch)
        instance_tz = zone_of(instance.get("timeZone"), fallback_tz)
        begins = to_utc(parse_local(instance["start"], instance_tz), instance_tz)
        ends = begins + parse_duration(instance.get("duration"))
        if (after and ends <= after) or (before and begins >= before):
            continue
        instance["_start_utc"] = begins
        result.append(instance)
    return result


def span_of(event: dict, fallback_tz: str | None) -> tuple[datetime, datetime | None, int]:
    """(first start, last end or None for a series without an end, recurs) in naive UTC, for the period queries."""

    tz = zone_of(event.get("timeZone"), fallback_tz)
    start = to_utc(parse_local(event["start"], tz), tz)
    end = start + parse_duration(event.get("duration"))
    rule = event.get("recurrenceRule")
    overrides = event.get("recurrenceOverrides") or {}
    if not rule and not overrides:
        return _naive_utc(start), _naive_utc(end), 0

    if rule and not (rule.get("count") or rule.get("until")):
        firsts = occurrences(event, None, start + timedelta(days=1), fallback_tz)
        begin = min([start] + [instance["_start_utc"] for instance in firsts])
        return _naive_utc(begin), None, 1

    instances = occurrences(event, None, None, fallback_tz)
    if not instances:
        return _naive_utc(start), _naive_utc(end), 1
    begin = min(instance["_start_utc"] for instance in instances)
    finish = max(instance["_start_utc"] + parse_duration(instance.get("duration")) for instance in instances)
    return _naive_utc(begin), _naive_utc(finish), 1


# --- the stored objects -----------------------------------------------------------------------------------------


def _loads(data) -> dict:
    if isinstance(data, dict):
        return data
    return jsonlib.loads(data or "{}")


# The mail server leaves out a map an event does not have, where the services write null: the formatter reads
# `event.get("alerts", {})` and would fail on a null.
_MAPS = {
    "alerts",
    "locations",
    "links",
    "participants",
    "recurrenceOverrides",
    "keywords",
    "categories",
    "relatedTo",
    "replyTo",
    "virtualLocations",
}


def _dumps(obj: dict) -> str:
    kept = {
        key: value
        for key, value in obj.items()
        if not key.startswith("_") and not (key in _MAPS and value is None)
    }
    return jsonlib.dumps(kept, default=str)


def apply_patch(obj: dict, patch: dict) -> dict:
    """A JMAP /set update: a property replaced, or a path inside one ("recurrenceOverrides/<id>/title") set;
    a null value at the end of a path removes that entry."""

    for key, value in patch.items():
        if "/" not in key:
            obj[key] = value
            continue
        parts = [part.replace("~1", "/").replace("~0", "~") for part in key.split("/")]
        target = obj
        for part in parts[:-1]:
            if not isinstance(target.get(part), dict):
                target[part] = {}
            target = target[part]
        if value is None:
            target.pop(parts[-1], None)
        else:
            target[parts[-1]] = value
    return obj


# --- the connection ---------------------------------------------------------------------------------------------


class LocalJMAPConnection:
    """What the calendar's JMAP services ask of a connection, answered on Frappe records (see the top of the file)."""

    def __init__(self, account: str, user: str) -> None:
        self.account = account
        self.user = user
        self.capabilities = CAPABILITIES
        self.api_url = "local"
        self.state = STATE
        self.accounts = {
            account: {
                "name": user,
                "isPersonal": True,
                "isReadOnly": False,
                "accountCapabilities": {capability: {} for capability in CAPABILITIES},
            }
        }
        self.primary_accounts = {capability: account for capability in CAPABILITIES}

    @property
    def time_zone(self) -> str:
        return frappe.db.get_value("User", self.user, "time_zone") or get_system_timezone()

    def _session_discovery(self) -> None:
        """Nothing to discover: the session never changes."""

    def request(self, method=None, url=None, headers=None, json=None, return_json=True, **kwargs) -> dict:
        responses = []
        for name, arguments, call_id in (json or {}).get("methodCalls") or []:
            handler = HANDLERS.get(name)
            if handler is None:
                raise NotImplementedError(_("{0} needs a mail account.").format(name))
            responses.append([name, handler(self, arguments or {}), call_id])
        return {"methodResponses": responses, "sessionState": STATE}

    # calendars

    def calendar_rows(self, locking: bool = False) -> list:
        return frappe.db.get_values(
            "Local Calendar",
            {"account": self.account},
            ["name", "data"],
            as_dict=True,
            order_by="creation asc",
            for_update=locking,
        )

    def calendars(self) -> list[dict]:
        rows = self.calendar_rows()
        if not rows:
            # The screen asks for the calendars from several places at once, so two requests of a first visit can
            # both find none (two default calendars on the hub, 10.10). The account's row is the lock: the second
            # one waits for the first to commit, and its locking read sees the calendar the first one made.
            frappe.db.get_value("Local Calendar Account", self.account, "name", for_update=True)
            rows = self.calendar_rows(locking=True)
        if not rows:
            self.insert_calendar(
                {
                    "name": _("Calendar"),
                    "description": "",
                    "color": DEFAULT_COLOR,
                    "sortOrder": 0,
                    "isDefault": True,
                    "isSubscribed": True,
                    "isVisible": True,
                    "includeInAvailability": "all",
                    "timeZone": self.time_zone,
                }
            )
            rows = self.calendar_rows()
        return [{**_loads(row.data), "id": row.name, "shareWith": None, "myRights": RIGHTS} for row in rows]

    def insert_calendar(self, obj: dict) -> str:
        doc = frappe.get_doc({"doctype": "Local Calendar", "account": self.account})
        doc.data = _dumps({**obj, "shareWith": None})
        doc.insert(ignore_permissions=True)
        return doc.name

    def save_calendar(self, id: str, obj: dict) -> None:
        kept = {key: value for key, value in obj.items() if key != "myRights"}
        frappe.db.set_value(
            "Local Calendar", id, "data", _dumps({**kept, "id": id, "shareWith": None}), update_modified=True
        )

    def set_only_default(self, id: str) -> None:
        for calendar in self.calendars():
            want = calendar["id"] == id
            if bool(calendar.get("isDefault")) != want:
                calendar["isDefault"] = want
                self.save_calendar(calendar["id"], calendar)

    # events

    def event_row(self, id: str):
        return frappe.db.get_value(
            "Local Calendar Event", {"name": id, "account": self.account}, ["name", "data"], as_dict=True
        )

    def event(self, id: str) -> dict | None:
        row = self.event_row(id)
        return {**_loads(row.data), "id": row.name} if row else None

    def store_event(self, obj: dict, id: str | None = None) -> str:
        begin, finish, recurs = span_of(obj, self.time_zone)
        values = {"uid": obj.get("uid"), "range_start": begin, "range_end": finish, "recurs": recurs}
        if id:
            frappe.db.set_value(
                "Local Calendar Event",
                id,
                {**values, "data": _dumps({**obj, "id": id})},
                update_modified=True,
            )
            return id
        doc = frappe.get_doc({"doctype": "Local Calendar Event", "account": self.account, **values})
        doc.data = "{}"
        doc.insert(ignore_permissions=True)
        frappe.db.set_value("Local Calendar Event", doc.name, "data", _dumps({**obj, "id": doc.name}))
        return doc.name


# --- the JMAP methods it answers --------------------------------------------------------------------------------


def _project(obj: dict, properties: list[str] | None) -> dict:
    clean = {key: value for key, value in obj.items() if not key.startswith("_")}
    if not properties:
        return clean
    return {key: clean.get(key) for key in {*properties, "id"}}


def calendar_get(connection: LocalJMAPConnection, arguments: dict) -> dict:
    calendars = connection.calendars()
    ids = arguments.get("ids")
    found = calendars if ids is None else [calendar for calendar in calendars if calendar["id"] in ids]
    not_found = [] if ids is None else [id for id in ids if id not in {c["id"] for c in calendars}]
    return {
        "accountId": connection.account,
        "state": STATE,
        "list": [_project(calendar, arguments.get("properties")) for calendar in found],
        "notFound": not_found,
    }


def _resolve_creation_reference(value, created: dict):
    """`onSuccessSetIsDefault: "#<creation id>"` names a calendar created in the same call."""

    if isinstance(value, str) and value.startswith("#"):
        return (created.get(value[1:]) or {}).get("id")
    return value


def calendar_set(connection: LocalJMAPConnection, arguments: dict) -> dict:
    result = {
        "accountId": connection.account,
        "oldState": STATE,
        "newState": STATE,
        "created": {},
        "notCreated": {},
        "updated": {},
        "notUpdated": {},
        "destroyed": [],
        "notDestroyed": {},
    }
    known = {calendar["id"]: calendar for calendar in connection.calendars()}

    for creation_id, obj in (arguments.get("create") or {}).items():
        if obj.get("shareWith"):
            result["notCreated"][creation_id] = {
                "type": "forbidden",
                "description": _("Sharing needs a mail account."),
            }
            continue
        calendar = {
            "description": "",
            "color": DEFAULT_COLOR,
            "sortOrder": 0,
            "isSubscribed": True,
            "isVisible": True,
            "includeInAvailability": "all",
            "timeZone": connection.time_zone,
            **obj,
            "isDefault": False,
        }
        result["created"][creation_id] = {"id": connection.insert_calendar(calendar)}

    for id, patch in (arguments.get("update") or {}).items():
        if id not in known:
            result["notUpdated"][id] = {"type": "notFound"}
            continue
        if patch.get("shareWith") or any(key.startswith("shareWith/") for key in patch):
            result["notUpdated"][id] = {
                "type": "forbidden",
                "description": _("Sharing needs a mail account."),
            }
            continue
        calendar = apply_patch(
            dict(known[id]), {key: value for key, value in patch.items() if key != "myRights"}
        )
        connection.save_calendar(id, calendar)
        if patch.get("isDefault"):
            connection.set_only_default(id)
        result["updated"][id] = None

    for id in arguments.get("destroy") or []:
        calendar = known.get(id)
        if not calendar:
            result["notDestroyed"][id] = {"type": "notFound"}
            continue
        if calendar.get("isDefault"):
            result["notDestroyed"][id] = {
                "type": "forbidden",
                "description": _("The default calendar stays."),
            }
            continue
        _remove_calendar_from_events(connection, id, bool(arguments.get("onDestroyRemoveEvents")))
        frappe.delete_doc("Local Calendar", id, ignore_permissions=True, force=True)
        result["destroyed"].append(id)

    if default := _resolve_creation_reference(arguments.get("onSuccessSetIsDefault"), result["created"]):
        connection.set_only_default(default)

    return result


def _remove_calendar_from_events(
    connection: LocalJMAPConnection, calendar_id: str, remove_events: bool
) -> None:
    default = next((c["id"] for c in connection.calendars() if c.get("isDefault")), None)
    for row in frappe.get_all(
        "Local Calendar Event", filters={"account": connection.account}, fields=["name", "data"]
    ):
        event = {**_loads(row.data), "id": row.name}
        calendar_ids = dict(event.get("calendarIds") or {})
        if calendar_id not in calendar_ids:
            continue
        calendar_ids.pop(calendar_id, None)
        if not calendar_ids:
            if remove_events:
                frappe.delete_doc("Local Calendar Event", row.name, ignore_permissions=True, force=True)
                continue
            calendar_ids = {default: True} if default else {}
        event["calendarIds"] = calendar_ids
        connection.store_event(event, row.name)


def participant_identity_get(connection: LocalJMAPConnection, arguments: dict) -> dict:
    user = frappe.db.get_value("User", connection.user, ["full_name", "email"], as_dict=True) or {}
    identity = {
        "id": "local",
        "name": user.get("full_name") or connection.user,
        "calendarAddress": f"mailto:{(user.get('email') or connection.user).lower()}",
        "isDefault": True,
    }
    return {"accountId": connection.account, "state": STATE, "list": [identity], "notFound": []}


def event_get(connection: LocalJMAPConnection, arguments: dict) -> dict:
    ids = arguments.get("ids")
    if ids is None:
        ids = frappe.get_all("Local Calendar Event", filters={"account": connection.account}, pluck="name")

    found, not_found = [], []
    for id in ids:
        base_id, recurrence_id = split_id(id)
        event = connection.event(base_id)
        if not event:
            not_found.append(id)
            continue
        if recurrence_id:
            patch = (event.get("recurrenceOverrides") or {}).get(recurrence_id)
            if (patch or {}).get("excluded"):
                not_found.append(id)
                continue
            event = make_instance(event, recurrence_id, patch)
        found.append(_project(event, arguments.get("properties")))
    return {"accountId": connection.account, "state": STATE, "list": found, "notFound": not_found}


def _matches(event: dict, condition: dict | None) -> bool:
    """A JMAP FilterOperator / FilterCondition, the time bounds left to the query itself."""

    if not condition:
        return True
    if "operator" in condition:
        results = [_matches(event, sub) for sub in condition.get("conditions") or []]
        operator = str(condition["operator"]).upper()
        if operator == "OR":
            return any(results)
        if operator == "NOT":
            return not any(results)
        return all(results)
    if (calendar := condition.get("inCalendar")) and calendar not in (event.get("calendarIds") or {}):
        return False
    if (uid := condition.get("uid")) and event.get("uid") != uid:
        return False
    for key in ("title", "description"):
        if (needle := condition.get(key)) and str(needle).lower() not in str(event.get(key) or "").lower():
            return False
    if needle := condition.get("text"):
        haystack = " ".join(str(event.get(key) or "") for key in ("title", "description")).lower()
        if str(needle).lower() not in haystack:
            return False
    return True


def _bounds(condition: dict | None) -> tuple[datetime | None, datetime | None]:
    """The after/before of a filter (at its top or in an AND)."""

    if not condition:
        return None, None
    if "operator" in condition:
        if str(condition["operator"]).upper() != "AND":
            return None, None
        after = before = None
        for sub in condition.get("conditions") or []:
            sub_after, sub_before = _bounds(sub)
            after = sub_after or after
            before = sub_before or before
        return after, before
    after = parse_utc(condition["after"]) if condition.get("after") else None
    before = parse_utc(condition["before"]) if condition.get("before") else None
    return after, before


def event_query(connection: LocalJMAPConnection, arguments: dict) -> dict:
    condition = arguments.get("filter") or {}
    after, before = _bounds(condition)
    expand = bool(arguments.get("expandRecurrences"))
    fallback = arguments.get("timeZone") or connection.time_zone

    filters = [["account", "=", connection.account]]
    if before:
        filters.append(["range_start", "<", _naive_utc(before)])
    rows = frappe.get_all("Local Calendar Event", filters=filters, fields=["name", "data", "range_end"])

    hits: list[tuple[datetime, str]] = []
    for row in rows:
        if after and row.range_end and row.range_end <= _naive_utc(after):
            continue
        event = {**_loads(row.data), "id": row.name}
        if event.get("recurrenceRule") or event.get("recurrenceOverrides"):
            instances = occurrences(event, after, before, fallback)
            if expand:
                hits.extend(
                    (instance["_start_utc"], instance["id"])
                    for instance in instances
                    if _matches(instance, condition)
                )
            elif instances and _matches(event, condition):
                hits.append((instances[0]["_start_utc"], event["id"]))
            continue
        tz = zone_of(event.get("timeZone"), fallback)
        begins = to_utc(parse_local(event["start"], tz), tz)
        ends = begins + parse_duration(event.get("duration"))
        if (after and ends <= after) or (before and begins >= before):
            continue
        if _matches(event, condition):
            hits.append((begins, event["id"]))

    sort = (arguments.get("sort") or [{"property": "start", "isAscending": True}])[0]
    hits.sort(key=lambda hit: (hit[0], hit[1]), reverse=not sort.get("isAscending", True))
    position = int(arguments.get("position") or 0)
    limit = arguments.get("limit")
    ids = [id for _start, id in hits]
    window = ids[position : position + int(limit)] if limit is not None else ids[position:]
    return {
        "accountId": connection.account,
        "queryState": STATE,
        "canCalculateChanges": False,
        "position": position,
        "ids": window,
        "total": len(ids),
    }


def _with_calendar(connection: LocalJMAPConnection, event: dict) -> dict:
    """An event lives in calendars of this account: its own, or the default one."""

    known = {calendar["id"] for calendar in connection.calendars()}
    calendar_ids = {id: True for id, on in (event.get("calendarIds") or {}).items() if on and id in known}
    if not calendar_ids:
        default = next((c["id"] for c in connection.calendars() if c.get("isDefault")), None)
        calendar_ids = {default: True} if default else {}
    event["calendarIds"] = calendar_ids
    return event


def event_set(connection: LocalJMAPConnection, arguments: dict) -> dict:
    result = {
        "accountId": connection.account,
        "oldState": STATE,
        "newState": STATE,
        "created": {},
        "notCreated": {},
        "updated": {},
        "notUpdated": {},
        "destroyed": [],
        "notDestroyed": {},
    }

    for creation_id, obj in (arguments.get("create") or {}).items():
        try:
            event = _with_calendar(connection, {**obj, "sequence": int(obj.get("sequence") or 0)})
            parse_local(event["start"])
            parse_duration(event.get("duration"))
            result["created"][creation_id] = {"id": connection.store_event(event)}
        except (KeyError, ValueError, TypeError) as error:
            result["notCreated"][creation_id] = {"type": "invalidProperties", "description": str(error)}

    for id, patch in (arguments.get("update") or {}).items():
        base_id, recurrence_id = split_id(id)
        event = connection.event(base_id)
        if not event:
            result["notUpdated"][id] = {"type": "notFound"}
            continue
        if recurrence_id:  # an occurrence's own update is an exception of its series
            patch = {f"recurrenceOverrides/{recurrence_id}/{key}": value for key, value in patch.items()}
        try:
            changed = apply_patch(event, dict(patch))
            if "sequence" not in patch:
                changed["sequence"] = int(changed.get("sequence") or 0) + 1
            connection.store_event(_with_calendar(connection, changed), base_id)
            result["updated"][id] = None
        except (KeyError, ValueError, TypeError) as error:
            result["notUpdated"][id] = {"type": "invalidProperties", "description": str(error)}

    for id in arguments.get("destroy") or []:
        base_id, recurrence_id = split_id(id)
        event = connection.event(base_id)
        if not event:
            result["notDestroyed"][id] = {"type": "notFound"}
            continue
        if recurrence_id:
            connection.store_event(
                apply_patch(event, {f"recurrenceOverrides/{recurrence_id}": {"excluded": True}}), base_id
            )
        else:
            frappe.delete_doc("Local Calendar Event", base_id, ignore_permissions=True, force=True)
        result["destroyed"].append(id)

    return result


# --- alerts -----------------------------------------------------------------------------------------------------

# The mail server pushes an alert when it falls due (a CalendarAlert) and send_event_alert_notification shows it: the
# socket of an open tab, then the device. A calendar kept here has no server to push it: every minute,
# deliver_due_alerts (hooks.py) finds the alerts that fell due since the run before and hands each one, once, to that
# same sender.
ALERT_HORIZON = timedelta(days=8)  # how long before its event an alert may ring and still be found
ALERT_GRACE = timedelta(minutes=2)  # a run that comes late still delivers what fell due before it


def alerts_of(event: dict, calendars: dict[str, dict]) -> dict:
    """The event's own alerts, or its calendar's defaults when it uses them."""

    if not event.get("useDefaultAlerts"):
        return event.get("alerts") or {}
    key = "defaultAlertsWithoutTime" if event.get("showWithoutTime") else "defaultAlertsWithTime"
    for calendar_id in event.get("calendarIds") or {}:
        if defaults := (calendars.get(calendar_id) or {}).get(key):
            return defaults
    return {}


def may_ring(event: dict) -> bool:
    """Whether the event, or one of its occurrences changed alone, has alerts at all."""

    changed = [patch or {} for patch in (event.get("recurrenceOverrides") or {}).values()]
    return any(part.get("alerts") or part.get("useDefaultAlerts") for part in [event, *changed])


def due_alerts(
    event: dict, calendars: dict[str, dict], after: datetime, until: datetime, fallback_tz: str | None
) -> list[tuple[str, str | None, datetime]]:
    """(alert uid, recurrence id or None, when it rings) of each alert that rings in (after, until]: every
    occurrence by its own alerts, those of an occurrence changed alone included."""

    series = bool(event.get("recurrenceRule") or event.get("recurrenceOverrides"))
    due: dict[tuple[str, str | None, datetime], None] = {}  # in order, each once
    for instance in occurrences(event, after - ALERT_HORIZON, until + ALERT_HORIZON, fallback_tz):
        begins = instance["_start_utc"]
        for uid, alert in alerts_of(instance, calendars).items():
            trigger = (alert or {}).get("trigger") or {}
            if trigger.get("@type") == "AbsoluteTrigger":
                # One moment for the whole series: it rings once.
                rings = parse_utc(trigger["when"]) if trigger.get("when") else None
                recurrence_id = None
            else:
                from_end = str(trigger.get("relativeTo") or "start").lower() == "end"
                base = begins + parse_duration(instance.get("duration")) if from_end else begins
                rings = base + parse_duration(trigger.get("offset"))
                recurrence_id = instance["recurrenceId"] if series else None
            if rings and after < rings <= until:
                due[(uid, recurrence_id, rings)] = None
    return list(due)


def deliver_due_alerts(now: datetime | None = None) -> int:
    """Every minute: the alerts of the calendars kept here that rang since the run before, each handed once to the
    sender of the mail server's own alerts. An event that cannot be read is logged and left out, the others still
    ring. Returns how many went out."""

    from suite.calendar.doctype.calendar_event import calendar_event

    now = now or datetime.now(UTC)
    after = now - ALERT_GRACE
    rows = frappe.get_all(
        "Local Calendar Event",
        filters=[["range_start", "<=", _naive_utc(now + ALERT_HORIZON)]],
        or_filters=[["range_end", "is", "not set"], ["range_end", ">=", _naive_utc(now - ALERT_HORIZON)]],
        fields=["name", "account", "data"],
    )
    accounts: dict[str, tuple[str | None, str, dict[str, dict]]] = {}
    sent = 0
    for row in rows:
        try:
            event = {**_loads(row.data), "id": row.name}
            if not may_ring(event):
                continue
            if row.account not in accounts:
                accounts[row.account] = _alert_context(row.account)
            owner, zone, calendars = accounts[row.account]
            due = due_alerts(event, calendars, after, now, zone) if owner else []
        except Exception:
            _log_unreadable_event(row.name)
            continue
        for uid, recurrence_id, rings in due:
            # The moment is part of what rang: an event put off after its reminder rings again at its new time.
            key = f"local-calendar-alert|{row.name}|{recurrence_id or ''}|{uid}|{rings:%Y%m%dT%H%M%S}"
            if frappe.cache.get_value(key):
                continue
            frappe.cache.set_value(key, 1, expires_in_sec=3 * 24 * 60 * 60)
            calendar_event.send_event_alert_notification(
                owner, {"accountId": row.account, "calendarEventId": row.name, "recurrenceId": recurrence_id}
            )
            sent += 1
    return sent


def _alert_context(account: str) -> tuple[str | None, str, dict[str, dict]]:
    """The account's user, the zone their events are read in, and their calendars (whose default alerts apply)."""

    owner = frappe.db.get_value("Local Calendar Account", account, "user")
    zone = (owner and frappe.db.get_value("User", owner, "time_zone")) or get_system_timezone()
    calendars = {
        calendar.name: _loads(calendar.data)
        for calendar in frappe.get_all(
            "Local Calendar", filters={"account": account}, fields=["name", "data"]
        )
    }
    return owner, zone, calendars


def _log_unreadable_event(name: str) -> None:
    """Once a day per event: a broken one would otherwise write an error every minute."""

    flag = f"local-calendar-alert-error|{name}"
    if frappe.cache.get_value(flag):
        return
    frappe.cache.set_value(flag, 1, expires_in_sec=24 * 60 * 60)
    frappe.log_error("Local calendar alert skipped an unreadable event", f"{name}\n{frappe.get_traceback()}")


HANDLERS = {
    "Calendar/get": calendar_get,
    "Calendar/set": calendar_set,
    "CalendarEvent/get": event_get,
    "CalendarEvent/set": event_set,
    "CalendarEvent/query": event_query,
    "ParticipantIdentity/get": participant_identity_get,
}

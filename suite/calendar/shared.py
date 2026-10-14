# //// Neoffice — added file (no upstream equivalent): the calendars other people shared with the person, seen in
# //// the person's own calendar like the ones they made, with a mark that says they are shared (maintenance#1579).
# ////
# //// Upstream shows ONE mail account at a time: a calendar that a colleague shared lives in the colleague's
# //// account, so the person saw it only by switching accounts. Here the calendar page and Neodesk ask for the
# //// calendars and the events of the person's other accounts too (`shared=1`), and an object of another account is
# //// handed out under an id that names its account, « <account>~<id> »: ids are only unique inside an account
# //// (two accounts both have a calendar `c`). The endpoints that take such an id (an event, a calendar) go
# //// through `resolves_shared`, which makes the call on that account with the plain ids. The server's own
# //// rights apply as for any call on that account: nothing here grants anything.
from __future__ import annotations

import functools
import inspect

import frappe
from frappe import _

SEPARATOR = "~"

# What the person's other accounts add to a calendar's fields, so that a screen can tell and draw it.
FIELDS = (
    "name",
    "_name",
    "id",
    "color",
    "description",
    "visible",
    "default",
    "subscribed",
    "may_admin",
    "may_write_all",
    "may_delete",
    "may_read_items",
)


def compose(account: str, object_id: str) -> str:
    """The id of an object of another account, as the screens handle it."""

    return f"{account}{SEPARATOR}{object_id}"


def split_id(value) -> tuple[str | None, str]:
    """(account, plain id) of a composed id, (None, value) of a plain one."""

    if isinstance(value, str) and SEPARATOR in value:
        account, _separator, rest = value.partition(SEPARATOR)
        if account and rest:
            return account, rest
    return None, value


def other_accounts(account: str) -> list[str]:
    """The mail accounts of the session user other than `account`: where a calendar may have been shared with
    them. None for a calendar kept in Neoffice (nobody shares those), nor for an account that is not theirs."""

    from suite.calendar.local import is_local_account
    from suite.mail.doctype.user_account.user_account import get_user_jmap_accounts

    if not account or is_local_account(account):
        return []

    accounts = get_user_jmap_accounts(frappe.session.user)
    if account not in accounts:
        return []
    return [other for other in accounts if other != account and not is_local_account(other)]


def owner_label(account: str) -> str:
    """Who an account belongs to, for a person who reads a calendar of it: the name of its user, else its address."""

    me = frappe.session.user
    owners = frappe.db.get_all("User Account", {"account": account, "user": ["!=", me]}, pluck="user")
    if owners:
        name = frappe.db.get_value("User", owners[0], "full_name")
        if name:
            return name
    return frappe.db.get_value("JMAP Account", account, "_name") or account


def shared_calendars(account: str) -> list[dict]:
    """The calendars of the person's other accounts that they may read, as `get_calendars` lists their own."""

    from suite.calendar.doctype.calendar.calendar import fetch_calendars

    shared = []
    for other in other_accounts(account):
        try:
            calendars = fetch_calendars(other, limit=100)
        except Exception:
            # An account that no longer answers (a delegation withdrawn) costs its calendars, not the page.
            continue

        owner = owner_label(other)
        for calendar in calendars:
            if not calendar.get("may_read_items"):
                continue  # free/busy only: there is nothing of it to show
            entry = {key: calendar.get(key) for key in FIELDS}
            entry.update(
                {
                    "id": compose(other, calendar["id"]),
                    # Two people both have « Calendrier »: the owner says whose it is.
                    "_name": f"{calendar.get('_name')} ({owner})",
                    "raw_name": calendar.get("_name"),
                    # Not THEIR default: an event goes to the person's own default calendar.
                    "default": 0,
                    "share_with": [],
                    "shared_with_me": 1,
                    "owner": owner,
                    "owner_account": other,
                }
            )
            shared.append(entry)
    return shared


def shared_events(
    account: str, from_date: str, to_date: str, time_zone: str, own_uids: set[str]
) -> list[dict]:
    """The events of the person's other accounts, on the same period, under ids that name their account. An event
    the person already has in their own account (an invitation) is not shown twice: their own copy wins."""

    from suite.calendar.api import enrich_events_with_master_data
    from suite.calendar.doctype.calendar_event.calendar_event import fetch_calendar_events
    from suite.mail.utils.dt import normalize_utc_z

    shared = []
    for other in other_accounts(account):
        try:
            events = fetch_calendar_events(
                other,
                {"after": normalize_utc_z(from_date), "before": normalize_utc_z(to_date)},
                limit=999,
                time_zone=time_zone,
                expand_recurrences=True,
            )[0]
            enrich_events_with_master_data(other, events)
        except Exception:
            continue

        for event in events:
            if event.get("uid") and event["uid"] in own_uids:
                continue
            event["id"] = compose(other, event["id"])
            if event.get("master_id"):
                event["master_id"] = compose(other, event["master_id"])
            event["shared_with_me"] = 1
            shared.append(event)
    return shared


def resolves_shared(*scalars: str, lists: tuple[str, ...] = ()):
    """For an endpoint that takes ids of the objects of the account it is given. An id that names another account
    (« <account>~<id> ») makes the call on that account, with the plain ids. `scalars` are the parameters that hold
    one id, `lists` the ones that hold several. Several accounts in one call, or a plain id next to an id of
    another account, is refused: one call is one account."""

    def decorate(function):
        signature = inspect.signature(function)
        var_keyword = next(
            (p.name for p in signature.parameters.values() if p.kind is inspect.Parameter.VAR_KEYWORD), None
        )
        known = set(signature.parameters)

        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            if var_keyword is None:
                # What frappe.call does for a function that takes no **kwargs: what it does not name is dropped.
                kwargs = {key: value for key, value in kwargs.items() if key in known}
            try:
                bound = signature.bind(*args, **kwargs)
            except TypeError:
                return function(*args, **kwargs)

            values = bound.arguments
            extra = values.get(var_keyword) if var_keyword else None

            def read(name):
                if name in values and name != var_keyword:
                    return values[name]
                return extra.get(name) if isinstance(extra, dict) else None

            def write(name, value):
                if name in values and name != var_keyword:
                    values[name] = value
                elif isinstance(extra, dict) and name in extra:
                    extra[name] = value

            accounts, plain = set(), False
            for name in scalars:
                value = read(name)
                prefix, _rest = split_id(value)
                if prefix:
                    accounts.add(prefix)
                elif value:
                    plain = True
            for name in lists:
                for item in read(name) or []:
                    prefix, _rest = split_id(item)
                    if prefix:
                        accounts.add(prefix)
                    elif item:
                        plain = True

            if not accounts:
                return function(*bound.args, **bound.kwargs)
            if len(accounts) > 1 or (plain and values.get("account") not in accounts):
                frappe.throw(_("One call can only touch the calendars of one account."))

            (account,) = accounts
            for name in scalars:
                value = read(name)
                if value:
                    write(name, split_id(value)[1])
            for name in lists:
                items = read(name)
                if items:
                    write(name, [split_id(item)[1] for item in items])
            values["account"] = account
            return function(*bound.args, **bound.kwargs)

        return wrapper

    return decorate

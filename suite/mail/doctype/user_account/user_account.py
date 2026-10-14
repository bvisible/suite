# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations

from uuid import uuid7

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.caching import request_cache

from suite.utils.permissions import OwnerFromUser
from suite.utils.user import is_administrator, is_system_manager


class UserAccount(OwnerFromUser, Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        account: DF.Link
        user: DF.Link
        user_settings: DF.Link
    # end: auto-generated types

    def autoname(self) -> None:
        self.name = str(uuid7())


@request_cache
def get_user_for_jmap_account(
    account: str,
    allow_system_manager: bool = True,
    raise_exception: bool = False,
    ignore_permissions: bool = False,
) -> str | None:
    """Returns the user for the given JMAP account ID. If no user is found, it returns None. If raise_exception is True, it raises an exception if the account does not belong to any user.

    Pass ignore_permissions=True to resolve a linked user regardless of the session user's
    role — for background jobs and unauthenticated flows (e.g. Guest RSVP requests) that
    act on an account they don't own.
    """

    # //// Neoffice — a local calendar account (suite/calendar/local.py) belongs to one user, under the same
    # //// rules (maintenance#1387): the Calendar doctypes' permission checks and counts go through here.
    from suite.calendar.local import is_local_account, local_account_user

    if is_local_account(account):
        return local_account_user(account, allow_system_manager, raise_exception, ignore_permissions)

    if frappe.db.exists("JMAP Account", account):
        account_users = frappe.db.get_all("User Account", {"account": account}, pluck="user")

        if account_users:
            user = frappe.session.user

            if user in account_users:
                return user

            elif (
                ignore_permissions
                or is_administrator(user)
                or (allow_system_manager and is_system_manager(user))
            ):
                return account_users[0]

            elif raise_exception:
                frappe.throw(
                    _("JMAP account {0} does not belong to the user {1}.").format(
                        frappe.bold(account), frappe.bold(user)
                    )
                )

        elif raise_exception:
            frappe.throw(_("JMAP account {0} does not belong to any user.").format(frappe.bold(account)))

    elif raise_exception:
        frappe.throw(_("JMAP account {0} does not exist.").format(frappe.bold(account)))


@request_cache
def get_user_jmap_accounts(user: str | None = None, raise_exception: bool = False) -> list[str]:
    """Returns the list of JMAP accounts for the given user. If no user is provided, it defaults to the current session user.

    Cached per request: the returned list is shared, so callers must treat it as read-only.
    """

    user = user or frappe.session.user
    accounts = frappe.db.get_all("User Account", {"user": user}, pluck="account")

    if not accounts and raise_exception:
        frappe.throw(_("User {0} does not have any JMAP accounts configured.").format(frappe.bold(user)))

    return accounts


def is_jmap_account_belongs_to_user(
    account: str, user: str | None = None, raise_exception: bool = False
) -> bool:
    """Checks if the given JMAP account ID belongs to the specified user. If no user is provided, it defaults to the current session user."""

    user = user or frappe.session.user
    exists = bool(frappe.db.exists("User Account", {"user": user, "account": account}))

    # //// Neoffice — a local calendar account belongs to its one user (maintenance#1387): Meet attaches its
    # //// rooms to the events of such a calendar too (suite/meet/api/schedule.py).
    from suite.calendar.local import is_local_account

    if not exists and is_local_account(account):
        exists = frappe.db.get_value("Local Calendar Account", account, "user") == user

    if raise_exception and not exists:
        frappe.throw(
            _("JMAP account {0} does not belong to the user {1}.").format(
                frappe.bold(account), frappe.bold(user)
            )
        )

    return exists


# //// Neoffice — which of a user's accounts are THEIR OWN mailbox, as the mail server says it for that user
# //// (maintenance#1579). Upstream reads the flag of the shared « JMAP Account » document, written once from the
# //// session of the first user who got the account: a mailbox its owner shares with a colleague stays « personal »
# //// for the colleague too. He then has two personal accounts: the calendar and the mail open the owner's, and
# //// get_user_personal_jmap_account finds none (no dates of the ERP, no iCal address, no mail API). The session of
# //// each user says it per user (isPersonal). It is read here from the cache the JMAP layer keeps, with no call
# //// to the mail server; the document's flag stays the answer where that session does not say (cold cache, no
# //// JMAP settings, a session that names no personal account, an account it does not list). To drop when
# //// upstream keeps the flag per user.
def get_personal_accounts_of_user(user: str, accounts: list[str]) -> list[str]:
    """The accounts among `accounts` that are the user's own mailbox."""

    if not accounts:
        return []

    flags = _session_personal_flags(user)
    if flags is None:
        return frappe.db.get_all(
            "JMAP Account", {"is_personal": True, "name": ("in", accounts)}, pluck="name"
        )

    personal = {account for account in accounts if flags.get(account)}
    unlisted = [account for account in accounts if account not in flags]
    if unlisted:
        personal.update(
            frappe.db.get_all("JMAP Account", {"is_personal": True, "name": ("in", unlisted)}, pluck="name")
        )
    return [account for account in accounts if account in personal]


def _session_personal_flags(user: str) -> dict[str, bool] | None:
    """`isPersonal` of each account in the user's cached JMAP session, or None when the session is absent or
    names no personal account."""

    from suite.mail.jmap import get_jmap_session_manager

    try:
        session = get_jmap_session_manager(user).get_session()
    except Exception:
        return None

    accounts = session.get("accounts") if isinstance(session, dict) else None
    if not isinstance(accounts, dict):
        return None

    flags = {
        account: bool(details.get("isPersonal"))
        for account, details in accounts.items()
        if isinstance(details, dict)
    }
    return flags if any(flags.values()) else None


def warm_user_jmap_session(user: str) -> None:
    """Connects once as the user, so that the session the mail server holds for them is in the cache."""

    from suite.mail.jmap import get_jmap_connection

    # A refusal is for the calls that follow to say: what it puts in the message log is not wanted here.
    messages = list(frappe.local.message_log)
    try:
        get_jmap_connection(user)
    except Exception:
        frappe.local.message_log = messages


def get_user_personal_jmap_account(user: str | None = None, raise_exception: bool = False) -> str | None:
    """Returns the personal JMAP account ID for the given user. If no user is provided, it defaults to the current session user."""

    user = user or frappe.session.user
    user_accounts = get_user_jmap_accounts(user, raise_exception=raise_exception)
    # //// Neoffice — the user's own mailbox as the mail server says it for them, not the flag of the shared
    # //// document (maintenance#1579, get_personal_accounts_of_user above).
    personal_accounts = get_personal_accounts_of_user(user, user_accounts)

    if personal_accounts:
        if len(personal_accounts) > 1:
            if raise_exception:
                frappe.throw(
                    _("User {0} has multiple personal JMAP accounts configured.").format(frappe.bold(user))
                )
        else:
            return personal_accounts[0]

    elif raise_exception:
        frappe.throw(
            _("User {0} does not have a personal JMAP account configured.").format(frappe.bold(user))
        )


def on_doctype_update() -> None:
    frappe.db.add_unique("User Account", ["user", "account"], constraint_name="unique_user_account")

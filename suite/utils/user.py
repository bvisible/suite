from __future__ import annotations
import frappe
from frappe import _
from frappe.core.doctype.user.user import User, generate_keys
from frappe.utils.caching import request_cache

from suite.utils import user_context

RESERVED_USERS = ("Guest", "Administrator")


def is_administrator(user: str) -> bool:
    """Returns True if the user is Administrator else False."""

    return user == "Administrator"


@request_cache
def has_role(user: str, roles: str | list) -> bool:
    """Returns True if the user has any of the given roles else False."""

    if isinstance(roles, str):
        roles = [roles]

    user_roles = frappe.get_roles(user)
    for role in roles:
        if role in user_roles:
            return True

    return False


@request_cache
def is_system_manager(user: str) -> bool:
    """Returns True if the user is Administrator or System Manager else False."""

    return is_administrator(user) or has_role(user, "System Manager")


@request_cache
def is_suite_admin(user: str) -> bool:
    """Returns True if the user is a Suite Admin else False."""

    return has_role(user, "Suite Admin")


@request_cache
def is_suite_user(user: str) -> bool:
    """Returns True if the user is a Suite User else False."""

    return has_role(user, "Suite User")


def is_user_enabled(user: str) -> bool:
    """Returns True if the user account is enabled else False."""

    return bool(frappe.db.get_value("User", user, "enabled"))


def assign_role(user: User, role_name: str, desk_access: bool = True) -> None:
    """Append `role_name` to an in-memory User doc, creating the Role if missing.

    Meant to be called from a `before_insert` hook so the role is part of the
    document Frappe validates. Assigning roles after insert is too late for
    `User.check_roles_added` (which warns "Newly created user X has no roles
    enabled") and for `User.set_system_user` (which demotes a role-less user to
    a Website User), and it costs an extra `User.save` per role.

    When the Role does not yet exist (e.g. programmatic site setup before the
    fixture syncs) it is created with `desk_access` so it matches its fixture.
    Getting this wrong matters: `set_system_user` keys the new user's `user_type`
    off whether any assigned role has desk access, so creating a desk-access role
    without it here would silently demote the user to a Website User.
    """
    # `before_insert` runs ahead of `set_new_name`, so `user.name` is still unset
    # on a fresh User — fall back to the email it will be named after.
    identifier = user.name or user.email
    if not identifier or identifier in RESERVED_USERS:
        return

    if not frappe.db.exists("Role", role_name):
        frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": int(desk_access)}).insert(
            ignore_permissions=True
        )

    if any(row.role == role_name for row in user.get("roles") or []):
        return

    user.append("roles", {"role": role_name})


def assign_suite_role(user: User, method: str | None = None) -> None:
    """Grant the suite-wide "Suite User" role to a new User.

    Wired to the User `before_insert` hook so every new user gets suite access
    (mail, calendar, meet, ...) before Frappe validates the document — see
    `assign_role` for why assignment happens before insert.

    #//// Neoffice — `desk_access=False`, where upstream takes the default of True.
    #////
    #//// This hook fires for EVERY new User, shop signups included, and
    #//// `User.set_system_user` reads `user_type` straight off "does any assigned
    #//// role carry desk access". With upstream's default, every visitor who
    #//// creates an account on the shop becomes a System User with access to
    #//// /app. That is not hypothetical: it is what this fleet was fixed for in
    #//// e20b2ac06, and 8b911806e reintroduced the exposure by folding the
    #//// desk-less "Drive User"/"Meet User" roles into a desk-access "Suite User"
    #//// (measured 31.08.2026 on osiris: 277 of 297 portal accounts would have
    #//// been promoted).
    #////
    #//// This argument only bites when the Role does not exist yet — a fresh
    #//// install, or one of the migration patches racing the fixture sync. The
    #//// binding lock is `desk_access: 0` on "Suite User" in
    #//// suite/fixtures/role.json, which `sync_fixtures()` re-applies on every
    #//// migrate. Both must survive the next merge; neither is sufficient alone.
    #////
    #//// Removing desk access from the role costs the portal nothing: desk_access
    #//// gates /app only, never doctype permissions, so Drive, Calendar, Meet and
    #//// Mail keep working for a Website User. Staff hold desk roles of their own
    #//// (System Manager, "Suite Admin", the ERPNext roles).
    """

    assign_role(user, "Suite User", desk_access=False)


@frappe.whitelist(methods=["POST"])
def generate_user_keys(user: str) -> dict:
    """Generates API and Secret keys for the user."""

    session_user = frappe.session.user
    if is_system_manager(session_user) or session_user == user:
        with user_context("Administrator"):
            return generate_keys(user)

    frappe.throw(_("Not permitted"), frappe.PermissionError)

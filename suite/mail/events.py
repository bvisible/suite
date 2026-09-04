#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from typing import Any

import frappe
from frappe import _
from frappe.core.doctype.user.user import _get_user_for_update_password
from frappe.core.doctype.user.user import update_password as update_frappe_password
from frappe.model.document import Document

from suite.mail.stalwart import add_account_role as add_stalwart_account_role
from suite.mail.stalwart import delete_account as delete_stalwart_account
from suite.mail.stalwart import remove_account_role as remove_stalwart_account_role
from suite.mail.stalwart import update_password as update_stalwart_password
from suite.mail.utils import get_config, is_stalwart_configured
from suite.mail.utils.user import is_jmap_configured
from suite.utils import execute_with_logging


def create_user_settings(doc: Document, method: str | None = None) -> None:
    """Create User Settings for the new user if not already present."""

    if not frappe.db.exists("User Settings", {"user": doc.name}):
        settings = frappe.new_doc("User Settings")
        settings.user = doc.name
        settings.insert(ignore_permissions=True, ignore_mandatory=True)


# //// Neoffice: auto-provision a Stalwart mailbox for every new desk user, so
# Mail AND Calendar work out of the box on deploy without a manual Mail Account
# Request. Upstream only created an empty User Settings; the mailbox was never
# created automatically. Enqueued so a slow stalwart-cli never blocks user
# creation; a migration patch backfills existing users (provision_existing_mail_accounts). ////
def provision_mail_account(doc: Document, method: str | None = None) -> None:
    """after_insert(User) → auto-create the user's Stalwart mailbox (async)."""

    if not _should_provision_mail(doc):
        return

    frappe.enqueue(
        "suite.mail.events._provision_mail_account_now",
        queue="short",
        job_id=f"provision-mail-{doc.name}",
        deduplicate=True,
        enqueue_after_commit=True,
        user=doc.name,
    )


def _should_provision_mail(doc: Document) -> bool:
    """Only active desk (System User) accounts with a real e-mail, on a
    Stalwart-enabled instance, not already provisioned. Website (client) signups
    do NOT get a mailbox."""

    if doc.name in ("Guest", "Administrator") or not doc.enabled:
        return False
    if getattr(doc, "user_type", None) != "System User":
        return False
    if "@" not in (doc.email or ""):
        return False
    if not is_stalwart_configured(raise_exception=False):
        return False
    if frappe.db.get_value("User Settings", {"user": doc.name}, "username"):
        return False  # already provisioned
    return True


def _provision_mail_account_now(user: str) -> None:
    """Create the Stalwart account + app password and store the JMAP credentials
    on User Settings — the User Account / JMAP Account links then sync on save."""

    from frappe.utils import cint

    from suite.mail.stalwart import create_account, create_app_password, get_domains
    from suite.mail.utils import get_config

    user_doc = frappe.get_doc("User", user)
    if not _should_provision_mail(user_doc):
        return

    domains = [d.get("name") for d in get_domains() if d.get("name")]
    if not domains:
        return  # no mail domain configured on Stalwart yet

    local_base = user_doc.email.split("@")[0]
    domain = domains[0]
    password = frappe.generate_hash(length=20)

    # //// Neoffice: two Frappe users can share an email local-part
    # (jeremy@bvisible.ch vs jeremy@neoservice.ai; info@displaycompany vs
    # info@testcompany). The Stalwart mailbox is <local>@<domain>, so derive a
    # UNIQUE local part — suffix on collision — instead of failing silently and
    # leaving the user with no calendar. ////
    account = None
    for attempt in range(0, 30):
        cand_local = local_base if attempt == 0 else f"{local_base}{attempt + 1}"
        cand = f"{cand_local}@{domain}"
        if frappe.db.exists("User Settings", {"username": cand}):
            continue  # already taken by another user
        try:
            create_account(
                name=cand_local,
                domain=domain,
                password=password,
                description=user_doc.full_name or cand_local,
                aliases=[],
                groups=[],
                roles=["User"],
                quota=cint(get_config("default_disk_quota_gb")) * 1024**3,
                timezone=None,
            )
            account = cand
            break
        except Exception as e:
            # Stalwart-side collision not tracked in User Settings — try next suffix
            frappe.log_error("Mail auto-provision retry", f"account={cand} user={user}: {e}")
            continue

    if not account:
        frappe.log_error("Mail auto-provision failed", f"user={user}: no free username after retries")
        return

    app_password = create_app_password(account)

    if not frappe.db.exists("User Settings", {"user": user}):
        s = frappe.new_doc("User Settings")
        s.user = user
        s.insert(ignore_permissions=True, ignore_mandatory=True)

    settings = frappe.get_doc("User Settings", {"user": user})
    settings.username = account
    settings.app_password = app_password
    # save() triggers sync_jmap_accounts -> creates JMAP Account + User Account links
    settings.save(ignore_permissions=True)
    frappe.db.commit()


@frappe.whitelist()
def ensure_personal_mail_account() -> bool:
    """//// Neoffice: guarantee a desk user ALWAYS has a calendar/mailbox.
    Provision the current user's mailbox synchronously on demand if they are an
    eligible System User without one — this closes the brief async window right
    after signup and covers any user the backfill missed. Returns True if the
    user has an account afterwards (so the Calendar can proceed instead of
    showing "no account"). Website (client) users return False and keep the
    informational page. ////"""

    user = frappe.session.user
    if user in ("Guest", "Administrator"):
        return False
    if frappe.db.get_value("User Settings", {"user": user}, "username"):
        return True

    doc = frappe.get_doc("User", user)
    if not _should_provision_mail(doc):
        return False

    try:
        _provision_mail_account_now(user)
    except Exception:
        frappe.log_error("On-demand mail provision failed", f"user={user}")
        return False

    return bool(frappe.db.get_value("User Settings", {"user": user}, "username"))


@frappe.whitelist()
def provision_existing_mail_accounts() -> dict:
    """Backfill: provision a mailbox for every eligible desk user that has none.
    Idempotent — used by the migration patch and callable manually on deploy."""

    frappe.only_for("System Manager")
    provisioned, skipped = [], 0
    users = frappe.get_all(
        "User",
        filters={"enabled": 1, "user_type": "System User", "name": ["not in", ["Administrator", "Guest"]]},
        pluck="name",
    )
    for name in users:
        doc = frappe.get_doc("User", name)
        if _should_provision_mail(doc):
            try:
                _provision_mail_account_now(name)
                provisioned.append(name)
            except Exception:
                frappe.log_error("Mail auto-provision failed", f"user={name}")
        else:
            skipped += 1
    return {"provisioned": provisioned, "skipped": skipped}


def delete_user_accounts(doc: Document, method: str | None = None) -> None:
    """Delete User Accounts when the user is deleted."""

    for account in frappe.db.get_all("User Account", filters={"user": doc.name}, pluck="name"):
        frappe.delete_doc("User Account", account, ignore_permissions=True, delete_permanently=True)


def delete_user_settings(doc: Document, method: str | None = None) -> None:
    """Delete User Settings when the user is deleted."""

    for settings in frappe.db.get_all("User Settings", filters={"user": doc.name}, pluck="name"):
        frappe.delete_doc("User Settings", settings, ignore_permissions=True, delete_permanently=True)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def update_password(
    new_password: str, logout_all_sessions: int = 0, key: str | None = None, old_password: str | None = None
) -> Any:
    """Override the default update_password whitelisted method to update the password on Stalwart server when the user updates their password."""

    frappe.flags.in_update_password = True

    if not is_stalwart_configured(raise_exception=False):
        return update_frappe_password(
            new_password=new_password,
            logout_all_sessions=logout_all_sessions,
            key=key,
            old_password=old_password,
        )

    result = _get_user_for_update_password(key, old_password)
    user = result.get("user")

    result = update_frappe_password(
        new_password=new_password, logout_all_sessions=logout_all_sessions, key=key, old_password=old_password
    )

    if user and is_jmap_configured(user):
        execute_with_logging(
            lambda: update_stalwart_password(user, new_password=new_password),
            title="Failed to update password on Stalwart server",
            with_context=False,
            module="Mail",
        )

    return result


def update_account_password(doc: Document, method: str | None = None) -> None:
    """Updates the password on Stalwart server when the user updates their password."""

    if (
        frappe.flags.in_update_password
        or doc.flags.in_insert
        or not doc.enabled
        or not is_stalwart_configured(raise_exception=False)
        or not is_jmap_configured(doc.name)
    ):
        return

    user = doc.name
    new_password = doc._User__new_password

    if not new_password:
        return

    execute_with_logging(
        lambda: update_stalwart_password(user, new_password=new_password),
        title="Failed to update password on Stalwart server",
        with_context=False,
        module="Mail",
    )


def clear_sessions_on_disable(doc: Document, method: str | None = None) -> None:
    """Log the user out everywhere when they are disabled.

    Clears both the user's Frappe sessions and their cached JMAP session so a disabled user
    loses access immediately instead of continuing on an existing session until it expires.
    """

    if doc.flags.in_insert or doc.enabled or not doc.has_value_changed("enabled"):
        return

    from frappe.sessions import clear_sessions

    from suite.mail.jmap import get_jmap_session_manager

    clear_sessions(user=doc.name, force=True)
    get_jmap_session_manager(doc.name).clear_session()


def apply_disabled_account_role(doc: Document, method: str | None = None) -> None:
    """Apply the configured Stalwart role to the user's mail account when the user is disabled.

    The role is created manually on Stalwart with the desired allowed/disabled permissions, so
    applying it effectively restricts the disabled user's mail access. No-op if no role is configured.
    """

    if (
        doc.flags.in_insert
        or doc.enabled
        or not doc.has_value_changed("enabled")
        or not is_stalwart_configured(raise_exception=False)
        or not is_jmap_configured(doc.name)
    ):
        return

    role = get_config("disabled_account_role")
    if not role:
        return

    execute_with_logging(
        lambda: add_stalwart_account_role(doc.name, role),
        title="Failed to apply disabled account role on Stalwart server",
        with_context=False,
        module="Mail",
    )


def remove_disabled_account_role(doc: Document, method: str | None = None) -> None:
    """Remove the configured Stalwart disabled account role when the user is re-enabled.

    This reverses apply_disabled_account_role so the user regains their mail access on enable.
    No-op if no role is configured.
    """

    if (
        doc.flags.in_insert
        or not doc.enabled
        or not doc.has_value_changed("enabled")
        or not is_stalwart_configured(raise_exception=False)
        or not is_jmap_configured(doc.name)
    ):
        return

    role = get_config("disabled_account_role")
    if not role:
        return

    execute_with_logging(
        lambda: remove_stalwart_account_role(doc.name, role),
        title="Failed to remove disabled account role on Stalwart server",
        with_context=False,
        module="Mail",
    )


def delete_account(doc: Document, method: str | None = None) -> None:
    if not is_stalwart_configured(raise_exception=False) or not is_jmap_configured(doc.name):
        return

    user = doc.name
    execute_with_logging(
        lambda: delete_stalwart_account(user),
        title="Failed to delete account on Stalwart server",
        with_context=False,
        module="Mail",
    )

    # The cached JMAP session carries the account's ids. Left behind, a user recreated on the same
    # address would inherit the deleted account's ids and every call would be scoped to an account
    # the server no longer considers theirs.
    from suite.mail.jmap import get_jmap_session_manager

    get_jmap_session_manager(user).clear_session()

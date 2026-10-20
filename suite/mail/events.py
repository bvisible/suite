# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.core.doctype.user.user import _get_user_for_update_password
from frappe.core.doctype.user.user import update_password as update_frappe_password
from frappe.model.document import Document

from suite.mail.directory import delete_account as delete_mail_account
from suite.mail.directory import set_account_enabled
from suite.mail.directory import update_password as update_mail_password

# //// Neoffice — our own way into Stalwart's management API, for the mailbox of a new desk user: upstream's
# //// directory now goes through Suite Cloud, which a self-hosted fleet has not (suite/mail/neoffice_stalwart.py).
from suite.mail.neoffice_stalwart import is_stalwart_configured
from suite.mail.utils.user import is_jmap_configured
from suite.suite_core.utils import is_suite_cloud_configured
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

    # //// Neoffice — re-indented to spaces (was tabs); whitespace only, see 3c5320395.
    if not _should_provision_mail(doc):
        return

    # //// Neoffice — re-indented to spaces (was tabs); whitespace only.
    frappe.enqueue(
        "suite.mail.events._provision_mail_account_now",
        queue="short",
        job_id=f"provision-mail-{doc.name}",
        deduplicate=True,
        enqueue_after_commit=True,
        user=doc.name,
    )


# //// Neoffice — re-indented to spaces (was tabs); whitespace only.
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

    from suite.mail.neoffice_stalwart import create_account, create_app_password, get_domains
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

    # //// Neoffice — re-indented to spaces (was tabs); whitespace only.
    doc = frappe.get_doc("User", user)
    if not _should_provision_mail(doc):
        return False

    # //// Neoffice — re-indented to spaces (was tabs); whitespace only.
    try:
        _provision_mail_account_now(user)
    except Exception:
        frappe.log_error("On-demand mail provision failed", f"user={user}")
        return False

    # //// Neoffice — re-indented to spaces (was tabs); whitespace only.
    return bool(frappe.db.get_value("User Settings", {"user": user}, "username"))


# //// Neoffice — re-indented to spaces (was tabs); whitespace only.
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


# //// Neoffice — the mailbox of a deleted or disabled desk user on our own Stalwart (maintenance#1743): kept with its
# //// mail, nobody let in (suite/mail/neoffice_stalwart.py, lock_account); a user enabled again gets a new app
# //// password. delete_account calls lock_own_mailbox first among the User's on_trash hooks, while User Settings,
# //// which holds the mailbox's address, is still there; apply_disabled_account_role and remove_disabled_account_role
# //// call it, and unlock_own_mailbox, on a change of `enabled`. The work itself waits for the commit (Frappe may still
# //// refuse a deletion after on_trash: a linked document), and each job looks at the user again when it runs.
def lock_own_mailbox(user: str) -> None:
    """Have the mailbox of `user`, who is being deleted or disabled, locked once that is committed, and forget their
    JMAP session. A mailbox another user's settings name too (a team's) is theirs as well: it stays open."""

    if not is_stalwart_configured(raise_exception=False):
        return
    address = (frappe.db.get_value("User Settings", {"user": user}, "username") or "").strip().lower()
    if "@" not in address:
        return
    if frappe.db.exists("User Settings", {"username": address, "user": ["!=", user]}):
        frappe.log_error(
            "Mail account of a user left open",
            f"address={address}: another user's settings name it too",
        )
        return

    frappe.enqueue(
        "suite.mail.events.lock_mailbox_now",
        queue="short",
        job_id=f"lock-mail-{address}",
        deduplicate=True,
        enqueue_after_commit=True,
        address=address,
        user=user,
    )

    from suite.mail.jmap import clear_jmap_session

    clear_jmap_session(user)


def lock_mailbox_now(address: str, user: str | None = None) -> None:
    """The job lock_own_mailbox queues: lock `address`, and say so in the error log, with the address, when it could
    not be done or the server has no such account. Nothing is done for a `user` who is enabled by the time it runs
    (disabled, then enabled again before the job came)."""

    if user and frappe.db.get_value("User", user, "enabled"):
        return

    from suite.mail.neoffice_stalwart import lock_account

    try:
        locked = lock_account(address)
    except Exception:
        frappe.log_error(
            "Failed to lock the mail account of a user",
            f"address={address}\n{frappe.get_traceback()}",
        )
        return
    if not locked:
        frappe.log_error("Mail account of a user not found", f"address={address}")


def unlock_own_mailbox(user: str) -> None:
    """Have the mailbox of `user`, who is enabled again, opened to them once that is committed: a new app password,
    which the site uses for their mail. The app passwords the lock revoked stay revoked."""

    if not is_stalwart_configured(raise_exception=False):
        return
    address = (frappe.db.get_value("User Settings", {"user": user}, "username") or "").strip().lower()
    if "@" not in address:
        return
    frappe.enqueue(
        "suite.mail.events.unlock_mailbox_now",
        queue="short",
        job_id=f"unlock-mail-{address}",
        deduplicate=True,
        enqueue_after_commit=True,
        address=address,
        user=user,
    )


def unlock_mailbox_now(address: str, user: str) -> None:
    """The job unlock_own_mailbox queues: a new app password for `address`, kept in `user`'s settings, and their JMAP
    session forgotten so that the next one signs in with it. Nothing is done for a user who is gone or disabled again
    by the time it runs, or whose settings name another mailbox by then."""

    if not frappe.db.get_value("User", user, "enabled"):
        return
    name = frappe.db.get_value("User Settings", {"user": user}, "name")
    if not name:
        return
    settings = frappe.get_doc("User Settings", name)
    if (settings.username or "").strip().lower() != address:
        return

    from suite.mail.jmap import clear_jmap_session
    from suite.mail.neoffice_stalwart import create_app_password

    try:
        settings.app_password = create_app_password(address)
        settings.save(ignore_permissions=True)
    except Exception:
        frappe.log_error(
            "Failed to open the mail account of a user again",
            f"address={address}\n{frappe.get_traceback()}",
        )
        return
    clear_jmap_session(user)


@frappe.whitelist(methods=["POST"])
def lock_orphan_mailboxes(lock: int = 0) -> dict:
    """The mailboxes no existing user holds (`orphans`: no existing user is linked to their JMAP Account, and no
    user's settings name them) and those of disabled users (`disabled`) that no enabled user holds too; with `lock`,
    what became of each: locked, not found on the server, or failed (the error log says why, with the address). A
    mailbox an enabled user holds in any way is never in either list. For the mailboxes left open before
    lock_own_mailbox existed."""

    frappe.only_for("System Manager")
    configured = is_stalwart_configured(raise_exception=False)
    address = lambda value: (value or "").strip().lower()  # noqa: E731
    users = {row.name: bool(row.enabled) for row in frappe.get_all("User", fields=["name", "enabled"])}
    enabled = {name for name, on in users.items() if on}
    links = frappe.get_all("User Account", fields=["user", "account"])
    accounts = frappe.get_all("JMAP Account", fields=["name", "_name"])
    settings = frappe.get_all("User Settings", fields=["user", "username"])

    by_existing = {link.account for link in links if link.user in users}
    by_enabled = {link.account for link in links if link.user in enabled}
    held = {address(row.username) for row in settings if row.user in users and row.username}
    held |= {address(account._name) for account in accounts if account.name in by_existing}
    held_by_enabled = {address(row.username) for row in settings if row.user in enabled and row.username}
    held_by_enabled |= {address(account._name) for account in accounts if account.name in by_enabled}

    orphans = sorted(
        {
            address(account._name)
            for account in accounts
            if account.name not in by_existing and "@" in address(account._name)
        }
        - held
    )
    disabled = sorted(
        {
            address(row.username)
            for row in settings
            if row.user in users and row.user not in enabled and "@" in address(row.username)
        }
        - held_by_enabled
    )
    result: dict = {
        "configured": configured,
        "orphans": orphans,
        "disabled": disabled,
        "locked": [],
        "not_found": [],
        "failed": [],
    }
    if not frappe.utils.cint(lock) or not configured:
        return result

    from suite.mail.neoffice_stalwart import lock_account

    for target in [*orphans, *disabled]:
        try:
            locked = lock_account(target)
        except Exception:
            frappe.log_error(
                "Failed to lock an orphan mailbox", f"address={target}\n{frappe.get_traceback()}"
            )
            result["failed"].append(target)
            continue
        result["locked" if locked else "not_found"].append(target)
    return result


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

    if not is_suite_cloud_configured():
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
            lambda: update_mail_password(user, new_password=new_password),
            title="Failed to update the mail account password",
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
        or not is_suite_cloud_configured()
        or not is_jmap_configured(doc.name)
    ):
        return

    user = doc.name
    new_password = doc._User__new_password

    if not new_password:
        return

    execute_with_logging(
        lambda: update_mail_password(user, new_password=new_password),
        title="Failed to update the mail account password",
        with_context=False,
        module="Mail",
    )


def delete_push_subscriptions_on_disable(doc: Document, method: str | None = None) -> None:
    """Delete this site's push subscriptions on the mail server when the user is disabled.

    Only the subscriptions wearing the site's device client id go; the user's custom ones stay.
    Ordered ahead of apply_disabled_account_role: that role may revoke the account's access on
    Stalwart, after which the JMAP delete would be refused.
    """

    if doc.flags.in_insert or doc.enabled or not doc.has_value_changed("enabled"):
        return
    if not is_jmap_configured(doc.name):
        return

    from suite.mail.doctype.push_subscription.push_subscription import delete_site_push_subscriptions

    user = doc.name
    execute_with_logging(
        lambda: delete_site_push_subscriptions(user),
        title="Failed to delete push subscriptions on mail server",
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

    from suite.mail.jmap import clear_jmap_session

    clear_sessions(user=doc.name, force=True)
    clear_jmap_session(doc.name)


def apply_disabled_account_role(doc: Document, method: str | None = None) -> None:
    """Locks the user's mail account when the user is disabled.

    Suite Cloud swaps the account onto its locked role: it keeps receiving mail but can no
    longer log in, send or read.
    """

    if doc.flags.in_insert or doc.enabled or not doc.has_value_changed("enabled"):
        return
    # //// Neoffice — Suite Cloud locks the account of a disabled user; a self-hosted fleet has none, and the mailbox
    # //// stayed open. Ours is locked the same way as a deleted user's, its mail kept (lock_own_mailbox; #1743).
    if not is_suite_cloud_configured():
        lock_own_mailbox(doc.name)
        return
    if not is_jmap_configured(doc.name):
        return

    execute_with_logging(
        lambda: set_account_enabled(doc.name, False),
        title="Failed to lock the mail account",
        with_context=False,
        module="Mail",
    )


def remove_disabled_account_role(doc: Document, method: str | None = None) -> None:
    """Unlocks the user's mail account when the user is re-enabled."""

    if doc.flags.in_insert or not doc.enabled or not doc.has_value_changed("enabled"):
        return
    # //// Neoffice — the other half of the lock above on our own Stalwart: the user enabled again gets a new app
    # //// password, which the site uses for their mail (unlock_own_mailbox; #1743).
    if not is_suite_cloud_configured():
        unlock_own_mailbox(doc.name)
        return
    if not is_jmap_configured(doc.name):
        return

    execute_with_logging(
        lambda: set_account_enabled(doc.name, True),
        title="Failed to unlock the mail account",
        with_context=False,
        module="Mail",
    )


def delete_account(doc: Document, method: str | None = None) -> None:
    # //// Neoffice — a self-hosted fleet has no Suite Cloud to delete the account through: the check below
    # //// returned at once, and every deleted desk user left a mailbox its app passwords still opened. The owner's
    # //// choice (maintenance#1743): the mail is kept and every way into it is shut, on our own Stalwart.
    if not is_suite_cloud_configured():
        lock_own_mailbox(doc.name)
        return
    if not is_jmap_configured(doc.name):
        return

    user = doc.name
    execute_with_logging(
        lambda: delete_mail_account(user),
        title="Failed to delete the mail account",
        with_context=False,
        module="Mail",
    )

    # The cached JMAP session carries the account's ids. Left behind, a user recreated on the same
    # address would inherit the deleted account's ids and every call would be scoped to an account
    # the server no longer considers theirs.
    from suite.mail.jmap import clear_jmap_session

    clear_jmap_session(user)

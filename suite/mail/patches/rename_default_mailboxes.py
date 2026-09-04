#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe
from frappe.utils import create_batch

from suite.mail.doctype.jmap_account.jmap_account import rename_default_mailboxes
from suite.mail.doctype.sieve_script.sieve_script import build_automation_sieve
from suite.utils import enqueue_job, user_context

_ACCOUNTS_PER_BATCH = 100


def execute() -> None:
    """Rename default mailboxes still carrying their server-assigned names.

    New accounts get renamed during account setup; this backfills accounts created before
    that. Only mailboxes still carrying the exact server-assigned name are touched, so
    user-renamed mailboxes are left alone and a re-run is a no-op. Accounts that got a
    rename also get their automation sieve script rebuilt, since it files into mailboxes
    by path and would otherwise keep referencing the old names.

    Deferred to a background job: renaming needs a live JMAP session per account, which is
    not reliably reachable during ``bench migrate``.
    """

    frappe.enqueue(rename_default_mailboxes_for_existing_accounts, queue="long", enqueue_after_commit=True)


def rename_default_mailboxes_for_existing_accounts() -> None:
    """Fan the accounts out into long-queue batches."""

    account_users = get_accounts_with_enabled_user()
    for i, batch in enumerate(create_batch(list(account_users.items()), _ACCOUNTS_PER_BATCH)):
        enqueue_job(
            _rename_default_mailboxes,
            job_id=f"rename-default-mailboxes::{i}",
            deduplicate=True,
            queue="long",
            timeout=3600,
            account_users=dict(batch),
        )


def _rename_default_mailboxes(account_users: dict[str, str]) -> None:
    """Rename each account's default mailboxes, isolating per-account failures."""

    for account, user in account_users.items():
        # The job runs async after the fan-out committed, so an account can vanish in between.
        if not frappe.db.exists("JMAP Account", account):
            continue

        try:
            # Reached over JMAP as the account's own (enabled) user, not as Administrator:
            # resolving the connection as Administrator picks an arbitrary linked user,
            # which may be disabled.
            with user_context(user):
                if rename_default_mailboxes(account):
                    # The automation sieve files into mailboxes by path, so the stored
                    # script still references the old names. activate=False on purpose:
                    # activating here would override an account whose active script is the
                    # vacation auto-responder or one the user wrote themselves.
                    build_automation_sieve(account)
        except Exception:
            # Already logged by rename_default_mailboxes; move on to the next account.
            pass


def get_accounts_with_enabled_user() -> dict[str, str]:
    """JMAP accounts mapped to one of their enabled users.

    Accounts whose linked users are all disabled are skipped: a JMAP connection can only be
    opened as an enabled user. Joined to JMAP Account to drop stale User Account rows
    pointing at accounts that no longer exist.
    """

    USER_ACCOUNT = frappe.qb.DocType("User Account")
    USER = frappe.qb.DocType("User")
    JMAP_ACCOUNT = frappe.qb.DocType("JMAP Account")

    rows = (
        frappe.qb.from_(USER_ACCOUNT)
        .inner_join(USER)
        .on(USER_ACCOUNT.user == USER.name)
        .inner_join(JMAP_ACCOUNT)
        .on(USER_ACCOUNT.account == JMAP_ACCOUNT.name)
        .where(USER.enabled == 1)
        .select(USER_ACCOUNT.account, USER_ACCOUNT.user)
    ).run(as_dict=True)

    account_users = {}
    for row in rows:
        account_users.setdefault(row.account, row.user)

    return account_users

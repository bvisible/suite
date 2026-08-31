from __future__ import annotations
import frappe
from frappe.utils import create_batch

from suite.mail.doctype.sieve_script.sieve_script import build_automation_sieve
from suite.mail.utils import log_mail_error
from suite.utils import enqueue_job

_ACCOUNTS_PER_BATCH = 20


def execute() -> None:
    """Regenerate the automation Sieve script for accounts whose stored copy may be wrong.

    Two generation bugs are fixed alongside this patch, and both leave incorrect content sitting on
    the Stalwart server:

    - Rule text (``emails_from`` / ``subject_contains``) was interpolated into the script without
      escaping. A value carrying a double quote produced a script the server rejected, so the
      ``SieveScript/set`` failed, the error was swallowed, and the account kept its previous script —
      the user's rule silently never took effect.
    - Mailbox paths were resolved by walking parents by name. Where two mailboxes share a leaf name
      that resolved the wrong parent, so ``fileinto`` was generated against the wrong folder.

    Nothing rebuilds these scripts on a schedule — ``build_automation_sieve`` only runs when a user
    touches a folder, a rule, or screening — so an affected account would keep the bad script
    indefinitely. Rebuilding is idempotent, so a re-run is a no-op for accounts already correct.

    Deferred to a background job: regeneration needs a live JMAP session per account, which is not
    reliably reachable during ``bench migrate``.
    """

    frappe.enqueue(rebuild_automation_sieve_scripts, queue="long", enqueue_after_commit=True)


def rebuild_automation_sieve_scripts() -> None:
    """Fan the affected accounts out into long-queue batches."""

    accounts = get_accounts_with_automation_rules()
    for i, batch in enumerate(create_batch(accounts, _ACCOUNTS_PER_BATCH)):
        enqueue_job(
            _rebuild_automation_sieve_scripts,
            job_id=f"rebuild-automation-sieve-scripts::{i}",
            deduplicate=True,
            queue="long",
            timeout=3600,
            accounts=batch,
        )


def _rebuild_automation_sieve_scripts(accounts: list[str]) -> None:
    """Rebuild each account's automation script inline, isolating per-account failures."""

    for account in accounts:
        # The job runs async after the fan-out committed, so an account can vanish in between.
        if not account or not frappe.db.exists("JMAP Account", account):
            continue

        try:
            # activate=False on purpose: this refreshes the script's content only. Activating here
            # would override an account whose active script is the vacation auto-responder or one
            # the user wrote themselves.
            build_automation_sieve(account)
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            log_mail_error(
                "Rebuild Automation Sieve Patch Error",
                f"Failed to rebuild the automation sieve script for JMAP account {account}",
            )


def get_accounts_with_automation_rules() -> list[str]:
    """Accounts that have at least one mailbox automation rule, deduplicated.

    Scoped deliberately. ``get_automation_script_name`` *creates* the automation script when an
    account has none, so rebuilding indiscriminately would conjure an empty script onto every
    account on the site. Only mailboxes carrying a sender or subject condition contribute generated
    content, and those are exactly the accounts either bug could have affected.

    Joined to JMAP Account because Mailbox Settings carries stale rows from before the
    shared-per-account reshape — account values in the legacy ``user@domain:accountid`` format, or
    empty — and rebuilding those fails with "JMAP account does not exist".
    """

    MAILBOX_SETTINGS = frappe.qb.DocType("Mailbox Settings")
    JMAP_ACCOUNT = frappe.qb.DocType("JMAP Account")

    return (
        frappe.qb.from_(MAILBOX_SETTINGS)
        .inner_join(JMAP_ACCOUNT)
        .on(MAILBOX_SETTINGS.account == JMAP_ACCOUNT.name)
        .where(
            (MAILBOX_SETTINGS.emails_from.isnotnull() & (MAILBOX_SETTINGS.emails_from != ""))
            | (MAILBOX_SETTINGS.subject_contains.isnotnull() & (MAILBOX_SETTINGS.subject_contains != ""))
        )
        .select(MAILBOX_SETTINGS.account)
        .distinct()
    ).run(pluck="account")

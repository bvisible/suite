# //// Neoffice: deploy-time backfill — give every existing eligible desk user a
# Stalwart mailbox (mail + calendar), so the feature works for the whole team
# right after the app is deployed, not only for users created afterwards (those
# are handled by the after_insert hook). Idempotent + safe when Stalwart is off. ////
from __future__ import annotations

import frappe

from suite.mail.events import _should_provision_mail
from suite.mail.utils import is_stalwart_configured


def execute():
    """Enqueue (NOT inline) a mailbox provisioning job per eligible user.

    //// Neoffice: provisioning calls stalwart-cli (a multi-second subprocess)
    per user; doing that inline inside `bench migrate` holds the migrate
    transaction long enough to hit 'Lock wait timeout'. Enqueue instead so
    migrate returns immediately and the worker provisions in the background. ////
    """

    if not is_stalwart_configured(raise_exception=False):
        return

    users = frappe.get_all(
        "User",
        filters={"enabled": 1, "user_type": "System User", "name": ["not in", ["Administrator", "Guest"]]},
        pluck="name",
    )
    for name in users:
        try:
            doc = frappe.get_doc("User", name)
            if _should_provision_mail(doc):
                frappe.enqueue(
                    "suite.mail.events._provision_mail_account_now",
                    queue="long",
                    job_id=f"provision-mail-{name}",
                    deduplicate=True,
                    user=name,
                )
        except Exception:
            frappe.log_error("Mail backfill enqueue failed", f"user={name}")

# //// Neoffice: deploy-time backfill — give every existing eligible desk user a
# Stalwart mailbox (mail + calendar), so the feature works for the whole team
# right after the app is deployed, not only for users created afterwards (those
# are handled by the after_insert hook). Idempotent + safe when Stalwart is off. ////
from __future__ import annotations

import frappe

from suite.mail.events import _provision_mail_account_now, _should_provision_mail
from suite.mail.utils import is_stalwart_configured


def execute():
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
				_provision_mail_account_now(name)
		except Exception:
			frappe.log_error("Mail backfill failed", f"user={name}")

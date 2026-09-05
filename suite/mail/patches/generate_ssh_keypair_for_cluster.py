# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe
from frappe import _

from suite.mail.utils import log_mail_error


def execute() -> None:
    clusters = frappe.db.get_all("Mail Cluster", {"ssh_public_key": ["in", ["", None]]}, pluck="name")
    for cluster in clusters:
        try:
            frappe.get_doc("Mail Cluster", cluster).generate_ssh_keypair(save=True)
        except Exception:
            log_mail_error(_("Failed to generate SSH keypair"), frappe.get_traceback(with_context=False))

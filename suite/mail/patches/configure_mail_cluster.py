# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe
from frappe import _

from suite.utils import execute_with_logging


def execute() -> None:
    def _configure(cluster) -> None:
        doc = frappe.get_doc("Mail Cluster", cluster)
        doc.default_domain = doc.default_domain or doc.hostname

        if not doc.recovery_admin_user:
            if hasattr(doc, "fallback_admin_user") and doc.fallback_admin_user:
                doc.recovery_admin_user = doc.fallback_admin_user

        if not doc.recovery_admin_password:
            if hasattr(doc, "fallback_admin_password") and doc.fallback_admin_password:
                if password := doc.get_password("fallback_admin_password"):
                    doc.recovery_admin_password = password

        doc._initialize_data_store()
        doc.save()

    for cluster in frappe.db.get_all("Mail Cluster", {}, pluck="name"):
        execute_with_logging(
            func=lambda: _configure(cluster),
            title=_("Failed to configure Mail Cluster {0}").format(frappe.bold(cluster)),
            module="Mail",
        )

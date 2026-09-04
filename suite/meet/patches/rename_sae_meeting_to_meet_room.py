#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe


def execute() -> None:
    """Rename the Meet DocTypes before their new schemas are synced."""
    if frappe.db.exists("DocType", "Sae Meeting User"):
        frappe.rename_doc("DocType", "Sae Meeting User", "Meet Room User", force=True)

    if frappe.db.exists("DocType", "Sae Meeting"):
        frappe.rename_doc("DocType", "Sae Meeting", "Meet Room", force=True)

    frappe.clear_cache(doctype="Meet Room")

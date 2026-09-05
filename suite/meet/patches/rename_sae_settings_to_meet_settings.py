# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe


def execute() -> None:
    """Rename the settings DocType before its new schema is synced."""
    if frappe.db.exists("DocType", "Sae Settings"):
        frappe.rename_doc("DocType", "Sae Settings", "Meet Settings", force=True)

    frappe.clear_cache(doctype="Meet Settings")

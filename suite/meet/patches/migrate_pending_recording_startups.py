# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe


def execute():
    if not frappe.db.table_exists("Meet Recording"):
        return
    frappe.db.set_value(
        "Meet Recording",
        {"status": "Pending"},
        "status",
        "Starting",
        update_modified=False,
    )

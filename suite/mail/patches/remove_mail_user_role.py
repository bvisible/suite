#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe


def execute() -> None:
    frappe.db.delete(
        "Has Role",
        {
            "role": "Mail User",
            "parenttype": "User",
        },
    )

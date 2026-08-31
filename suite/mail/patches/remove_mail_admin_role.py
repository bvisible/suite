from __future__ import annotations
import frappe


def execute() -> None:
    frappe.db.delete(
        "Has Role",
        {
            "role": "Mail Admin",
            "parenttype": "User",
            "parent": ("!=", "Administrator"),
        },
    )

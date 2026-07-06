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

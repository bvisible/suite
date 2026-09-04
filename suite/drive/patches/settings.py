#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe


def execute():
    if not frappe.db.table_exists("Drive Team Member"):
        # Site never had the legacy Drive schema — nothing to migrate.
        return

    for user in frappe.db.get_list("User", pluck="name"):
        teams = frappe.get_all(
            "Drive Team Member",
            pluck="parent",
            filters=[
                ["parenttype", "=", "Drive Team"],
                ["user", "=", user],
            ],
        )
        if teams:
            if not frappe.db.exists("Drive Settings", {"user": user}):
                frappe.get_doc(
                    {
                        "doctype": "Drive Settings",
                        "user": user,
                        "single_click": 1,
                        "default_team": teams[0],
                    }
                ).insert()

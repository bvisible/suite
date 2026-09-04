# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe

SUITE_USER_ROLE = "Suite User"


def after_app_install(app_name: str | None = None):
    assign_suite_role_to_all_users()


def assign_suite_role_to_all_users():
    if not frappe.db.exists("Role", SUITE_USER_ROLE):
        return

    users = frappe.get_all(
        "User",
        filters={"enabled": 1, "name": ["not in", ["Guest", "Administrator"]]},
        pluck="name",
    )

    for user_name in users:
        user = frappe.get_doc("User", user_name)
        if not any(r.role == SUITE_USER_ROLE for r in user.roles):
            user.append("roles", {"role": SUITE_USER_ROLE})
            user.save(ignore_permissions=True)

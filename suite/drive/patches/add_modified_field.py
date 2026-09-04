#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe


def execute():
    if not frappe.db.table_exists("Drive File"):
        # Site never had the legacy Drive schema — nothing to migrate.
        return

    for k in frappe.get_all("Drive File", fields=["name", "modified"]):
        frappe.db.set_value(
            "Drive File",
            k.name,
            "_modified",
            k.modified.strftime("%Y-%m-%d %H:%M:%S.%f"),
            update_modified=False,
        )

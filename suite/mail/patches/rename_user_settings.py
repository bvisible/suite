# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from uuid import uuid7

import frappe


def execute() -> None:
    for settings in frappe.db.get_all("User Settings", pluck="name"):
        doc = frappe.get_doc("User Settings", settings)
        doc.rename(str(uuid7()), force=True)

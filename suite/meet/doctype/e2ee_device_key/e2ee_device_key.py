# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe
from frappe.model.document import Document


class E2EEDeviceKey(Document):
    pass


def on_doctype_update() -> None:
    frappe.db.add_unique(
        "E2EE Device Key",
        ["user", "device_id"],
        constraint_name="unique_e2ee_device_user_device",
    )


def on_update(doc: E2EEDeviceKey, method: str | None = None) -> None:
    """Stamp created_at on first save (not on subsequent updates)."""
    if not doc.created_at:
        doc.db_set("created_at", frappe.utils.now_datetime(), update_modified=False)

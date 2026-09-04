# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe
from frappe.model.document import Document

PRIVILEGED_FIELDS = ("quota", "user_folder")


class DriveSettings(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        auto_detect_links: DF.Check
        quota: DF.Int
        user: DF.Link | None
        user_folder: DF.Link | None
        webdav_enabled: DF.Check
        writer_settings: DF.JSON | None
    # end: auto-generated types

    def validate(self):
        if self.flags.ignore_permissions or frappe.session.user == "Administrator":
            return
        if "Suite Admin" in frappe.get_roles():
            return

        before = self.get_doc_before_save()
        for field in PRIVILEGED_FIELDS:
            previous = before.get(field) if before else None
            if (self.get(field) or None) != (previous or None):
                frappe.throw(f"{field} is managed by Drive.", frappe.PermissionError)

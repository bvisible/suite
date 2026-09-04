#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe
from frappe import _
from frappe.model.document import Document


class DriveStorageReservation(Document):
    def validate(self):
        if isinstance(self.reserved_bytes, bool) or not isinstance(self.reserved_bytes, int):
            frappe.throw(_("Reserved bytes must be a nonnegative integer"))
        if self.reserved_bytes < 0:
            frappe.throw(_("Reserved bytes must be a nonnegative integer"))

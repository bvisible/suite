# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe
from frappe.model.document import Document


class DriveToken(Document):
    def autoname(self):
        # The name is the secret capability itself.
        self.name = frappe.generate_hash(length=43)

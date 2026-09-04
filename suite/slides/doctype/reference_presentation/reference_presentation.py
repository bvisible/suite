# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from frappe.model.document import Document


class ReferencePresentation(Document):
    pass

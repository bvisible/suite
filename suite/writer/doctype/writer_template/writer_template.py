# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from frappe.model.document import Document

from suite.utils.document_owner import refuse_owner_change  # //// Neoffice — WriterTemplate.validate (#2296)


class WriterTemplate(Document):
    # //// Neoffice — the owner of a saved template is not the caller's to change (neoffice-maintenance#2296):
    # //// template_has_permission lets the owner write it, and read the owner from the request being checked.
    def validate(self):
        refuse_owner_change(self)

# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from frappe.model.document import Document


class EmailAddress(Document):
    def db_insert(self, *args, **kwargs):
        raise NotImplementedError

    def load_from_db(self):
        raise NotImplementedError

    def db_update(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError

    @staticmethod
    def get_list(filters=None, page_length=20, **kwargs):
        pass

    @staticmethod
    def get_count(filters=None, **kwargs):
        pass

    @staticmethod
    def get_stats(**kwargs):
        pass

# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from uuid_utils import uuid7


class EmailMessagePart(Document):
	def autoname(self) -> None:
		self.name = str(uuid7())

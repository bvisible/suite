# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

from mail.utils.validation import is_valid_cron_expression


class MailAgentStore(Document):
	def validate(self):
		self.validate_purge_frequency()

	def validate_purge_frequency(self):
		"""Validate the purge frequency"""

		if self.purge_frequency:
			is_valid_cron_expression(self.purge_frequency, raise_exception=True)

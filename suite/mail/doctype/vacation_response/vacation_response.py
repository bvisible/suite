# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now


class VacationResponse(Document):
	def validate(self) -> None:
		if self.enabled:
			self.validate_from_date()
			self.validate_to_date()

	def validate_from_date(self) -> None:
		"""Validates the From Date."""

		if not self.from_date:
			frappe.throw(_("From Date is required."))

	def validate_to_date(self) -> None:
		"""Validates the To Date."""

		if not self.to_date:
			frappe.throw(_("{0} is required.").format(frappe.bold(_("To Date"))))
		elif self.to_date < now():
			frappe.throw(_("{0} cannot be in the past.").format(frappe.bold(_("To Date"))))
		elif self.to_date < self.from_date:
			frappe.throw(
				_("{0} cannot be before {1}.").format(frappe.bold(_("To Date")), frappe.bold(_("From Date")))
			)

# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now

from mail.jmap import get_jmap_client
from mail.utils.dt import convert_to_utc


class VacationResponse(Document):
	def validate(self) -> None:
		if self.enabled:
			self.validate_from_date()
			self.validate_to_date()

	def on_update(self) -> None:
		self._create_or_update_vacation_response()

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

	def _create_or_update_vacation_response(self) -> None:
		"""Create or update the vacation response using JMAP client."""

		from_date = convert_to_utc(self.from_date).isoformat()
		to_date = convert_to_utc(self.to_date).isoformat()

		try:
			client = get_jmap_client(self.account)
			client.vacation_response_set(
				bool(self.enabled), from_date, to_date, self.subject, self.text_body, self.html_body
			)
		except Exception:
			frappe.log_error(
				title=_("Failed to create or update vacation response"),
				message=frappe.get_traceback(with_context=True),
			)
			frappe.throw(_("Failed to create or update vacation response."))

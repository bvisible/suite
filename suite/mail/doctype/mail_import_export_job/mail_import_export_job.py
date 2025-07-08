# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from uuid_utils import uuid7

from mail.utils.cache import get_account_for_user
from mail.utils.user import is_account_owner, is_system_manager


class MailImportExportJob(Document):
	def autoname(self) -> None:
		self.name = str(uuid7())


def get_permission_query_condition(user: str | None = None) -> str:
	user = user or frappe.session.user

	if is_system_manager(user):
		return ""

	if account := get_account_for_user(user):
		return f"(`tabMail Import Export Job`.account = '{account}')"
	else:
		return "1=0"


def has_permission(doc: Document, ptype: str, user: str | None = None) -> bool:
	if doc.doctype != "Mail Import Export Job":
		return False

	user = user or frappe.session.user
	user_is_system_manager = is_system_manager(user)
	user_is_account_owner = is_account_owner(doc.account, user)

	if user_is_system_manager or user_is_account_owner:
		return True

	return False

# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from mail.backend import MailBackendMemberManager
from mail.utils.cache import (
	get_account_for_user,
	get_cluster_for_tenant,
	get_groups_owned_by_tenant,
	get_tenant_for_group,
	get_tenant_for_user,
)
from mail.utils.user import has_role, is_system_manager


class MailingListMember(Document):
	@property
	def member_is_group(self) -> bool:
		"""Return True if the member is a Mailing List."""

		return self.member_type == "Mailing List"

	def validate(self) -> None:
		self.validate_mailing_list()
		self.validate_member_tenant()
		self.validate_member_name()

	def validate_mailing_list(self) -> None:
		"""Validate if the Mailing List is enabled."""

		if not frappe.db.get_value("Mailing List", self.mailing_list, "enabled"):
			frappe.throw(_("The Mailing List {0} is disabled.").format(frappe.bold(self.mailing_list)))

	def validate_member_tenant(self) -> None:
		"""Validate if the Mailing List and the member belong to the same tenant."""

		group_tenant = get_tenant_for_group(self.mailing_list)
		member_tenant = frappe.db.get_value(self.member_type, self.member_name, "tenant")

		if group_tenant != member_tenant:
			frappe.throw(
				_("The Mailing List {0} and the member {1} {2} must belong to the same tenant.").format(
					frappe.bold(self.mailing_list), self.member_type, frappe.bold(self.member_name)
				)
			)

	def validate_member_name(self) -> None:
		"""Validate if the member name is not the same as the Mailing List."""

		if self.mailing_list == self.member_name:
			if self.member_type == "Mailing List":
				frappe.throw(_("Mailing List cannot be a member of itself."))
			else:
				frappe.throw(_("Member cannot be the same as the Mailing List."))

		if not frappe.db.get_value(self.member_type, self.member_name, "enabled"):
			frappe.throw(
				_("The {0} {1} is disabled.").format(self.member_type, frappe.bold(self.member_name))
			)

	def after_insert(self) -> None:
		MailBackendMemberManager(
			"Mail Cluster", get_cluster_for_tenant(get_tenant_for_group(self.mailing_list))
		).create(
			self.mailing_list,
			self.member_name,
			self.member_is_group,
		)

	def on_trash(self) -> None:
		MailBackendMemberManager(
			"Mail Cluster", get_cluster_for_tenant(get_tenant_for_group(self.mailing_list))
		).delete(
			self.mailing_list,
			self.member_name,
			self.member_is_group,
		)


def has_permission(doc: "Document", ptype: str, user: str | None = None) -> bool:
	if doc.doctype != "Mailing List Member":
		return False

	user = user or frappe.session.user

	if is_system_manager(user):
		return True

	if has_role(user, "Mail Admin"):
		if tenant := get_tenant_for_user(user):
			return doc.mailing_list in get_groups_owned_by_tenant(tenant)

	if has_role(user, "Mail User"):
		return doc.member_type == "Mail Account" and doc.member_name == get_account_for_user(user)

	return False


def get_permission_query_condition(user: str | None = None) -> str:
	user = user or frappe.session.user

	if is_system_manager(user):
		return ""

	if has_role(user, "Mail Admin"):
		if tenant := get_tenant_for_user(user):
			if groups := get_groups_owned_by_tenant(tenant):
				return f'(`tabMailing List Member`.`mailing_list` IN ({", ".join([frappe.db.escape(group) for group in groups])}))'

	if has_role(user, "Mail User"):
		if account := get_account_for_user(user):
			return f'(`tabMailing List Member`.`member_type` = "Mail Account" AND `tabMailing List Member`.`member_name` = {frappe.db.escape(account)})'

	return "1=0"


def on_doctype_update() -> None:
	frappe.db.add_unique(
		"Mailing List Member",
		["mailing_list", "member_name"],
		constraint_name="unique_mailing_list_member",
	)

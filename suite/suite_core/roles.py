# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

RESERVED_USERS = ("Guest", "Administrator")


def assign_role(user, role_name: str, desk_access: bool = True) -> None:
	"""Append `role_name` to an in-memory User doc, creating the Role if missing.

	Meant to be called from a `before_insert` hook so the role is part of the
	document Frappe validates. Assigning roles after insert is too late for
	`User.check_roles_added` (which warns "Newly created user X has no roles
	enabled") and for `User.set_system_user` (which demotes a role-less user to
	a Website User), and it costs an extra `User.save` per role.

	#//// Neoffice — `desk_access` is a parameter here, and our apps pass False.
	#//// The Role doctype defaults it to 1, and assigning a desk-access role
	#//// re-promotes a user to System User: that is exactly how frontend signups
	#//// silently became system users. Upstream keeps True as its default, so
	#//// this argument must survive the next merge — see the callers.
	"""
	# `before_insert` runs ahead of `set_new_name`, so `user.name` is still unset
	# on a fresh User — fall back to the email it will be named after.
	identifier = user.name or user.email
	if not identifier or identifier in RESERVED_USERS:
		return

	if not frappe.db.exists("Role", role_name):
		frappe.get_doc(
			{"doctype": "Role", "role_name": role_name, "desk_access": int(desk_access)}
		).insert(ignore_permissions=True)

	if any(row.role == role_name for row in user.get("roles") or []):
		return

	user.append("roles", {"role": role_name})

# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now

from mail.jmap import get_jmap_client
from mail.utils import extract_filter_values
from mail.utils.cache import get_account_for_user


class Mailbox(Document):
	def autoname(self) -> None:
		self.name = f"{self.account}|{self.id}"

	def db_insert(self, *args, **kwargs) -> None:
		raise NotImplementedError

	def load_from_db(self) -> "Mailbox":
		mailbox = get_mailbox(self.name)
		return super(Document, self).__init__(mailbox)

	def db_update(self) -> None:
		raise NotImplementedError

	def delete(self) -> None:
		raise NotImplementedError

	@staticmethod
	def get_list(filters=None, page_length=20, **kwargs) -> list:
		filters = filters or []
		account_values = extract_filter_values(filters, [{"account": "="}])
		account = (
			account_values[0]
			if account_values and account_values[0]
			else get_account_for_user(frappe.session.user)
		)

		if not account:
			frappe.msgprint(_("Please select a account to view mailboxes."), alert=True)
			return []

		mailboxes = fetch_mailboxes(account, limit=page_length)

		if not mailboxes:
			frappe.msgprint(_("No mailboxes found."), alert=True)

		return mailboxes

	@staticmethod
	def get_count(filters=None, **kwargs) -> int:
		return len(Mailbox.get_list(filters, **kwargs))

	@staticmethod
	def get_stats(**kwargs) -> dict:
		pass


def get_mailbox(name: str) -> dict:
	"""Returns mailbox details for the given name in the format 'account|id'."""

	account, id = name.split("|")
	client = get_jmap_client(account)
	if mailboxes := client.mailbox_get([id]):
		return format_mailbox(account, mailboxes[0])

	frappe.throw(
		_("Mailbox with ID {0} not found in account {1}.").format(frappe.bold(id), frappe.bold(account))
	)


def fetch_mailboxes(account: str, page: int = 1, limit: int = 10) -> list:
	"""Returns a list of mailboxes for the given account."""

	client = get_jmap_client(account)
	if mailboxes := client.mailbox_get():
		return [format_mailbox(account, mailbox) for mailbox in mailboxes]

	return []


def format_mailbox(account: str, mailbox: dict) -> dict:
	"""Formats mailbox data for display."""

	if _parent := mailbox["parentId"]:
		_parent = f"{account}|{_parent}"
	if rights := mailbox.get("myRights"):
		rights = json.dumps(rights, indent=4, sort_keys=True)

	return {
		"name": f"{account}|{mailbox['id']}",
		"account": account,
		"id": mailbox["id"],
		"_name": mailbox["name"],
		"_parent": _parent,
		"parent_id": mailbox["parentId"],
		"role": mailbox["role"],
		"sort_order": cint(mailbox["sortOrder"]),
		"is_subscribed": bool(mailbox["isSubscribed"]),
		"total_emails": cint(mailbox["totalEmails"]),
		"unread_emails": cint(mailbox["unreadEmails"]),
		"total_threads": cint(mailbox["totalThreads"]),
		"unread_threads": cint(mailbox["unreadThreads"]),
		"rights": rights,
		"creation": now(),
		"modified": now(),
	}

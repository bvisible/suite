# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import hashlib
import json
from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, time_diff_in_seconds

from mail.jmap import get_jmap_client
from mail.utils import extract_filter_values
from mail.utils.cache import get_account_for_user
from mail.utils.dt import parse_iso_datetime
from mail.utils.user import is_system_manager

if TYPE_CHECKING:
	from mail.mail.doctype.email_message_part.email_message_part import EmailMessagePart


class EmailMessage(Document):
	@property
	def received_after(self) -> int:
		return time_diff_in_seconds(self.received_at, self.sent_at)

	@property
	def message(self) -> str | None:
		if self.blob_id:
			cache_key = get_blob_cache_key(self.account, self.blob_id)
			if content := frappe.cache.get_value(cache_key):
				return content.decode("utf-8")

	def db_insert(self, *args, **kwargs) -> None:
		raise NotImplementedError

	def load_from_db(self) -> "EmailMessage":
		if "-" not in self.name:
			frappe.throw(_("Name must be in the format {account}-{id}."))

		account, id = self.name.split("-")

		user = frappe.session.user
		if not is_system_manager(user):
			if account != get_account_for_user(user):
				frappe.throw(_("You do not have permission to view this message."))

		return super(Document, self).__init__(get_email_data(account, id))

	def db_update(self) -> None:
		raise NotImplementedError

	def delete(self) -> None:
		raise NotImplementedError

	@staticmethod
	def get_current_account(filters: list | None = None) -> str | None:
		filters = filters or []

		user = frappe.session.user
		account = get_account_for_user(user)

		if is_system_manager(user):
			account = extract_filter_values(filters, [{"account": "="}])[0] or account

		return account

	@staticmethod
	def get_list(filters: list | None = None, page_length: int = 20, start: int = 0, **kwargs) -> list:
		filters = filters or []
		account = EmailMessage.get_current_account(filters)

		if not account:
			frappe.msgprint(_("Please select an account to view messages."), alert=True)
			return []

		return get_email_messages(account, filter={}, position=start, limit=page_length)

	@staticmethod
	def get_count(filters: list | None = None, **kwargs) -> int:
		filters = filters or []
		account = EmailMessage.get_current_account(filters)

		return get_email_list_total(account, filter={}) if account else 0

	@staticmethod
	def get_stats(**kwargs) -> dict:
		return {}

	def _get_blob(self, blob_id: str, name: str | None = None) -> bytes:
		if not blob_id:
			frappe.throw(_("Blob ID is required."))

		cache_key = get_blob_cache_key(self.account, blob_id)
		if content := frappe.cache.get_value(cache_key):
			return content

		client = get_jmap_client(self.account)
		account_id = client.account_ids[0]
		content = client.download_blob(account_id, blob_id, name)
		cache_blob(self.account, blob_id, content)

		return content

	@frappe.whitelist()
	def _load_attachments(self, attachments: list["EmailMessagePart"] | None = None) -> None:
		if not self.has_attachment:
			return

		for attachment in attachments or self.attachments:
			self._get_blob(attachment.blob_id, attachment._name)

	@frappe.whitelist()
	def get_mime_message(self) -> str:
		if not self.blob_id:
			frappe.throw(_("Email does not have a blob ID."))

		return self._get_blob(self.blob_id).decode("utf-8")

	def get_attachment(self, cid: str | None = None, blob_id: str | None = None) -> bytes:
		if not self.has_attachment or not self.attachments:
			frappe.throw(_("Email does not have any attachments."))

		if not cid and not blob_id:
			frappe.throw(_("Either cid or blob_id is required."))

		attachment_to_download = None
		for attachment in self.attachments:
			if (cid and attachment.cid == cid) or (blob_id and attachment.blob_id == blob_id):
				attachment_to_download = attachment
				break

		if not attachment_to_download:
			frappe.throw(_("Attachment not found."))

		if content := self._get_blob(attachment_to_download.blob_id, attachment_to_download._name):
			return content

		frappe.throw(_("Failed to retrieve the attachment content."))


def get_email_messages(account: str, filter: dict, position: int = 0, limit: int = 50) -> list[dict]:
	ids = get_email_list(account, filter, position, limit)
	email_messages = get_emails_data(account, ids)

	return email_messages


def get_email_list(account: str, filter: dict, position: int = 0, limit: int = 50) -> list[str]:
	total_emails = get_email_list_total(account, filter)

	if total_emails == 0 or position >= total_emails:
		return []

	cache_key = get_list_cache_key(account, filter)
	cached_ids = frappe.cache.get_value(cache_key)

	if cached_ids is not None:
		return cached_ids[position : position + limit]

	client = get_jmap_client(account)
	account_id = client.account_ids[0]

	if total_emails > 1000:
		result = client.query_emails(account_id, filter, position, limit)
		cache_email_list_total(account, filter, result.get("total", 0))
		return result.get("ids", [])

	result = client.query_emails(account_id, filter, 0, total_emails)
	all_ids = result.get("ids", [])

	cache_email_ids(account, filter, all_ids)
	cache_email_list_total(account, filter, result.get("total", 0))

	return all_ids[position : position + limit]


def get_email_list_total(account: str, filter: dict, force_fresh: bool = False) -> int:
	if not force_fresh:
		cache_key = get_list_total_cache_key(account, filter)
		cached_total = frappe.cache.get_value(cache_key)

		if cached_total is not None:
			return cint(cached_total)

	client = get_jmap_client(account)
	account_id = client.account_ids[0]

	result = client.query_emails(account_id, filter, position=0, limit=0)
	total = result.get("total", 0)

	cache_email_list_total(account, filter, total)

	return total


def get_email_data(account: str, id: str) -> dict:
	emails = get_emails_data(account, [id])

	if not emails:
		frappe.throw(_("Email Message {0} not found.").format(frappe.bold(f"{account}-{id}")))

	return emails[0]


def get_emails_data(account: str, ids: list[str]) -> list[str]:
	email_messages = []

	ids_to_fetch = []
	for id in ids:
		email_message = frappe.cache.get_value(get_email_cache_key(account, id))
		if email_message:
			email_messages.append(email_message)
		else:
			ids_to_fetch.append(id)

	if ids_to_fetch:
		client = get_jmap_client(account)
		account_id = client.account_ids[0]
		for email_data in client.get_emails(account_id, ids_to_fetch):
			email_message = format_email_message(account, email_data)
			cache_email_message(account, email_data["id"], email_message)
			email_messages.append(email_message)

	return email_messages


def invalidate_email_list_cache(account: str, filter: dict) -> None:
	frappe.cache.delete_value(get_list_cache_key(account, filter))
	frappe.cache.delete_value(get_list_total_cache_key(account, filter))


def get_list_cache_key(account: str, filter: dict) -> str:
	filter_json = json.dumps(filter, sort_keys=True)
	filter_hash = hashlib.sha1(filter_json.encode()).hexdigest()
	return f"jmap:list:{account}:{filter_hash}"


def get_list_total_cache_key(account: str, filter: dict) -> str:
	filter_json = json.dumps(filter, sort_keys=True)
	filter_hash = hashlib.sha1(filter_json.encode()).hexdigest()
	return f"jmap:list:total:{account}:{filter_hash}"


def get_email_cache_key(account: str, id: str) -> str:
	return f"jmap:email:{account}:{id}"


def get_blob_cache_key(account: str, blob_id: str) -> str:
	return f"jmap:blob:{account}:{blob_id}"


def cache_email_ids(account: str, filter: dict, ids: list[str]) -> None:
	cache_key = get_list_cache_key(account, filter)
	frappe.cache.set_value(cache_key, ids, expires_in_sec=86400)


def cache_email_list_total(account: str, filter: dict, total: int = 0) -> None:
	cache_key = get_list_total_cache_key(account, filter)
	frappe.cache.set_value(cache_key, total, expires_in_sec=86400)


def cache_email_message(account: str, id: str, email_message: dict) -> None:
	cache_key = get_email_cache_key(account, id)
	frappe.cache.set_value(cache_key, email_message, expires_in_sec=86400)


def cache_blob(account: str, blob_id: str, content: bytes) -> None:
	cache_key = get_blob_cache_key(account, blob_id)
	frappe.cache.set_value(cache_key, content, expires_in_sec=86400)


def format_email_message(account: str, email: dict) -> dict:
	email_message = {}

	client = get_jmap_client(account)
	account_id = client.account_ids[0]

	email_message.update(
		{
			"name": f"{account}-{email['id']}",
			"account": account,
			"folder": client.get_mailbox_name(account_id, list(email["mailboxIds"].keys())[0]),
			"subject": email["subject"],
			"preview": (email.get("preview") or "").strip(),
			"sent_at": parse_iso_datetime(email["sentAt"]),
			"received_at": parse_iso_datetime(email["receivedAt"]),
			"blob_id": email["blobId"],
			"thread_id": email["threadId"],
			"size": email["size"],
			"_keywords": json.dumps(email["keywords"], indent=4),
			"has_attachment": bool(email["hasAttachment"]),
			"creation": parse_iso_datetime(email["receivedAt"]),
			"modified": parse_iso_datetime(email["receivedAt"]),
		}
	)

	for key in ["from", "sender"]:
		if reply_to := email[key]:
			email_message[f"{key}_name"] = reply_to[0]["name"]
			email_message[f"{key}_email"] = reply_to[0]["email"]

	email_message["recipients"] = []
	for key in ["to", "cc", "bcc"]:
		if rcpts := email[key]:
			titled_key = key.title()
			email_message["recipients"].extend(
				[{"type": titled_key, "display_name": rcpt["name"], "email": rcpt["email"]} for rcpt in rcpts]
			)

	if reply_to := email["replyTo"]:
		email_message["reply_to"] = [{"display_name": rt["name"], "email": rt["email"]} for rt in reply_to]

	for key, field in {"htmlBody": "html_body", "textBody": "text_body"}.items():
		if body := email[key]:
			part_id = body[0]["partId"]
			email_message[field] = email["bodyValues"].get(part_id, {}).get("value")

	for key, field in {"messageId": "message_id", "inReplyTo": "in_reply_to"}.items():
		if reply_to := email[key]:
			email_message[field] = reply_to[0]

	if email["keywords"].get("$seen", False):
		email_message["seen"] = 1

	for key, field in {
		"attachments": "attachments",
		"htmlBody": "_html_body",
		"textBody": "_text_body",
	}.items():
		email_message[field] = [
			{
				"part_id": p["partId"],
				"blob_id": p["blobId"],
				"size": p["size"],
				"_name": p["name"],
				"type": p["type"],
				"charset": p["charset"],
				"disposition": p["disposition"],
				"cid": p["cid"],
				"language": p["language"],
				"location": p["location"],
			}
			for p in email[key]
		]

	return email_message

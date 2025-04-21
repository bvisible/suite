# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
import re
from functools import cached_property

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, time_diff_in_seconds
from uuid_utils import uuid7

from mail.jmap import get_jmap_client
from mail.utils.cache import get_account_for_user
from mail.utils.dt import parse_iso_datetime
from mail.utils.email_parser import EmailParser
from mail.utils.user import is_account_owner, is_system_manager

BATCH_SIZE = 100
BLOB_CACHE_TTL = 3600


class EmailMessage(Document):
	@property
	def received_after(self) -> int:
		"""Returns the time difference in seconds between received and sent time."""

		return time_diff_in_seconds(self.received_at, self.sent_at)

	@property
	def spf_pass(self) -> int:
		"""Returns SPF pass status."""

		return cint(self.authentication_results.get("spf_pass"))

	@property
	def dkim_pass(self) -> int:
		"""Returns DKIM pass status."""

		return cint(self.authentication_results.get("dkim_pass"))

	@property
	def dmarc_pass(self) -> int:
		"""Returns DMARC pass status."""

		return cint(self.authentication_results.get("dmarc_pass"))

	@property
	def spf_description(self) -> str | None:
		"""Returns SPF description."""

		return self.authentication_results.get("spf_description")

	@property
	def dkim_description(self) -> str | None:
		"""Returns DKIM description."""

		return self.authentication_results.get("dkim_description")

	@property
	def dmarc_description(self) -> str | None:
		"""Returns DMARC description."""

		return self.authentication_results.get("dmarc_description")

	@cached_property
	def from_ip(self) -> str | None:
		"""Returns the IP address of the sender."""

		if not self.parsed_message:
			return

		if header := self.parsed_message.get_header("Received"):
			ip_pattern = re.compile(r"\[(?P<ip>[\d\.]+|[a-fA-F0-9:]+)")
			ip_match = ip_pattern.search(header)
			return ip_match.group("ip") if ip_match else None

	@cached_property
	def from_host(self) -> str | None:
		"""Returns the host of the sender."""

		if not self.parsed_message:
			return

		if header := self.parsed_message.get_header("Received"):
			host_pattern = re.compile(r"from\s+(?P<host>[^\s]+)")
			host_match = host_pattern.search(header)
			return host_match.group("host") if host_match else None

	@cached_property
	def spam_score(self) -> float:
		"""Returns the spam score of the email."""

		if not self.parsed_message:
			return 0.0

		if header := self.parsed_message.get_header("X-Spam-Status"):
			score_pattern = re.compile(r"score=(-?\d+\.?\d*)")
			score_match = score_pattern.search(header)
			return float(score_match.group(1)) if score_match else 0.0

	@property
	def message(self) -> str | None:
		"""Returns the message content if available."""

		cache_key = generate_blob_cache_key(self.account, self.blob_id)
		if content := frappe.cache.get_value(cache_key):
			return content.decode("utf-8")

	@cached_property
	def parsed_message(self) -> EmailParser | None:
		"""Returns the parsed email message."""

		if self.message:
			return EmailParser(self.message)

	@cached_property
	def authentication_results(self) -> dict[str, int | str]:
		"""Returns the authentication results of the email."""

		if not self.parsed_message:
			return {}

		return self.parsed_message.get_authentication_results()

	@staticmethod
	def _validate_permission(account: str) -> None:
		"""Validate if the user has permission to access the account."""

		user = frappe.session.user
		if not is_system_manager(user) and account != get_account_for_user(user):
			frappe.throw(_("You do not have permission to access this resource."), frappe.PermissionError)

	@staticmethod
	def _mark_emails_as_seen_unseen(account: str, message_ids: list[str], seen: bool) -> None:
		"""Mark emails as seen or unseen."""

		if not account or not message_ids:
			frappe.throw(_("Account and message IDs are required."))

		EmailMessage._validate_permission(account)

		email_id_keywords_map = {}
		message_id_keywords_map = {}
		for d in frappe.db.get_all(
			"Email Message", {"account": account, "name": ["in", message_ids]}, ["name", "_id", "_keywords"]
		):
			for name, _id, _keywords in d.items():
				_keywords = json.loads(_keywords)
				_keywords.update({"$seen": seen})
				email_id_keywords_map[_id] = _keywords
				message_id_keywords_map[name] = _keywords

		if not email_id_keywords_map:
			return

		client = get_jmap_client(account)
		client.update_emails_keywords(email_id_keywords_map)

		for message_id, _keywords in message_id_keywords_map.items():
			frappe.db.set_value("Email Message", message_id, "_keywords", json.dumps(_keywords, indent=4))

	@staticmethod
	def get_thread(account: str, thread_id: str) -> list[str]:
		"""Returns the message IDs in a thread."""

		if not account or not thread_id:
			frappe.throw(_("Account and thread ID are required."))

		EmailMessage._validate_permission(account)

		return frappe.db.get_all("Email Message", {"account": account, "thread_id": thread_id}, pluck="name")

	@staticmethod
	def get_thread_messages(account: str, thread_id: str) -> list["EmailMessage"]:
		"""Returns the email messages in a thread."""

		messages = []
		for message_id in EmailMessage.get_thread(account, thread_id):
			email_message = frappe.get_doc("Email Message", message_id)
			messages.append(email_message)

		return messages

	@staticmethod
	def move_emails_to_mailbox(
		account: str,
		message_ids: list[str],
		mailbox_id: str | None = None,
		mailbox_role: str | None = None,
		mailbox_name: str | None = None,
	) -> None:
		"""Move emails to a specified mailbox."""

		if not account or not message_ids or not (mailbox_id or mailbox_role or mailbox_name):
			frappe.throw(_("Account, message IDs, and mailbox ID/role/name are required."))

		EmailMessage._validate_permission(account)

		filters = {"account": account, "name": ["in", message_ids]}
		email_ids = frappe.db.get_all("Email Message", filters, pluck="_id")

		if not email_ids:
			return

		client = get_jmap_client(account)
		target_mailbox_id = mailbox_id or client.get_mailbox_id(mailbox_role, mailbox_name)

		if not target_mailbox_id:
			frappe.throw(_("Mailbox not found."))

		client.move_emails(email_ids, target_mailbox_id)
		target_mailbox_name = mailbox_name or client.get_mailbox_name(target_mailbox_id)
		frappe.db.set_value("Email Message", filters, "folder", target_mailbox_name)

	@staticmethod
	def mark_emails_as_seen(account: str, message_ids: list[str]) -> None:
		"""Mark emails as seen."""

		EmailMessage._mark_emails_as_seen_unseen(account, message_ids, seen=True)

	@staticmethod
	def mark_emails_as_unseen(account: str, message_ids: list[str]) -> None:
		"""Mark emails as unseen."""

		EmailMessage._mark_emails_as_seen_unseen(account, message_ids, seen=False)

	@staticmethod
	def fetch_blob(account: str, blob_id: str, name: str | None = None) -> bytes:
		"""Fetch the content of a blob."""

		if not account or not blob_id:
			frappe.throw(_("Account and blob ID are required."))

		EmailMessage._validate_permission(account)

		cache_key = generate_blob_cache_key(account, blob_id)
		if content := frappe.cache.get_value(cache_key):
			return content

		client = get_jmap_client(account)

		try:
			content = client.download_blob(blob_id, name)
			store_blob_in_cache(account, blob_id, content)
			return content
		except Exception as e:
			frappe.throw(_("Failed to download blob: {0}").format(str(e)))

	def autoname(self) -> None:
		self.name = str(uuid7())

	def clear_cached_properties(self) -> None:
		"""Clear cached properties to avoid stale data."""

		for property in [
			"from_ip",
			"from_host",
			"spam_score",
			"parsed_message",
			"authentication_results",
		]:
			self.__dict__.pop(property, None)

	def fetch_attachment(self, cid: str | None = None, blob_id: str | None = None) -> bytes:
		"""Returns the content of an attachment."""

		if not self.has_attachment or not self.attachments:
			frappe.throw(_("Email does not have any attachments."))

		if not cid and not blob_id:
			frappe.throw(_("Either cid or blob_id is required."))

		attachment = next(
			(a for a in self.attachments if (cid and a.cid == cid) or (blob_id and a.blob_id == blob_id)),
			None,
		)

		if not attachment:
			frappe.throw(_("Attachment not found."))

		return EmailMessage.fetch_blob(self.account, attachment.blob_id, attachment._name)

	@frappe.whitelist()
	def move_to_mailbox(
		self, mailbox_id: str | None = None, mailbox_role: str | None = None, mailbox_name: str | None = None
	) -> None:
		"""Move the email message to a specified folder."""

		EmailMessage.move_emails_to_mailbox(self.account, [self.name], mailbox_id, mailbox_role, mailbox_name)

	@frappe.whitelist()
	def mark_as_seen(self) -> None:
		"""Mark the email message as seen."""

		EmailMessage.mark_emails_as_seen(self.account, [self.name])

	@frappe.whitelist()
	def mark_as_unseen(self) -> None:
		"""Mark the email message as unseen."""

		EmailMessage.mark_emails_as_unseen(self.account, [self.name])

	@frappe.whitelist()
	def preload_attachments_to_cache(self) -> None:
		"""Preload attachments to cache."""

		if not self.has_attachment:
			return

		for attachment in self.attachments:
			try:
				EmailMessage.fetch_blob(self.account, attachment.blob_id, attachment._name)
			except Exception:
				frappe.log_error(
					title=_("Failed to load attachment"), message=frappe.get_traceback(with_context=False)
				)

	@frappe.whitelist()
	def get_mime_message(self) -> str:
		"""Returns the MIME message content."""

		if not self.blob_id:
			frappe.throw(_("Email does not have a blob ID."))

		try:
			self.clear_cached_properties()
			return EmailMessage.fetch_blob(self.account, self.blob_id).decode("utf-8")
		except UnicodeDecodeError:
			frappe.throw(_("Failed to decode email content."))
		except Exception:
			frappe.throw(_("Failed to retrieve the MIME message."))


def generate_blob_cache_key(account: str, blob_id: str) -> str:
	"""Returns cache key for blob content."""

	return f"jmap:blob:{account}:{blob_id}"


def store_blob_in_cache(account: str, blob_id: str, content: bytes) -> None:
	"""Cache blob content."""

	cache_key = generate_blob_cache_key(account, blob_id)
	frappe.cache.set_value(cache_key, content, expires_in_sec=BLOB_CACHE_TTL)


def fetch_emails(account: str) -> None:
	"""Fetch emails from the server and create EmailMessage documents."""

	client = get_jmap_client(account)

	try:
		result = client.query_emails(filter={}, limit=1000)
		if email_ids := result.get("ids", []):
			for ids_batch in split_into_batches(email_ids, BATCH_SIZE):
				for email_data in client.get_emails(email_ids=ids_batch):
					create_email_message(account, email_data)
				frappe.db.commit()
	except Exception:
		frappe.log_error(title=_("Failed to fetch emails"), message=frappe.get_traceback(with_context=False))


def split_into_batches(lst: list, size: int) -> list[list]:
	"""Returns a list of lists, each with a maximum size."""

	return [lst[i : i + size] for i in range(0, len(lst), size)]


def create_email_message(account: str, email: dict, do_not_save: bool = False) -> "EmailMessage":
	"""Creates an EmailMessage from the email data."""

	client = get_jmap_client(account)

	email_message: "EmailMessage" = frappe.new_doc("Email Message")
	email_message._id = email["id"]
	email_message.account = account
	email_message.folder = client.get_mailbox_name(list(email["mailboxIds"].keys())[0])
	email_message.subject = email["subject"]
	email_message.sent_at = parse_iso_datetime(email["sentAt"])
	email_message.received_at = parse_iso_datetime(email["receivedAt"])
	email_message.blob_id = email["blobId"]
	email_message.thread_id = email["threadId"]
	email_message.size = email["size"]
	email_message._keywords = json.dumps(email["keywords"], indent=4)
	email_message.has_attachment = cint(email["hasAttachment"])
	email_message.seen = cint(email["keywords"].get("$seen", False))

	# Process sender/from fields
	for key in ["sender", "from"]:
		if email[key]:
			setattr(email_message, f"{key}_name", email[key][0]["name"])
			setattr(email_message, f"{key}_email", email[key][0]["email"])

	# Process recipients
	for key in ["to", "cc", "bcc"]:
		if rcpts := email[key]:
			titled_key = key.title()
			for rcpt in rcpts:
				email_message.append(
					"recipients", {"type": titled_key, "display_name": rcpt["name"], "email": rcpt["email"]}
				)

	# Process reply-to
	if reply_to := email["replyTo"]:
		for rt in reply_to:
			email_message.append("reply_to", {"display_name": rt["name"], "email": rt["email"]})

	# Process html and text bodies
	for key, field in {"htmlBody": "html_body", "textBody": "text_body"}.items():
		if body := email[key]:
			part_id = body[0]["partId"]
			setattr(email_message, field, email["bodyValues"].get(part_id, {}).get("value"))

	# Process message metadata
	for key, field in {"messageId": "message_id", "inReplyTo": "in_reply_to"}.items():
		if email[key]:
			setattr(email_message, field, email[key][0])

	# Process attachments and body parts
	for key, field in {
		"attachments": "attachments",
		"htmlBody": "_html_body",
		"textBody": "_text_body",
	}.items():
		for p in email[key]:
			email_message.append(
				field,
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
				},
			)

	if not do_not_save:
		email_message.insert(ignore_permissions=True)

	return email_message


def get_permission_query_condition(user: str | None = None) -> str:
	user = user or frappe.session.user

	if is_system_manager(user):
		return ""

	if account := get_account_for_user(user):
		return f"(`tabEmail Message`.account = '{account}')"
	else:
		return "1=0"


def has_permission(doc: Document, ptype: str, user: str | None = None) -> bool:
	if doc.doctype != "Email Message":
		return False

	user = user or frappe.session.user
	user_is_system_manager = is_system_manager(user)
	user_is_account_owner = is_account_owner(doc.account, user)

	if user_is_system_manager:
		return True
	elif user_is_account_owner and ptype in ["read", "write", "delete"]:
		return True

	return False

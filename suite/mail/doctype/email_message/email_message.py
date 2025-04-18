# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import hashlib
import json
import re
from functools import cached_property

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, time_diff_in_seconds

from mail.jmap import get_jmap_client
from mail.utils import extract_filter_values
from mail.utils.cache import get_account_for_user
from mail.utils.dt import parse_iso_datetime
from mail.utils.email_parser import EmailParser
from mail.utils.user import is_system_manager

CACHE_TTL = 86400
BLOB_CACHE_TTL = 3600
MAX_ATTACHMENT_SIZE = 25 * 1024 * 1024
BATCH_SIZE = 100


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

		if self.blob_id:
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
	def resolve_user_account_from_filters(filters: list | None = None) -> str | None:
		"""Returns the account associated with the user from the filters."""

		filters = filters or []
		user = frappe.session.user
		account = get_account_for_user(user)

		if is_system_manager(user):
			account_filter = extract_filter_values(filters, [{"account": "="}])
			account = account_filter[0] if account_filter else account

		return account

	@staticmethod
	def get_list(filters: list | None = None, page_length: int = 20, start: int = 0, **kwargs) -> list:
		filters = filters or []
		account = EmailMessage.resolve_user_account_from_filters(filters)

		if not account:
			frappe.msgprint(_("Please select an account to view messages."), alert=True)
			return []

		email_ids = fetch_message_ids_with_cache(account, filter={}, position=start, limit=page_length)
		return fetch_batch_message_data(account, email_ids)

	@staticmethod
	def get_count(filters: list | None = None, **kwargs) -> int:
		filters = filters or []
		account = EmailMessage.resolve_user_account_from_filters(filters)
		return get_cached_message_count(account, filter={}) if account else 0

	@staticmethod
	def get_stats(**kwargs) -> dict:
		return {}

	@staticmethod
	def get_thread(account: str, thread_id: str) -> list[dict] | None:
		"""Returns the email messages in a thread."""

		EmailMessage._validate_permission(account)

		if not thread_id:
			frappe.throw(_("Thread ID is required."))

		client = get_jmap_client(account)
		if email_ids := client.get_threads([thread_id]).get(thread_id):
			return fetch_batch_message_data(account, email_ids)

	@staticmethod
	def _validate_permission(account: str) -> None:
		"""Validate if the user has permission to access the email message."""

		user = frappe.session.user
		if not is_system_manager(user) and account != get_account_for_user(user):
			frappe.throw(_("You do not have permission to view this message."), frappe.PermissionError)

	@staticmethod
	def move_emails_to_folder(
		account: str,
		email_ids: list[str],
		mailbox_id: str | None = None,
		mailbox_role: str | None = None,
		mailbox_name: str | None = None,
	) -> None:
		"""Move emails to a specified folder."""

		EmailMessage._validate_permission(account)

		if not email_ids:
			frappe.throw(_("Email IDs are required."))

		if not mailbox_id and not mailbox_role and not mailbox_name:
			frappe.throw(_("Mailbox role, name, or ID is required."))

		if isinstance(email_ids, str):
			email_ids = [email_ids]

		client = get_jmap_client(account)
		target_mailbox_id = mailbox_id or client.get_mailbox_id(mailbox_role, mailbox_name)

		if not target_mailbox_id:
			frappe.throw(_("Mailbox not found."))

		client.move_emails(email_ids, target_mailbox_id)

		for email_id in email_ids:
			frappe.cache.delete_value(generate_message_cache_key(account, email_id))

	@staticmethod
	def mark_emails_as_seen(account: str, email_ids: list[str]) -> None:
		"""Mark emails as seen."""

		EmailMessage._validate_permission(account)

		if not email_ids:
			frappe.throw(_("Email IDs are required."))

		if isinstance(email_ids, str):
			email_ids = [email_ids]

		client = get_jmap_client(account)
		client.update_emails_keyword(email_ids, "$seen", True)

		for email_id in email_ids:
			frappe.cache.delete_value(generate_message_cache_key(account, email_id))

	@staticmethod
	def mark_emails_as_unseen(account: str, email_ids: list[str]) -> None:
		"""Mark emails as unseen."""

		EmailMessage._validate_permission(account)

		if not email_ids:
			frappe.throw(_("Email IDs are required."))

		if isinstance(email_ids, str):
			email_ids = [email_ids]

		client = get_jmap_client(account)
		client.update_emails_keyword(email_ids, "$seen", False)

		for email_id in email_ids:
			frappe.cache.delete_value(generate_message_cache_key(account, email_id))

	def db_insert(self, *args, **kwargs) -> None:
		raise NotImplementedError

	def load_from_db(self) -> "EmailMessage":
		if "-" not in self.name:
			frappe.throw(_("Name must be in the format {account}-{id}."))

		account, email_id = self.name.split("-", 1)
		EmailMessage._validate_permission(account)

		emails = fetch_batch_message_data(account, [email_id])
		if not emails:
			frappe.throw(
				_("Email Message {0} not found.").format(frappe.bold(f"{account}-{email_id}")),
				frappe.DoesNotExistError,
			)

		return super(Document, self).__init__(emails[0])

	def db_update(self) -> None:
		raise NotImplementedError

	def delete(self) -> None:
		raise NotImplementedError

	def fetch_blob_content(self, blob_id: str, name: str | None = None) -> bytes:
		"""Returns the content of the blob."""

		if not blob_id:
			frappe.throw(_("Blob ID is required."))

		cache_key = generate_blob_cache_key(self.account, blob_id)
		if content := frappe.cache.get_value(cache_key):
			return content

		client = get_jmap_client(self.account)

		try:
			content = client.download_blob(blob_id, name)
			if len(content) > MAX_ATTACHMENT_SIZE:
				frappe.throw(_("Attachment size exceeds maximum allowed limit."))

			store_blob_in_cache(self.account, blob_id, content)
			return content
		except Exception as e:
			frappe.throw(_("Failed to download blob: {0}").format(str(e)))

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

	def fetch_attachment_content(self, cid: str | None = None, blob_id: str | None = None) -> bytes:
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

		return self.fetch_blob_content(attachment.blob_id, attachment._name)

	@frappe.whitelist()
	def move_to_folder(
		self, mailbox_id: str | None = None, mailbox_role: str | None = None, mailbox_name: str | None = None
	) -> None:
		"""Move the email message to a specified folder."""

		account, email_id = self.name.split("-", 1)
		EmailMessage.move_emails_to_folder(account, [email_id], mailbox_id, mailbox_role, mailbox_name)

	@frappe.whitelist()
	def mark_as_seen(self) -> None:
		"""Mark the email message as seen."""

		account, email_id = self.name.split("-", 1)
		EmailMessage.mark_emails_as_seen(account, [email_id])

	@frappe.whitelist()
	def mark_as_unseen(self) -> None:
		"""Mark the email message as unseen."""

		account, email_id = self.name.split("-", 1)
		EmailMessage.mark_emails_as_unseen(account, [email_id])

	@frappe.whitelist()
	def preload_attachments_to_cache(self) -> None:
		"""Preload attachments to cache."""

		if not self.has_attachment:
			return

		for attachment in self.attachments:
			try:
				self.fetch_blob_content(attachment.blob_id, attachment._name)
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
			return self.fetch_blob_content(self.blob_id).decode("utf-8")
		except UnicodeDecodeError:
			frappe.throw(_("Failed to decode email content."))
		except Exception:
			frappe.throw(_("Failed to retrieve the MIME message."))


def fetch_message_ids_with_cache(account: str, filter: dict, position: int = 0, limit: int = 50) -> list[str]:
	"""Returns email IDs with caching."""

	total_emails = get_cached_message_count(account, filter)

	if total_emails == 0 or position >= total_emails:
		return []

	cache_key = generate_message_list_cache_key(account, filter)
	cached_email_ids = frappe.cache.get_value(cache_key)

	if cached_email_ids is not None:
		return cached_email_ids[position : position + limit]

	client = get_jmap_client(account)

	try:
		if total_emails > 1000:
			result = client.query_emails(filter, position, limit)
			store_message_count_in_cache(account, filter, result.get("total", 0))
			return result.get("ids", [])

		result = client.query_emails(filter, 0, total_emails)
		all_email_ids = result.get("ids", [])

		store_message_ids_in_cache(account, filter, all_email_ids)
		store_message_count_in_cache(account, filter, result.get("total", 0))

		return all_email_ids[position : position + limit]
	except Exception:
		frappe.log_error(
			title=_("Failed to get email list"), message=frappe.get_traceback(with_context=False)
		)
		return []


def get_cached_message_count(account: str, filter: dict, force_fresh: bool = False) -> int:
	"""Returns the total count of emails with caching."""

	if not force_fresh:
		cache_key = generate_message_count_cache_key(account, filter)
		cached_total = frappe.cache.get_value(cache_key)

		if cached_total is not None:
			return cint(cached_total)

	client = get_jmap_client(account)

	try:
		result = client.query_emails(filter, position=0, limit=0)
		total = result.get("total", 0)
		store_message_count_in_cache(account, filter, total)
		return total
	except Exception:
		frappe.log_error(
			title=_("Failed to get email count"), message=frappe.get_traceback(with_context=False)
		)
		return 0


def fetch_batch_message_data(account: str, email_ids: list[str]) -> list[dict]:
	"""Returns formatted email data for a batch of emails."""

	email_messages = []
	email_ids_to_fetch = []

	for email_id in email_ids:
		email_message = frappe.cache.get_value(generate_message_cache_key(account, email_id))
		if email_message:
			email_messages.append(email_message)
		else:
			email_ids_to_fetch.append(email_id)

	if email_ids_to_fetch:
		client = get_jmap_client(account)

		try:
			for ids_batch in split_into_batches(email_ids_to_fetch, BATCH_SIZE):
				for email_data in client.get_emails(email_ids=ids_batch):
					email_message = transform_jmap_to_standard_format(account, email_data)
					store_message_in_cache(account, email_data["id"], email_message)
					email_messages.append(email_message)
		except Exception:
			frappe.log_error(
				title=_("Failed to get email data"), message=frappe.get_traceback(with_context=False)
			)

	return email_messages


def split_into_batches(lst: list, size: int) -> list[list]:
	"""Returns a list of lists, each with a maximum size."""

	return [lst[i : i + size] for i in range(0, len(lst), size)]


def clear_message_list_cache(account: str, filter: dict) -> None:
	"""Clear the cache for email list and count."""

	frappe.cache.delete_value(generate_message_list_cache_key(account, filter))
	frappe.cache.delete_value(generate_message_count_cache_key(account, filter))


def generate_message_list_cache_key(account: str, filter: dict) -> str:
	"""Returns cache key for email list."""

	filter_json = json.dumps(filter, sort_keys=True)
	filter_hash = hashlib.sha1(filter_json.encode()).hexdigest()
	return f"jmap:list:{account}:{filter_hash}"


def generate_message_count_cache_key(account: str, filter: dict) -> str:
	"""Returns cache key for email count."""

	filter_json = json.dumps(filter, sort_keys=True)
	filter_hash = hashlib.sha1(filter_json.encode()).hexdigest()
	return f"jmap:list:total:{account}:{filter_hash}"


def generate_message_cache_key(account: str, email_id: str) -> str:
	"""Returns cache key for email message."""

	return f"jmap:email:{account}:{email_id}"


def generate_blob_cache_key(account: str, blob_id: str) -> str:
	"""Returns cache key for blob content."""

	return f"jmap:blob:{account}:{blob_id}"


def store_message_ids_in_cache(account: str, filter: dict, email_ids: list[str]) -> None:
	"""Cache email IDs for a given filter."""

	cache_key = generate_message_list_cache_key(account, filter)
	frappe.cache.set_value(cache_key, email_ids, expires_in_sec=CACHE_TTL)


def store_message_count_in_cache(account: str, filter: dict, total: int = 0) -> None:
	"""Cache the total count of emails for a given filter."""

	cache_key = generate_message_count_cache_key(account, filter)
	frappe.cache.set_value(cache_key, total, expires_in_sec=CACHE_TTL)


def store_message_in_cache(account: str, email_id: str, email_message: dict) -> None:
	"""Cache email message data."""

	cache_key = generate_message_cache_key(account, email_id)
	frappe.cache.set_value(cache_key, email_message, expires_in_sec=CACHE_TTL)


def store_blob_in_cache(account: str, blob_id: str, content: bytes) -> None:
	"""Cache blob content."""

	cache_key = generate_blob_cache_key(account, blob_id)
	frappe.cache.set_value(cache_key, content, expires_in_sec=BLOB_CACHE_TTL)


def transform_jmap_to_standard_format(account: str, email: dict) -> dict:
	"""Transform JMAP email format to standard format."""

	client = get_jmap_client(account)

	email_message = {
		"name": f"{account}-{email['id']}",
		"account": account,
		"folder": client.get_mailbox_name(list(email["mailboxIds"].keys())[0]),
		"subject": email["subject"],
		"preview": (email.get("preview") or "").strip(),
		"sent_at": parse_iso_datetime(email["sentAt"]),
		"received_at": parse_iso_datetime(email["receivedAt"]),
		"blob_id": email["blobId"],
		"thread_id": email["threadId"],
		"size": email["size"],
		"_keywords": json.dumps(email["keywords"], indent=4),
		"has_attachment": cint(email["hasAttachment"]),
		"creation": parse_iso_datetime(email["receivedAt"]),
		"modified": parse_iso_datetime(email["receivedAt"]),
	}

	# Process sender/from fields
	for key in ["sender", "from"]:
		if reply_to := email[key]:
			email_message[f"{key}_name"] = reply_to[0]["name"]
			email_message[f"{key}_email"] = reply_to[0]["email"]

	# Process recipients
	email_message["recipients"] = []
	for key in ["to", "cc", "bcc"]:
		if rcpts := email[key]:
			titled_key = key.title()
			email_message["recipients"].extend(
				[{"type": titled_key, "display_name": rcpt["name"], "email": rcpt["email"]} for rcpt in rcpts]
			)

	# Process reply-to
	if reply_to := email["replyTo"]:
		email_message["reply_to"] = [{"display_name": rt["name"], "email": rt["email"]} for rt in reply_to]

	# Process html and text bodies
	for key, field in {"htmlBody": "html_body", "textBody": "text_body"}.items():
		if body := email[key]:
			part_id = body[0]["partId"]
			email_message[field] = email["bodyValues"].get(part_id, {}).get("value")

	# Process message metadata
	for key, field in {"messageId": "message_id", "inReplyTo": "in_reply_to"}.items():
		if reply_to := email[key]:
			email_message[field] = reply_to[0]

	# Process seen status
	if email["keywords"].get("$seen", False):
		email_message["seen"] = 1

	# Process attachments and body parts
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

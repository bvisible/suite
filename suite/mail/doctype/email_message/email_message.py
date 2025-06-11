# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
import re
from collections import defaultdict
from email.utils import formataddr
from functools import cached_property
from typing import Literal

import frappe
from bs4 import BeautifulSoup
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import Interval, Order
from frappe.query_builder.custom import GROUP_CONCAT
from frappe.query_builder.functions import Max, Now
from frappe.utils import cint, escape_html, time_diff_in_seconds
from pypika import Case
from uuid_utils import uuid7

from mail.jmap import get_jmap_client, get_mailbox_id, get_mailbox_name, get_mailbox_role
from mail.mail.doctype.jmap_sync_state.jmap_sync_state import (
	create_jmap_sync_state,
	get_current_state,
	update_current_state,
)
from mail.mail.doctype.mail_contact.mail_contact import create_mail_contact
from mail.mail.doctype.mail_queue.mail_queue import MailQueue
from mail.utils import convert_html_to_text, enqueue_job, user_context
from mail.utils.cache import get_account_for_user
from mail.utils.dt import parse_iso_datetime
from mail.utils.email_parser import EmailParser
from mail.utils.user import get_account_email_addresses, is_account_owner, is_system_manager
from mail.utils.validation import validate_permission_for_account

BLOB_CACHE_TTL = 3600


class EmailMessage(Document):
	@staticmethod
	def get_threads(
		account: str, mailbox_ids: list[str] | None = None, start: int = 0, limit: int = 50
	) -> list[str]:
		"""Returns the latest email messages in each thread."""

		validate_permission_for_account(account)

		EM = frappe.qb.DocType("Email Message")

		subquery = (
			frappe.qb.from_(EM)
			.select(EM.thread_id, Max(EM.received_at).as_("latest_received_at"))
			.where((EM.account == account) & (EM.destroyed == 0))
			.groupby(EM.thread_id)
		).as_("latest")

		if mailbox_ids:
			subquery = subquery.where(EM.mailbox_id.isin(mailbox_ids))

		query = (
			frappe.qb.from_(EM)
			.join(subquery)
			.on((EM.thread_id == subquery.thread_id) & (EM.received_at == subquery.latest_received_at))
			.select(
				EM.name,
				EM.account,
				EM.thread_id,
				EM.from_name,
				EM.from_email,
				EM.subject,
				Case().when(EM.html_body.isnotnull(), EM.html_body).else_(EM.text_body).as_("preview"),
				EM.has_attachment,
				EM.received_at,
				EM.seen,
				EM.draft,
				EM.flagged,
				EM.answered,
				EM.forwarded,
			)
			.where((EM.account == account) & (EM.destroyed == 0))
			.orderby(EM.received_at, order=frappe.qb.desc)
			.offset(start)
			.limit(limit)
		)

		if mailbox_ids:
			query = query.where(EM.mailbox_id.isin(mailbox_ids))

		messages = query.run(as_dict=True)

		for message in messages:
			if preview := message.get("preview"):
				message["preview"] = convert_html_to_text(preview)

		attachments_map = {}
		if messages_with_attachment := [m["name"] for m in messages if m["has_attachment"]]:
			PART = frappe.qb.DocType("Email Message Part")
			attachments = (
				frappe.qb.from_(PART)
				.select(
					PART.parent,
					PART.filename,
					PART.type,
					PART.size,
					PART.disposition,
					PART.blob_id,
				)
				.where(
					(PART.parenttype == "Email Message")
					& (PART.parentfield == "attachments")
					& (PART.parent.isin(messages_with_attachment))
				)
			).run(as_dict=True)

			attachments_map = defaultdict(list)
			for a in attachments:
				if not a.filename:
					if a.type == "message/delivery-status":
						a.filename = "Delivery Report"
					elif a.type == "message/rfc822":
						a.filename = "Original Message"
				attachments_map[a.pop("parent")].append(a)

		if attachments_map:
			for message in messages:
				if message["has_attachment"]:
					message["attachments"] = attachments_map.get(message["name"], [])
				else:
					message["attachments"] = []

		return messages

	@staticmethod
	def get_message_ids(account: str, thread_ids: list[str], mailbox_id: str | None = None) -> list[str]:
		"""Returns the message IDs for the given threads."""

		if not account or not thread_ids:
			frappe.throw(_("Account and thread IDs are required."))

		validate_permission_for_account(account)

		filters = {"account": account, "thread_id": ["in", thread_ids], "destroyed": 0}
		if mailbox_id:
			filters["mailbox_id"] = mailbox_id

		return frappe.get_all("Email Message", filters, pluck="name")

	@staticmethod
	def get_thread_messages(account: str, thread_id: str) -> list["EmailMessage"]:
		"""Returns the email messages in a thread."""

		messages = []
		for message_id in EmailMessage.get_message_ids(account, [thread_id]):
			email_message = frappe.get_doc("Email Message", message_id)
			messages.append(email_message)

		return messages

	@staticmethod
	def move_emails_to_mailbox(
		account: str,
		message_ids: list[str],
		mailbox_id: str | None = None,
		mailbox_role: str | None = None,
	) -> None:
		"""Move emails to a specified mailbox."""

		if not account or not message_ids or not (mailbox_id or mailbox_role):
			frappe.throw(_("Account, message IDs, and mailbox ID/role/name are required."))

		validate_permission_for_account(account)

		filters = {"account": account, "name": ["in", message_ids], "destroyed": 0}
		emails_to_move = frappe.db.get_all("Email Message", filters, ["_id", "mailbox_id"], as_list=True)

		if not emails_to_move:
			return

		target_mailbox_id = mailbox_id or get_mailbox_id(account, role=mailbox_role)

		if not target_mailbox_id:
			frappe.throw(_("Mailbox not found."))

		try:
			client = get_jmap_client(account)
			client.email_set_mailbox(list(emails_to_move), target_mailbox_id)
			target_mailbox_role = mailbox_role or get_mailbox_role(account, target_mailbox_id)
			target_mailbox_name = get_mailbox_name(account, target_mailbox_id)

			# This database update could potentially cause a deadlock.
			frappe.db.set_value(
				"Email Message",
				filters,
				{
					"mailbox_id": target_mailbox_id,
					"mailbox_role": target_mailbox_role,
					"folder": target_mailbox_name,
				},
			)
		except Exception:
			frappe.log_error(
				title=_("Failed to move email(s) to mailbox"),
				message=frappe.get_traceback(with_context=True),
			)
			frappe.throw(_("Failed to move email(s) to mailbox."))

	@staticmethod
	def mark_emails_as_seen_unseen(account: str, message_ids: list[str], seen: bool) -> None:
		"""Mark emails as seen or unseen."""

		EmailMessage._update_emails_keyword(account, message_ids, "$seen", seen, "seen")

	@staticmethod
	def mark_emails_as_flagged_unflagged(account: str, message_ids: list[str], flagged: bool) -> None:
		"""Mark emails as flagged or unflagged."""

		EmailMessage._update_emails_keyword(account, message_ids, "$flagged", flagged, "flagged")

	@staticmethod
	def destroy_emails(account: str, message_ids: list[str]) -> None:
		"""Delete emails from the server and mark them as destroyed."""

		if not account or not message_ids:
			frappe.throw(_("Account and message IDs are required."))

		validate_permission_for_account(account)

		filters = {"account": account, "name": ["in", message_ids], "destroyed": 0}
		email_ids = frappe.db.get_all("Email Message", filters, pluck="_id")

		if not email_ids:
			return

		try:
			client = get_jmap_client(account)
			client.email_set_destroy(email_ids)

			# This database update could potentially cause a deadlock.
			frappe.db.set_value("Email Message", filters, "destroyed", 1)
		except Exception:
			frappe.log_error(
				title=_("Failed to destroy email(s)"),
				message=frappe.get_traceback(with_context=True),
			)
			frappe.throw(_("Failed to destroy email(s)."))

	@staticmethod
	def fetch_blob(account: str, blob_id: str, name: str | None = None) -> bytes:
		"""Fetch the content of a blob."""

		if not account or not blob_id:
			frappe.throw(_("Account and blob ID are required."))

		validate_permission_for_account(account)

		cache_key = EmailMessage._get_blob_cache_key(account, blob_id)
		if content := frappe.cache.get_value(cache_key):
			return content

		try:
			client = get_jmap_client(account)
			content = client.download_blob(blob_id, name)
			EmailMessage._store_blob_in_cache(account, blob_id, content)
			return content
		except Exception:
			frappe.log_error(
				title=_("Failed to fetch blob"),
				message=frappe.get_traceback(with_context=True),
			)
			frappe.throw(_("Failed to fetch blob."))

	@staticmethod
	def _update_emails_keyword(
		account: str, message_ids: list[str], keyword: str, value: bool, db_field: str
	) -> None:
		"""Update email keywords and document field."""

		if not account or not message_ids:
			frappe.throw(_("Account and message IDs are required."))

		validate_permission_for_account(account)

		email_id_keywords_map = {}
		message_id_keywords_map = {}

		for d in frappe.db.get_all(
			"Email Message",
			{"account": account, "name": ["in", message_ids], "destroyed": 0},
			["name", "_id", "_keywords"],
		):
			name, _id, _keywords = d.values()
			_keywords = json.loads(_keywords)
			_keywords.update({keyword: value})
			email_id_keywords_map[_id] = _keywords
			message_id_keywords_map[name] = _keywords

		if not email_id_keywords_map:
			return

		try:
			client = get_jmap_client(account)
			client.email_set_keywords(email_id_keywords_map)

			# This database update could potentially cause a deadlock.
			for message_id, _keywords in message_id_keywords_map.items():
				frappe.db.set_value(
					"Email Message",
					message_id,
					{db_field: cint(value), "_keywords": json.dumps(_keywords)},
				)
		except Exception:
			frappe.log_error(
				title=_("Failed to update email(s)"),
				message=frappe.get_traceback(with_context=True),
			)
			frappe.throw(_("Failed to update email(s)."))

	@staticmethod
	def _create_or_update_from_email_data(account: str, email_data: dict) -> None:
		"""Create or update an EmailMessage document from JMAP email data."""

		notify = False
		email_message = EmailMessage._create_from_email_data(account, email_data, do_not_save=True)

		try:
			email_message.insert(ignore_permissions=True)
			notify = True
		except frappe.UniqueValidationError:
			if email_message_name := frappe.db.get_value(
				"Email Message", {"account": account, "_id": email_data["id"]}, "name"
			):
				email_message = frappe.get_doc("Email Message", email_message_name)
				email_message = EmailMessage._create_from_email_data(
					account, email_data, email_message, do_not_save=True
				)
				email_message.flags.notify_update = True
				email_message.save(ignore_permissions=True)
				notify = True

		if notify:
			frappe.publish_realtime(
				"mail_created_or_updated", email_message.mailbox_role, user=email_message.account
			)

	@staticmethod
	def _create_from_email_data(
		account: str, email_data: dict, email_message: "EmailMessage" = None, do_not_save: bool = False
	) -> "EmailMessage":
		"""Create an EmailMessage document from JMAP email data."""

		email_message: "EmailMessage" = email_message or frappe.new_doc("Email Message")
		email_message._id = email_data["id"]
		email_message.account = account
		email_message.mailbox_id = list(email_data["mailboxIds"].keys())[0]
		email_message.mailbox_role = get_mailbox_role(account, email_message.mailbox_id)
		email_message.folder = get_mailbox_name(account, email_message.mailbox_id)
		email_message.subject = email_data["subject"]
		email_message.sent_at = parse_iso_datetime(email_data["sentAt"])
		email_message.received_at = parse_iso_datetime(email_data["receivedAt"])
		email_message.blob_id = email_data["blobId"]
		email_message.thread_id = email_data["threadId"]
		email_message.size = email_data["size"]
		email_message._keywords = json.dumps(email_data["keywords"])
		email_message.has_attachment = cint(email_data["hasAttachment"])

		for key in ["draft", "seen", "flagged", "answered", "forwarded"]:
			setattr(email_message, key, cint(email_data["keywords"].get(f"${key}", False)))

		# Process sender/from fields
		for key in ["sender", "from"]:
			if email_data[key]:
				setattr(email_message, f"{key}_name", email_data[key][0]["name"])
				setattr(email_message, f"{key}_email", email_data[key][0]["email"])

		# Process recipients
		email_message.recipients = []
		for key in ["to", "cc", "bcc"]:
			if rcpts := email_data[key]:
				titled_key = key.title()
				for rcpt in rcpts:
					email_message.append(
						"recipients",
						{"type": titled_key, "display_name": rcpt["name"], "email": rcpt["email"]},
					)

		# Process reply-to
		email_message.reply_to = []
		if reply_to := email_data["replyTo"]:
			for rt in reply_to:
				email_message.append("reply_to", {"display_name": rt["name"], "email": rt["email"]})

		# Process html and text bodies
		for key, field in {"htmlBody": "html_body", "textBody": "text_body"}.items():
			if body := email_data[key]:
				part_id = body[0]["partId"]
				setattr(email_message, field, email_data["bodyValues"].get(part_id, {}).get("value"))

		# Process message metadata
		for key, field in {"messageId": "message_id", "inReplyTo": "in_reply_to"}.items():
			if email_data[key]:
				setattr(email_message, field, email_data[key][0])

		# Process attachments and body parts
		for key, field in {
			"attachments": "attachments",
			"htmlBody": "_html_body",
			"textBody": "_text_body",
		}.items():
			setattr(email_message, field, [])
			for p in email_data[key]:
				email_message.append(
					field,
					{
						"part_id": p["partId"],
						"blob_id": p["blobId"],
						"size": p["size"],
						"filename": p["name"],
						"type": p["type"],
						"charset": p["charset"],
						"disposition": p["disposition"],
						"cid": p["cid"],
						"language": str(p["language"]),
						"location": p["location"],
					},
				)

		email_message.flags.fetched_from_server = True

		if not do_not_save:
			email_message.insert(ignore_permissions=True)

		return email_message

	@staticmethod
	def _patch_from_email_data(account: str, email_data: dict) -> None:
		"""Patch the EmailMessage document with updated JMAP email data."""

		_id = email_data["id"]

		mailbox_id = list(email_data["mailboxIds"].keys())[0]
		mailbox_role = get_mailbox_role(account, mailbox_id)
		folder = get_mailbox_name(account, mailbox_id)

		_keywords = json.dumps(email_data["keywords"])
		draft = cint(email_data["keywords"].get("$draft", False))
		seen = cint(email_data["keywords"].get("$seen", False))
		flagged = cint(email_data["keywords"].get("$flagged", False))
		answered = cint(email_data["keywords"].get("$answered", False))
		forwarded = cint(email_data["keywords"].get("$forwarded", False))

		filters = {"account": account, "_id": _id, "destroyed": 0}
		frappe.db.set_value(
			"Email Message",
			filters,
			{
				"mailbox_id": mailbox_id,
				"mailbox_role": mailbox_role,
				"folder": folder,
				"_keywords": _keywords,
				"draft": draft,
				"seen": seen,
				"flagged": flagged,
				"answered": answered,
				"forwarded": forwarded,
			},
		)

	@staticmethod
	def _store_blob_in_cache(account: str, blob_id: str, content: bytes) -> None:
		"""Cache blob content."""

		cache_key = EmailMessage._get_blob_cache_key(account, blob_id)
		frappe.cache.set_value(cache_key, content, expires_in_sec=BLOB_CACHE_TTL)

	@staticmethod
	def _get_blob_cache_key(account: str, blob_id: str) -> str:
		"""Returns cache key for blob content."""

		return f"jmap:blob:{account}:{blob_id}"

	@property
	def to(self) -> list[dict[str, str | None]]:
		"""Returns the recipients in the To field."""

		return self._get_recipients("To")

	@property
	def cc(self) -> list[dict[str, str | None]]:
		"""Returns the recipients in the Cc field."""

		return self._get_recipients("Cc")

	@property
	def bcc(self) -> list[dict[str, str | None]]:
		"""Returns the recipients in the Bcc field."""

		return self._get_recipients("Bcc")

	@property
	def received_after(self) -> float:
		"""Returns the time difference in seconds between received and sent time."""

		return time_diff_in_seconds(self.received_at, self.sent_at)

	@property
	def fetched_after(self) -> float:
		"""Returns the time difference in seconds between creation and received time."""

		return time_diff_in_seconds(self.creation, self.received_at)

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
	def keywords(self) -> str | None:
		"""Returns the indented JSON keywords."""

		return json.dumps(json.loads(self._keywords), indent=4) if self._keywords else None

	@property
	def message(self) -> str | None:
		"""Returns the message content if available."""

		cache_key = EmailMessage._get_blob_cache_key(self.account, self.blob_id)
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

	@cached_property
	def email_type(self) -> str:
		"""Returns the type of email (Sent or Received)."""

		email_type = "Received"
		user_addresses = get_account_email_addresses(self.account)

		if self.from_email in user_addresses or self.sender_email in user_addresses:
			email_type = "Sent"

		return email_type

	def autoname(self) -> None:
		self.name = str(uuid7())

	def after_insert(self) -> None:
		self.create_mail_contacts()

	def on_trash(self) -> None:
		if not self.destroyed:
			frappe.throw(_("You must destroy this email message before it can be deleted."))

	def create_mail_contacts(self) -> None:
		"""Creates Mail Contacts."""

		user, create_contact = frappe.db.get_value(
			"Mail Account", self.account, ["user", "create_mail_contact"]
		)

		if create_contact:
			for rcpt in self.recipients:
				create_mail_contact(user, rcpt.email, rcpt.display_name)

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

	def validate_draft(self) -> None:
		"""Raise an exception if the email message is a draft."""

		if self.draft:
			frappe.throw(
				_("Email Message {0} is a draft. Please send it before performing this action.").format(
					frappe.bold(self.name)
				)
			)

	def validate_destroyed(self) -> None:
		"""Raise an exception if the email message is destroyed."""

		if self.destroyed:
			frappe.throw(
				_("Email Message {0} has been destroyed and will be permanently removed soon.").format(
					frappe.bold(self.name)
				)
			)

	def fetch_attachment(self, cid: str | None = None, blob_id: str | None = None) -> bytes:
		"""Returns the content of an attachment."""

		self.validate_destroyed()

		if not any([self.attachments, self._html_body, self._text_body]):
			frappe.throw(_("Email does not have any attachments."))

		if not cid and not blob_id:
			frappe.throw(_("Either cid or blob_id is required."))

		attachment = next(
			(a for a in self.attachments if (cid and a.cid == cid) or (blob_id and a.blob_id == blob_id)),
			None,
		)

		if not attachment:
			attachment = next(
				(
					p
					for p in self._html_body + self._text_body
					if (p.disposition == "inline")
					and ((cid and p.cid == cid) or (blob_id and p.blob_id == blob_id))
				),
				None,
			)

		if not attachment:
			frappe.throw(_("Attachment not found."))

		return EmailMessage.fetch_blob(self.account, attachment.blob_id, attachment.filename)

	@frappe.whitelist()
	def save_draft(self) -> None:
		"""Save the email message as a draft."""

		self._update_or_submit_draft(save_as_draft=True)

	@frappe.whitelist()
	def submit(self) -> None:
		"""Submit the draft email message."""

		self._update_or_submit_draft(save_as_draft=False)

	@frappe.whitelist()
	def destroy(self) -> None:
		"""Destroy the email message."""

		if self.destroyed:
			frappe.throw(_("Email Message {0} has already been destroyed.").format(frappe.bold(self.name)))

		EmailMessage.destroy_emails(self.account, [self.name])

	@frappe.whitelist()
	def move_to_mailbox(self, mailbox_id: str | None = None, mailbox_role: str | None = None) -> None:
		"""Move the email message to a specified folder."""

		self.validate_draft()
		self.validate_destroyed()
		EmailMessage.move_emails_to_mailbox(self.account, [self.name], mailbox_id, mailbox_role)
		self.reload()

	@frappe.whitelist()
	def set_seen(self, seen: bool) -> None:
		"""Mark the email message as seen or unseen."""

		self.validate_destroyed()
		EmailMessage.mark_emails_as_seen_unseen(self.account, [self.name], seen)
		self.reload()

	@frappe.whitelist()
	def set_flagged(self, flagged: bool) -> None:
		"""Mark the email message as flagged or unflagged."""

		self.validate_destroyed()
		EmailMessage.mark_emails_as_flagged_unflagged(self.account, [self.name], flagged)
		self.reload()

	@frappe.whitelist()
	def reply(self) -> "MailQueue":
		"""Reply to the email message."""

		recipients = []

		if self.email_type == "Sent":
			# To = original To
			for rcpt in self.recipients:
				if rcpt.type == "To":
					recipients.append(
						{"type": rcpt.type, "display_name": rcpt.display_name, "email": rcpt.email}
					)

		elif self.email_type == "Received":
			# To = Reply-To if present, else From
			if self.reply_to:
				recipients.append(
					{"type": "To", "display_name": rt.display_name, "email": rt.email} for rt in self.reply_to
				)
			else:
				recipients.append({"type": "To", "display_name": self.from_name, "email": self.from_email})

		return self._reply(recipients)

	@frappe.whitelist()
	def reply_all(self) -> "MailQueue":
		"""Reply to all recipients of the email message."""

		recipients = []

		if self.email_type == "Sent":
			# To = original To
			# Cc = original Cc
			for rcpt in self.recipients:
				if rcpt.type in ["To", "Cc"]:
					recipients.append(
						{"type": rcpt.type, "display_name": rcpt.display_name, "email": rcpt.email}
					)

		elif self.email_type == "Received":
			# To = Reply-To if present, else From
			if self.reply_to:
				recipients.append(
					{"type": "To", "display_name": rt.display_name, "email": rt.email} for rt in self.reply_to
				)
			else:
				recipients.append({"type": "To", "display_name": self.from_name, "email": self.from_email})

			# Cc = (original To + original Cc) minus user addresses
			user_addresses = get_account_email_addresses(self.account)
			for rcpt in self.recipients:
				if rcpt.type in ["To", "Cc"] and rcpt.email not in user_addresses:
					recipients.append({"type": "Cc", "display_name": rcpt.display_name, "email": rcpt.email})

		return self._reply(recipients)

	@frappe.whitelist()
	def forward(self) -> "MailQueue":
		"""Forward the email message."""

		self.validate_draft()
		self.validate_destroyed()

		formatted_sent_at = self.sent_at.strftime("%a, %B %-d, %Y at %-I:%M %p")
		forward_html_body = (
			"<p>---------- Forwarded message ---------</p>"
			'<table border="0" cellpadding="0" cellspacing="10">'
			f"<tr><td><b>From:</b></td><td>{escape_html(formataddr([self.from_name, self.from_email]))}</td></tr>"
			f"<tr><td><b>Date:</b></td><td>{formatted_sent_at}</td></tr>"
			f"<tr><td><b>Subject:</b></td><td>{self.subject}</td></tr>"
		)
		forward_text_body = (
			"---------- Forwarded message ---------\n"
			f"From: {formataddr([self.from_name, self.from_email])}\n"
			f"Date: {formatted_sent_at}\n"
			f"Subject: {self.subject}\n"
		)

		if to := ", ".join(
			[formataddr([rcpt["name"], rcpt["email"]]) for rcpt in self._get_recipients("To")]
		):
			forward_html_body += f"<tr><td><b>To:</b></td><td>{escape_html(to)}</td></tr>"
			forward_text_body += f"To: {to}\n"
		if cc := ", ".join(
			[formataddr([rcpt["name"], rcpt["email"]]) for rcpt in self._get_recipients("Cc")]
		):
			forward_html_body += f"<tr><td><b>Cc:</b></td><td>{escape_html(cc)}</td></tr>"
			forward_text_body += f"Cc: {cc}\n"

		original_html_body = self.html_body or ""
		original_text_body = self.text_body or ""

		quoted_html_body = f'<blockquote style="border-left:2px solid #ccc; margin-left:0; padding-left:1em;">{original_html_body}</blockquote>'
		quoted_text_body = "\n> ".join(original_text_body.strip().splitlines())

		forward_html_body += f"</table><br/> {quoted_html_body}"
		forward_html_body = BeautifulSoup(forward_html_body, "html.parser").prettify()
		forward_text_body += f"\n\n> {quoted_text_body}"

		attachments = [
			{
				"file_url": a.file_url,
				"blob_id": a.blob_id,
				"type": a.type,
				"size": a.size,
				"filename": a.filename,
				"disposition": a.disposition,
				"cid": a.cid,
			}
			for a in self.attachments
		]

		for body_part in self._html_body + self._text_body:
			if body_part.disposition == "inline":
				attachments.append(
					{
						"blob_id": body_part.blob_id,
						"type": body_part.type,
						"size": body_part.size,
						"filename": body_part.filename,
						"disposition": body_part.disposition,
						"cid": body_part.cid,
					}
				)

		return MailQueue._create(
			account=self.account,
			subject=f"Fwd: {self.subject}" if not self.subject.lower().startswith("fwd:") else self.subject,
			html_body=forward_html_body,
			text_body=forward_text_body,
			attachments=attachments,
			forwarded_from_id=self._id,
			do_not_save=True,
		)

	@frappe.whitelist()
	def preload_attachments_to_cache(self, include_inline: bool = True, include_regular: bool = True) -> None:
		"""Preload attachments to cache."""

		if not any([self.attachments, self._html_body, self._text_body]):
			return

		self.validate_destroyed()

		for attachment in self.attachments:
			if (include_inline and attachment.disposition == "inline") or (
				include_regular and attachment.disposition == "attachment"
			):
				EmailMessage.fetch_blob(self.account, attachment.blob_id, attachment.filename)

		if include_inline:
			for body_part in self._html_body + self._text_body:
				if body_part.disposition == "inline":
					EmailMessage.fetch_blob(self.account, body_part.blob_id, body_part.filename)

	@frappe.whitelist()
	def get_mime_message(self) -> str:
		"""Returns the MIME message content."""

		self.validate_destroyed()

		if not self.blob_id:
			frappe.throw(_("Email does not have a blob ID."))

		self.clear_cached_properties()
		return EmailMessage.fetch_blob(self.account, self.blob_id).decode("utf-8")

	def _get_recipients(self, type: Literal["To", "Cc", "Bcc"] | None = None) -> list[dict[str, str | None]]:
		"""Returns the recipients."""

		recipients = []
		for rcpt in self.recipients:
			if type and rcpt.type != type:
				continue

			recipients.append({"name": rcpt.display_name, "email": rcpt.email})

		return recipients

	def _update_or_submit_draft(self, save_as_draft: bool = True) -> None:
		"""Update or submit the draft email message."""

		self.validate_destroyed()

		if not self.draft:
			frappe.throw(_("Email Message {0} is not a draft.").format(frappe.bold(self.name)))

		recipients = [
			{"type": rcpt.type, "display_name": rcpt.display_name, "email": rcpt.email}
			for rcpt in self.recipients
		]
		reply_to = [{"display_name": rt.display_name, "email": rt.email} for rt in self.reply_to]
		attachments = [
			{
				"file_url": a.file_url,
				"blob_id": a.blob_id,
				"type": a.type,
				"size": a.size,
				"filename": a.filename,
				"disposition": a.disposition,
				"cid": a.cid,
			}
			for a in self.attachments
		]

		for body_part in self._html_body + self._text_body:
			if body_part.disposition == "inline":
				attachments.append(
					{
						"blob_id": body_part.blob_id,
						"type": body_part.type,
						"size": body_part.size,
						"filename": body_part.filename,
						"disposition": body_part.disposition,
						"cid": body_part.cid,
					}
				)

		MailQueue._create(
			account=self.account,
			from_name=self.from_name,
			from_email=self.from_email,
			subject=self.subject,
			reply_to=reply_to,
			recipients=recipients,
			attachments=attachments,
			html_body=self.html_body,
			text_body=self.text_body,
			message_id=self.message_id,
			_id=self._id,
			in_reply_to=self.in_reply_to,
			save_as_draft=save_as_draft,
		)

	def _reply(self, recipients: list[dict]) -> "MailQueue":
		"""Returns a unsaved EmailMessage object for replying to the email message."""

		self.validate_draft()
		self.validate_destroyed()

		return MailQueue._create(
			account=self.account,
			subject=f"Re: {self.subject}" if not self.subject.lower().startswith("re:") else self.subject,
			recipients=recipients,
			in_reply_to=self.message_id,
			in_reply_to_id=self._id,
			do_not_save=True,
		)


@frappe.whitelist()
def bulk_destroy(names: str | list[str]) -> None:
	"""Destroys the email messages."""

	if isinstance(names, str):
		names = json.loads(names)

	EM = frappe.qb.DocType("Email Message")
	query = (
		frappe.qb.from_(EM)
		.select(
			EM.account,
			GROUP_CONCAT(EM.name).as_("message_ids"),
		)
		.where((EM.destroyed == 0) & (EM.name.isin(names)))
		.groupby(EM.account)
	)

	for row in query.run(as_dict=True):
		EmailMessage.destroy_emails(row["account"], row["message_ids"].split(","))

	frappe.msgprint(_("Email messages destroyed successfully."), alert=True)


@frappe.whitelist()
def reply(source_name: str, target_doc=None) -> "MailQueue":
	"""Reply to the email message."""

	source_doc = frappe.get_doc("Email Message", source_name)
	return source_doc.reply()


@frappe.whitelist()
def reply_all(source_name: str, target_doc=None) -> "MailQueue":
	"""Reply to all recipients of the email message."""

	source_doc = frappe.get_doc("Email Message", source_name)
	return source_doc.reply_all()


@frappe.whitelist()
def forward(source_name: str, target_doc=None) -> "MailQueue":
	"""Forward the email message."""

	source_doc = frappe.get_doc("Email Message", source_name)
	return source_doc.forward()


def fetch_emails(account: str, position: int = 0, batch_size: int = 1000) -> None:
	"""Fetch all emails from the server and create EmailMessage documents."""

	if bool(get_current_state(account)):
		frappe.throw(
			_("Account {0} already synced. Use <code>fetch_changes</code> to update.").format(
				frappe.bold(account)
			)
		)
	elif not bool(frappe.db.exists("JMAP Sync State", account)):
		create_jmap_sync_state(account)

	try:
		client = get_jmap_client(account)
		result = client.email_query(filter={}, position=position, limit=batch_size)

		if email_ids := result["ids"]:
			emails, state = client.email_get(email_ids)
			for email_data in emails:
				EmailMessage._create_or_update_from_email_data(account, email_data)

			if result["total"] > batch_size:
				fetch_emails(account, position + batch_size, batch_size)

			update_current_state(account, state)
	except Exception:
		frappe.log_error(
			title=_("Failed to fetch emails"),
			message=frappe.get_traceback(with_context=True),
		)


def fetch_changes(account: str, email_states: list[str] | None = None) -> None:
	"""Fetch changes from the server and update EmailMessage documents."""

	current_state = get_current_state(account)

	if not current_state:
		return fetch_emails(account)
	elif email_states and current_state in email_states:
		return

	try:
		client = get_jmap_client(account)
		result = client.email_changes(current_state)

		if created_ids := result["created"]:
			for email_data in client.email_get(created_ids)[0]:
				try:
					EmailMessage._create_or_update_from_email_data(account, email_data)
				except Exception:
					frappe.log_error(
						title=_("Failed to process created email"),
						message=frappe.get_traceback(with_context=True),
					)

		if updated_ids := result["updated"]:
			properties = ["id", "mailboxIds", "keywords"]
			for email_data in client.email_get(updated_ids, properties=properties)[0]:
				EmailMessage._patch_from_email_data(account, email_data)

		if destroyed_ids := result["destroyed"]:
			filters = {"account": account, "_id": ["in", destroyed_ids], "destroyed": 0}
			frappe.db.set_value("Email Message", filters, "destroyed", 1)

		new_state = result["newState"]
		update_current_state(account, new_state)

		if result["hasMoreChanges"]:
			fetch_changes(account)
	except Exception:
		frappe.log_error(
			title=_("Failed to fetch changes"),
			message=frappe.get_traceback(with_context=True),
		)


def enqueue_fetch_changes(account: str, request_data: dict | None = None) -> None:
	"""Enqueue the fetch_changes job for the specified account."""

	email_states = None
	if request_data:
		email_states = list(
			set([s["Email"] for s in list(request_data["changed"].values()) if s.get("Email")])
		)

	with user_context("Administrator"):
		job_id = f"fetch_changes:{account}"
		enqueue_job(
			fetch_changes,
			account=account,
			email_states=email_states,
			queue="short",
			job_id=job_id,
			deduplicate=True,
			enqueue_after_commit=True,
		)


def schedule_fetch_changes() -> None:
	"""Scheduled job to fetch changes for accounts that haven't been synced in the last 3 hours."""

	SYNC_STATE = frappe.qb.DocType("JMAP Sync State")
	accounts = (
		frappe.qb.from_(SYNC_STATE)
		.select(SYNC_STATE.account)
		.where(SYNC_STATE.last_synced_at.isnull() | SYNC_STATE.last_synced_at < (Now() - Interval(hours=3)))
	).run(pluck="account")

	if accounts:
		for account in accounts:
			enqueue_fetch_changes(account)


def delete_destroyed_emails() -> None:
	"""Called by the scheduler to delete destroyed emails."""

	try:
		for message in frappe.db.get_all("Email Message", {"destroyed": 1}, pluck="name"):
			frappe.delete_doc("Email Message", message, ignore_permissions=True, delete_permanently=True)
	except Exception:
		frappe.log_error(
			title=_("Failed to delete destroyed emails"), message=frappe.get_traceback(with_context=True)
		)


def get_permission_query_condition(user: str | None = None) -> str:
	user = user or frappe.session.user

	if is_system_manager(user):
		return ""

	if account := get_account_for_user(user):
		return f"(`tabEmail Message`.account = '{account}') AND (`tabEmail Message`.destroyed = 0)"
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
	elif user_is_account_owner and ptype in ["read", "write", "delete"] and not doc.destroyed:
		return True

	return False


def on_doctype_update() -> None:
	frappe.db.add_unique("Email Message", ["account", "_id"], constraint_name="unique_email_message")

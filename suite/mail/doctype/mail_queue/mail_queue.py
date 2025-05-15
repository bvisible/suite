# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
from email import message_from_string
from email.utils import make_msgid, parseaddr
from mimetypes import guess_type
from pathlib import Path
from typing import Literal

import frappe
from frappe import _
from frappe.core.doctype.file.utils import find_file_by_url
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now
from frappe.utils import cint, get_datetime_str, random_string, time_diff_in_seconds
from uuid_utils import uuid7

from mail.jmap import get_identities, get_jmap_client, get_mailbox_id
from mail.utils.cache import get_account_for_email, get_account_for_user
from mail.utils.dt import convert_to_utc, parsedate_to_datetime
from mail.utils.user import get_account_email_addresses, is_account_owner, is_system_manager


class MailQueue(Document):
	@staticmethod
	def clear_old_logs(days: int = 3) -> None:
		MAIL_QUEUE = frappe.qb.DocType("Mail Queue")
		query = (
			frappe.qb.from_(MAIL_QUEUE)
			.select(MAIL_QUEUE.name)
			.where(
				(MAIL_QUEUE.status.isin(["Draft", "Submitted"]))
				& (MAIL_QUEUE.creation < (Now() - Interval(days=days)))
			)
		)

		for doc in query.run(pluck="name"):
			frappe.delete_doc("Mail Queue", doc)

	@property
	def received_after(self) -> int:
		"""Returns the time difference in seconds between received and sent time."""

		return time_diff_in_seconds(self.creation, self.sent_at)

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
	def identity_id(self) -> str:
		for identity in get_identities(self.account):
			if identity["email"] == self.from_email:
				return identity["id"]

		frappe.throw(_("Identity not found for email {0}").format(self.from_email))

	@property
	def response(self) -> str | None:
		"""Returns the indented JSON response."""

		return json.dumps(json.loads(self._response), indent=4) if self._response else None

	@property
	def error_message(self) -> str | None:
		"""Returns the error message."""

		if not self._response or self.status not in ["Failed to Draft", "Failed to Submit"]:
			return None

		response = json.loads(self._response)

		data = None
		if self.status == "Failed to Draft":
			data = response["methodResponses"][0][1].get("notCreated", {}).get(f"draft-{self.name}")
		elif self.status == "Failed to Submit":
			data = response["methodResponses"][1][1].get("notCreated", {}).get(f"submit-{self.name}")

		if data:
			message = f"{data['type']}: {data['description']}"

			if data.get("properties"):
				message += f" ({', '.join(data['properties'])})"

			return message

	def autoname(self) -> None:
		self.name = str(uuid7())

	def validate(self) -> None:
		self.validate_raw_message()
		self.validate_from_name()
		self.validate_from_email()
		self.validate_delivery_option()
		self.validate_recipients()
		self.validate_attachments()
		self.validate_message_id()
		self.validate_sent_at()
		self.validate_in_reply_to()

	def after_insert(self) -> None:
		self.submit()

	def validate_raw_message(self) -> None:
		"""Validates the raw message."""

		if not self.raw_message:
			return

		self.from_name = None
		self.from_email = None
		self.subject = None
		self.reply_to = []
		self.headers = []
		self.html_body = None
		self.text_body = None
		self.attachments = []
		self.message_id = None
		self.sent_at = None
		self.in_reply_to = None

		message = message_from_string(self.raw_message)
		if from_header := message.get("From"):
			self.from_name, self.from_email = parseaddr(from_header)

			if self.from_email not in get_account_email_addresses(self.account):
				self.from_email = None

		if not self.recipients:
			for rcpt_type in ["To", "Cc", "Bcc"]:
				if _rcpt := message.get(rcpt_type):
					for rcpt in _rcpt.split(","):
						self.append(
							"recipients",
							{
								"type": rcpt_type,
								"display_name": parseaddr(rcpt)[0],
								"email": parseaddr(rcpt)[1],
							},
						)

		if date_header := message.get("Date"):
			self.sent_at = get_datetime_str(parsedate_to_datetime(date_header))

	def validate_from_name(self) -> None:
		"""Validates the from name."""

		if not self.from_name:
			self.from_name = frappe.db.get_value("Mail Account", self.account, "display_name")

	def validate_from_email(self) -> None:
		"""Validates the from email."""

		if self.from_email:
			if self.account != get_account_for_email(self.from_email):
				frappe.throw(
					_(
						"You cannot send email from {0} using account {1}. Please use the email address associated with the account."
					).format(frappe.bold(self.from_email), frappe.bold(self.account))
				)
		else:
			self.from_email = frappe.db.get_value("Mail Account", self.account, "default_outgoing_email")

	def validate_delivery_option(self) -> None:
		"""Ensures exactly one delivery option is selected."""

		options = [self.save_as_draft, self.move_to_sent, self.delete_after_sending]
		if sum(options) != 1:
			self.save_as_draft = 0
			self.delete_after_sending = 0
			self.move_to_sent = 1
		else:
			selected_index = options.index(1)
			self.save_as_draft = int(selected_index == 0)
			self.move_to_sent = int(selected_index == 1)
			self.delete_after_sending = int(selected_index == 2)

	def validate_recipients(self) -> None:
		"""Validates the recipients."""

		if self.recipients:
			max_recipients = frappe.db.get_single_value("Mail Settings", "max_recipients")
			if len(self.recipients) > max_recipients:
				frappe.throw(
					_(
						"You cannot send to more than {0} recipients. Please use a mailing list or a group email address."
					).format(max_recipients)
				)
		elif not self.save_as_draft:
			frappe.throw(_("Please add at least one recipient."))

	def validate_attachments(self) -> None:
		"""Validates the attachments."""

		if not self.attachments:
			return

		for attachment in self.attachments:
			attachment.cid = attachment.cid or random_string(length=10)
			attachment.filename = attachment.filename or Path(attachment.file_url).name

	def validate_message_id(self) -> None:
		"""Validates the message ID."""

		if not self.message_id:
			self.message_id = make_msgid(domain=self.from_email.split("@")[-1])

	def validate_sent_at(self) -> None:
		"""Validates the sent at date."""

		if self.sent_at:
			if self.sent_at > self.creation:
				frappe.throw(_("Sent At date cannot be in the future."))
		else:
			self.sent_at = self.creation

	def validate_in_reply_to(self) -> None:
		"""Validates the In Reply To (Message ID)."""

		if self.in_reply_to and (not self.in_reply_to.startswith("<") and not self.in_reply_to.endswith(">")):
			self.in_reply_to = f"<{self.in_reply_to}>"

	def submit(self) -> None:
		"""Submits the email to the JMAP server."""

		client = get_jmap_client(self.account)
		draft_mailbox_id = get_mailbox_id(self.account, role="drafts")
		sent_mailbox_id = get_mailbox_id(self.account, role="sent")

		using = []
		method_calls = []

		if self.raw_message:
			blob = client.upload_blob(self.raw_message.encode("utf-8"), content_type="message/rfc822")
			using.append("urn:ietf:params:jmap:mail")
			method_calls.append(
				[
					"Email/import",
					{
						"accountId": client.account_id,
						"emails": {
							f"draft-{self.name}": {
								"blobId": blob["blobId"],
								"mailboxIds": {draft_mailbox_id: True},
								"keywords": {"$draft": True, "$seen": True},
							}
						},
					},
					"0",
				]
			)
		else:
			if self.attachments:
				for attachment in self.attachments:
					if file := find_file_by_url(attachment.file_url):
						content = file.get_content()
						content_type = guess_type(file.file_name)[0]
						blob = client.upload_blob(content, content_type)
						attachment.db_set(
							{"type": blob["type"], "size": blob["size"], "blob_id": blob["blobId"]}
						)

			using.append("urn:ietf:params:jmap:mail")
			method_calls.append(
				[
					"Email/set",
					{
						"accountId": client.account_id,
						"create": {f"draft-{self.name}": self._draft_mail(draft_mailbox_id)},
					},
					"0",
				]
			)

		if self.move_to_sent or self.delete_after_sending:
			method_call = [
				"EmailSubmission/set",
				{
					"accountId": client.account_id,
					"create": {
						f"submit-{self.name}": {
							"identityId": self.identity_id,
							"emailId": f"#draft-{self.name}",
							"envelope": {
								"mailFrom": {
									"email": self.from_email,
									"parameters": {
										"RET": "FULL",
										"ENVID": self.name,
									},
								},
								"rcptTo": [
									{
										"email": rcpt.email,
										"parameters": {
											"NOTIFY": "DELAY,FAILURE",
											"ORCPT": f"rfc822;{rcpt.email}",
										},
									}
									for rcpt in self.recipients
								],
							},
						}
					},
				},
				"1",
			]

			if self.move_to_sent:
				method_call[1]["onSuccessUpdateEmail"] = {
					f"#submit-{self.name}": {
						f"mailboxIds/{draft_mailbox_id}": None,
						f"mailboxIds/{sent_mailbox_id}": True,
						"keywords/$draft": None,
						"keywords/$seen": True,
					}
				}
			elif self.delete_after_sending:
				method_call[1]["onSuccessDestroyEmail"] = [f"#submit-{self.name}"]

			using.append("urn:ietf:params:jmap:submission")
			method_calls.append(method_call)

		response = client._make_request(using=using, method_calls=method_calls)

		kwargs = {"status": "Failed", "_response": json.dumps(response)}
		if data := response["methodResponses"][0][1].get("created", {}).get(f"draft-{self.name}"):
			kwargs.update(
				{
					"status": "Draft",
					"_id": data["id"],
					"blob_id": data["blobId"],
					"size": data["size"],
					"mailbox_id": draft_mailbox_id,
					"thread_id": data["threadId"],
				}
			)
		elif response["methodResponses"][0][1].get("notCreated", {}).get(f"draft-{self.name}"):
			kwargs["status"] = "Failed to Draft"

		if self.move_to_sent or self.delete_after_sending:
			if response["methodResponses"][1][1].get("created", {}).get(f"submit-{self.name}"):
				kwargs.update(
					{
						"status": "Submitted",
						"mailbox_id": sent_mailbox_id,
					}
				)
			elif response["methodResponses"][1][1].get("notCreated", {}).get(f"submit-{self.name}"):
				kwargs["status"] = "Failed to Submit"

		self._db_set(notify_update=True, **kwargs)

	def _get_recipients(self, type: Literal["To", "Cc", "Bcc"] | None = None) -> list[dict[str, str | None]]:
		"""Returns the recipients."""

		recipients = []
		for rcpt in self.recipients:
			if type and rcpt.type != type:
				continue

			recipients.append({"name": rcpt.display_name, "email": rcpt.email})

		return recipients

	def _draft_mail(self, draft_mailbox_id: str) -> dict:
		"""Returns the draft mail object."""

		mail = {
			"mailboxIds": {draft_mailbox_id: True},
			"keywords": {"$draft": True, "$seen": True},
			"from": [{"name": self.from_name, "email": self.from_email}],
		}

		for field in ["to", "cc", "bcc"]:
			if hasattr(self, field):
				if value := getattr(self, field):
					mail[field] = value

		if self.subject:
			mail["subject"] = self.subject

		mail.update(
			{
				"sentAt": convert_to_utc(self.sent_at).isoformat(),
				"header:Message-ID": self.message_id,
			}
		)

		if self.reply_to:
			mail["header:Reply-To"] = ", ".join([f'"{rt.display_name}" <{rt.email}>' for rt in self.reply_to])

		if self.in_reply_to:
			mail["header:In-Reply-To"] = self.in_reply_to

		for header in self.headers:
			if header.key and header.value:
				mail[f"header:{header.key}"] = header.value

		mail["textBody"] = [{"partId": "text", "type": "text/plain"}]
		mail["htmlBody"] = [{"partId": "html", "type": "text/html"}]
		mail["bodyValues"] = {
			"text": {"value": self.text_body, "charset": "utf-8", "isTruncated": False},
			"html": {"value": self.html_body, "charset": "utf-8", "isTruncated": False},
		}

		attachments = []
		for attachment in self.attachments:
			attachments.append(
				{
					"name": attachment.filename,
					"type": attachment.type,
					"cid": attachment.cid,
					"blobId": attachment.blob_id,
					"disposition": attachment.disposition,
				}
			)
		mail["attachments"] = attachments

		return mail

	def _db_set(
		self,
		update_modified: bool = True,
		commit: bool = False,
		notify_update: bool = False,
		**kwargs,
	) -> None:
		"""Updates the document with the given key-value pairs."""

		self.db_set(kwargs, update_modified=update_modified, commit=commit)

		if notify_update:
			self.notify_update()


def create_mail_queue(do_not_save: bool = False, **kwargs) -> MailQueue:
	"""Creates a new Mail Queue document."""

	kwargs = frappe._dict(kwargs)

	doc = frappe.new_doc("Mail Queue")
	doc.account = kwargs.account
	doc.from_name = kwargs.from_name
	doc.from_email = kwargs.from_email
	doc.subject = kwargs.subject
	doc.save_as_draft = cint(kwargs.save_as_draft)
	doc.move_to_sent = cint(kwargs.move_to_sent)
	doc.delete_after_sending = cint(kwargs.delete_after_sending)

	if kwargs.reply_to:
		for reply_to in kwargs.reply_to:
			doc.append("reply_to", reply_to)

	if kwargs.headers:
		for header in kwargs.headers:
			doc.append("headers", header)

	if kwargs.recipients:
		for rcpt in kwargs.recipients:
			doc.append("recipients", rcpt)

	if kwargs.attachments:
		for attachment in kwargs.attachments:
			doc.append(
				"attachments",
				{
					"file_url": attachment["file_url"],
					"disposition": attachment["disposition"],
					"filename": attachment.get("filename"),
				},
			)

	doc.html_body = kwargs.html_body
	doc.text_body = kwargs.text_body
	doc.message_id = kwargs.message_id
	doc.sent_at = kwargs.sent_at
	doc.in_reply_to = kwargs.in_reply_to

	if not do_not_save:
		doc.save()

	return doc


def get_permission_query_condition(user: str | None = None) -> str:
	user = user or frappe.session.user

	if is_system_manager(user):
		return ""

	if account := get_account_for_user(user):
		return f"(`tabMail Queue`.account = '{account}')"
	else:
		return "1=0"


def has_permission(doc: Document, ptype: str, user: str | None = None) -> bool:
	if doc.doctype != "Mail Queue":
		return False

	user = user or frappe.session.user
	user_is_system_manager = is_system_manager(user)
	user_is_account_owner = is_account_owner(doc.account, user)

	if user_is_system_manager or user_is_account_owner:
		return True

	return False

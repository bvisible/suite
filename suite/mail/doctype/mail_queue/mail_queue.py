# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
from email.utils import make_msgid
from typing import Literal

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now
from frappe.utils import time_diff_in_seconds
from uuid_utils import uuid7

from mail.jmap import get_identities, get_jmap_client, get_mailbox_id
from mail.utils.cache import get_account_for_email, get_account_for_user
from mail.utils.dt import convert_to_utc
from mail.utils.user import is_account_owner, is_system_manager


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
		self.validate_from_name()
		self.validate_from_email()
		self.validate_recipients()
		self.validate_message_id()
		self.validate_sent_at()

	def after_insert(self) -> None:
		self.submit()

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

	def validate_recipients(self) -> None:
		"""Validates the recipients."""

		max_recipients = frappe.db.get_single_value("Mail Settings", "max_recipients")
		if len(self.recipients) > max_recipients:
			frappe.throw(
				_(
					"You cannot send to more than {0} recipients. Please use a mailing list or a group email address."
				).format(max_recipients)
			)

	def validate_message_id(self) -> None:
		"""Validates the message ID."""

		if not self.message_id:
			self.message_id = make_msgid(domain=self.from_email.split("@")[-1])

	def validate_sent_at(self) -> None:
		"""Validates the sent at date."""

		if not self.sent_at:
			self.sent_at = self.creation

		if self.sent_at > self.creation:
			frappe.throw(_("Sent At date cannot be in the future."))

	def submit(self) -> None:
		"""Submits the email to the JMAP server."""

		client = get_jmap_client(self.account)
		draft_mailbox_id = get_mailbox_id(self.account, role="drafts")
		sent_mailbox_id = get_mailbox_id(self.account, role="sent")

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

		body_structure = {"type": "multipart/alternative", "subParts": []}
		body_values = {}
		for idx, field in enumerate(["text_html", "text_plain"], start=1):
			if value := getattr(self, field):
				body_structure["subParts"].append(
					{"partId": str(idx), "type": field.replace("_", "/"), "header:Content-Language": "en"}
				)
				body_values[str(idx)] = {"value": value, "isTruncated": False}

		mail["bodyStructure"] = body_structure
		mail["bodyValues"] = body_values

		response = client._make_request(
			using=["urn:ietf:params:jmap:mail"],
			method_calls=[
				[
					"Email/set",
					{
						"accountId": client.account_id,
						"create": {f"draft-{self.name}": mail},
					},
					"0",
				],
				[
					"EmailSubmission/set",
					{
						"accountId": client.account_id,
						"create": {
							f"submit-{self.name}": {
								"identityId": self.identity_id,
								"emailId": f"#draft-{self.name}",
							}
						},
						"onSuccessUpdateEmail": {
							f"#submit-{self.name}": {
								f"mailboxIds/{draft_mailbox_id}": None,
								f"mailboxIds/{sent_mailbox_id}": True,
								"keywords/$draft": None,
							}
						},
					},
					"1",
				],
			],
		)

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

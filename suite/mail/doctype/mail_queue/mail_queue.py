# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
from email import message_from_string
from email.utils import make_msgid, parseaddr
from mimetypes import guess_type
from pathlib import Path
from typing import Any, Literal

import frappe
from frappe import _
from frappe.core.doctype.file.utils import find_file_by_url
from frappe.model.document import Document
from frappe.query_builder import Interval, Order
from frappe.query_builder.functions import Now
from frappe.utils import add_to_date, cint, create_batch, get_datetime_str, now, random_string
from uuid_utils import uuid7

from mail.jmap import get_identities, get_jmap_client, get_mailbox_id
from mail.utils.cache import get_account_for_email, get_account_for_user
from mail.utils.dt import convert_to_utc, parsedate_to_datetime
from mail.utils.user import get_account_email_addresses, is_account_owner, is_system_manager


class MailQueue(Document):
	@staticmethod
	def clear_old_logs(days: int = 3) -> None:
		MQ = frappe.qb.DocType("Mail Queue")
		(
			frappe.qb.from_(MQ)
			.where((MQ.status.isin(["Drafted", "Submitted"])) & (MQ.creation < (Now() - Interval(days=days))))
			.delete()
		).run()

	@staticmethod
	def _create(do_not_save: bool = False, **kwargs) -> "MailQueue":
		"""Create a new MailQueue document."""

		kwargs = frappe._dict(kwargs)

		doc = frappe.new_doc("Mail Queue")
		doc.account = kwargs.account
		doc.from_name = kwargs.from_name
		doc.from_email = kwargs.from_email
		doc.subject = kwargs.subject

		for field in ["reply_to", "headers", "recipients", "attachments"]:
			if kwargs.get(field):
				setattr(doc, field, json.dumps(kwargs[field]))

		doc.html_body = kwargs.html_body
		doc.text_body = kwargs.text_body
		doc.forwarded_from_id = kwargs.forwarded_from_id
		doc.message_id = kwargs.message_id
		doc._id = kwargs._id
		doc.sent_at = kwargs.sent_at
		doc.in_reply_to = kwargs.in_reply_to
		doc.in_reply_to_id = kwargs.in_reply_to_id
		doc.save_as_draft = cint(kwargs.save_as_draft)
		doc.destroy_after_submission = cint(kwargs.destroy_after_submission)
		doc.delivery_mode = kwargs.delivery_mode or "Immediate"
		doc.raw_message = kwargs.raw_message

		if not do_not_save:
			doc.insert()

		return doc

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
		"""Returns the identity ID for the from email."""

		for identity in get_identities(self.account):
			if identity["email"] == self.from_email:
				return identity["id"]

		frappe.throw(_("Identity not found for email {0}").format(self.from_email))

	@property
	def response(self) -> str | None:
		"""Returns the indented JSON response."""

		_response = json_loads(self._response)
		return json.dumps(_response, indent=4) if _response else None

	@property
	def error_message(self) -> str | None:
		"""Returns the error message."""

		if not self._response or self.status not in ["Failed to Draft", "Failed to Submit"]:
			return None

		response = json_loads(self._response)

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
		if self.is_new():
			self.validate_status()
			self.validate_account()
			self.validate_raw_message()
			self.validate_from_name()
			self.validate_from_email()
			self.validate_delivery_mode()
			self.validate_reply_to()
			self.validate_headers()
			self.validate_recipients()
			self.validate_attachments()
			self.validate_message_id()
			self.validate_sent_at()
			self.validate_in_reply_to()
			self.validate_in_reply_to_id()

	def after_insert(self) -> None:
		if self.delivery_mode == "Immediate":
			self._process()
		elif self.delivery_mode == "Enqueue":
			frappe.enqueue_doc(self.doctype, self.name, "_process", queue="short", enqueue_after_commit=True)

	def validate_status(self) -> None:
		"""Validates the status."""

		if self.delivery_mode == "Immediate":
			self.status = None
			self.queued_at = None
		elif self.delivery_mode == "Enqueue":
			self.status = "Queued"
			self.queued_at = now()
		elif self.delivery_mode == "Batch":
			self.status = "Pending"
			self.queued_at = None

	def validate_account(self) -> None:
		"""Validates the account."""

		if not self.account:
			frappe.throw(_("Account is required."))

	def validate_raw_message(self) -> None:
		"""Validates the raw message."""

		if not self.raw_message:
			return

		self.from_name = None
		self.from_email = None
		self.subject = None
		self.reply_to = None
		self.headers = None
		self.html_body = None
		self.text_body = None
		self.attachments = None
		self.message_id = None
		self.sent_at = None
		self.in_reply_to = None

		message = message_from_string(self.raw_message)
		if from_header := message.get("From"):
			self.from_name, self.from_email = parseaddr(from_header)

			if self.from_email not in get_account_email_addresses(self.account):
				# If the `From` address doesn't match any of the account's associated addresses,
				# reset it to fall back to the account's default email address.
				self.from_email = None

		if not json_loads(self.recipients):
			recipients = []
			for rcpt_type in ["To", "Cc", "Bcc"]:
				if _rcpt := message.get(rcpt_type):
					for rcpt in _rcpt.split(","):
						recipients.append(
							{
								"type": rcpt_type,
								"display_name": parseaddr(rcpt)[0],
								"email": parseaddr(rcpt)[1],
							}
						)

			self.recipients = json.dumps(recipients)

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

	def validate_delivery_mode(self) -> None:
		"""Validates the delivery mode."""

		if self.delivery_mode:
			if self.delivery_mode not in ["Immediate", "Enqueue", "Batch"]:
				frappe.throw(_("Invalid delivery mode: {0}").format(self.delivery_mode))
		else:
			self.delivery_mode = "Immediate"

	def validate_reply_to(self) -> None:
		"""Validates the reply to."""

		reply_to = []
		for rt in json_loads(self.reply_to, default=[]):
			reply_to.append(
				{
					"display_name": rt.get("display_name"),
					"email": rt["email"],
				}
			)

		self.reply_to = json.dumps(reply_to)

	def validate_headers(self) -> None:
		"""Validates the headers."""

		standard_headers = {
			"from",
			"to",
			"cc",
			"bcc",
			"subject",
			"date",
			"message-id",
			"in-reply-to",
			"references",
			"reply-to",
			"sender",
			"return-path",
			"mime-version",
			"content-type",
			"content-transfer-encoding",
			"content-language",
			"x-priority",
		}

		headers = {}
		for key, value in json_loads(self.headers, default={}).items():
			if key.lower() in standard_headers:
				frappe.throw(
					_(
						"The header <b>{0}</b> is a standard email header and cannot be overridden. Please use custom headers prefixed with <code>X-</code>."
					).format(key)
				)

			headers[key] = value

		self.headers = json.dumps(headers)

	def validate_recipients(self) -> None:
		"""Validates the recipients."""

		recipients = []
		for rcpt in json_loads(self.recipients, default=[]):
			recipients.append(
				{
					"type": rcpt["type"],
					"display_name": rcpt.get("display_name"),
					"email": rcpt["email"],
				}
			)

		if not recipients and not self.save_as_draft:
			frappe.throw(_("Please add at least one recipient."))

		self.recipients = json.dumps(recipients)

	def validate_attachments(self) -> None:
		"""Validates the attachments."""

		attachments = []
		for a in json_loads(self.attachments, default=[]):
			attachments.append(
				{
					"file_url": a["file_url"],
					"disposition": a["disposition"],
					"cid": a.get("cid") or random_string(length=10),
					"filename": a.get("filename") or Path(a["file_url"]).name,
				}
			)

		self.attachments = json.dumps(attachments)

	def validate_message_id(self) -> None:
		"""Validates the message ID."""

		if not self.message_id:
			self.message_id = make_msgid(domain=self.from_email.split("@")[-1]).strip("<>")

	def validate_sent_at(self) -> None:
		"""Validates the sent at date."""

		if not self.raw_message:
			self.sent_at = now()

	def validate_in_reply_to(self) -> None:
		"""Validates the In Reply To (Message ID)."""

		if self.in_reply_to:
			self.in_reply_to = self.in_reply_to.strip("<>")

	def validate_in_reply_to_id(self) -> None:
		"""Validates the In Reply To ID."""

		if self.in_reply_to and not self.in_reply_to_id:
			self.in_reply_to_id = frappe.db.get_value(
				"Email Message",
				{"account": self.account, "destroyed": 0, "message_id": self.in_reply_to},
				"_id",
			)

	@frappe.whitelist()
	def retry(self) -> None:
		"""Retries Create, Update or Submit the Email."""

		frappe.only_for("System Manager")

		if self.status not in ["Failed", "Failed to Draft", "Failed to Submit"]:
			frappe.throw(_("Cannot retry a mail with status {0}").format(self.status))

		self._process()

	def _process(self) -> None:
		"""Create, Update or Submit the Email."""

		kwargs = {}

		try:
			client = get_jmap_client(self.account)
			draft_mailbox_id = get_mailbox_id(self.account, role="drafts")
			sent_mailbox_id = get_mailbox_id(self.account, role="sent")

			using = ["urn:ietf:params:jmap:mail"]
			method_calls = []
			call_id = 0

			if self.raw_message:
				blob = client.upload_blob(self.raw_message.encode("utf-8"), content_type="message/rfc822")
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
						str(call_id),
					]
				)
				call_id += 1

				if self._id:
					method_calls.append(
						[
							"Email/set",
							{
								"accountId": client.account_id,
								"destroy": [self._id] if self._id else None,
							},
							str(call_id),
						]
					)
					call_id += 1
			else:
				if attachments := json_loads(self.attachments):
					for a in attachments:
						if file := find_file_by_url(a["file_url"]):
							content = file.get_content()
							content_type = guess_type(file.file_name)[0]
							blob = client.upload_blob(content, content_type)
							a.update({"type": blob["type"], "size": blob["size"], "blob_id": blob["blobId"]})

					attachments = json.dumps(attachments)
					self.attachments = attachments
					kwargs["attachments"] = attachments

				method_calls.append(
					[
						"Email/set",
						{
							"accountId": client.account_id,
							"create": {f"draft-{self.name}": self._draft_mail(draft_mailbox_id)},
							"destroy": [self._id] if self._id else None,
						},
						str(call_id),
					]
				)
				call_id += 1

			if not self.save_as_draft:
				submission_call = [
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
											"email": rcpt["email"],
											"parameters": {
												"NOTIFY": "DELAY,FAILURE",
												"ORCPT": f"rfc822;{rcpt['email']}",
											},
										}
										for rcpt in json_loads(self.recipients)
									],
								},
							}
						},
					},
					str(call_id),
				]

				if self.destroy_after_submission:
					submission_call[1]["onSuccessDestroyEmail"] = [f"#submit-{self.name}"]
				else:
					submission_call[1]["onSuccessUpdateEmail"] = {
						f"#submit-{self.name}": {
							f"mailboxIds/{draft_mailbox_id}": None,
							f"mailboxIds/{sent_mailbox_id}": True,
							"keywords/$draft": None,
							"keywords/$seen": True,
						}
					}

				using.append("urn:ietf:params:jmap:submission")
				method_calls.append(submission_call)
				call_id += 1

				if self.forwarded_from_id or self.in_reply_to_id:
					updates = {}

					for _id, keyword in [
						(self.forwarded_from_id, "$forwarded"),
						(self.in_reply_to_id, "$answered"),
					]:
						if not _id:
							continue

						updates.setdefault(_id, {}).update({f"keywords/{keyword}": True})

					if updates:
						method_calls.append(
							[
								"Email/set",
								{
									"accountId": client.account_id,
									"update": {_id: keywords for _id, keywords in updates.items()},
								},
								str(call_id),
							]
						)
						call_id += 1

			response = client._make_request(using=using, method_calls=method_calls)

			kwargs.update({"status": "Failed", "_response": json.dumps(response)})
			if data := response["methodResponses"][0][1].get("created", {}).get(f"draft-{self.name}"):
				kwargs.update(
					{
						"status": "Drafted",
						"_id": data["id"],
						"blob_id": data["blobId"],
						"size": data["size"],
						"drafted_at": now(),
						"thread_id": data["threadId"],
						"mailbox_id": draft_mailbox_id,
					}
				)
			elif response["methodResponses"][0][1].get("notCreated", {}).get(f"draft-{self.name}"):
				kwargs["status"] = "Failed to Draft"

			if not self.save_as_draft:
				if response["methodResponses"][1][1].get("created", {}).get(f"submit-{self.name}"):
					kwargs.update(
						{
							"status": "Submitted",
							"submitted_at": now(),
							"mailbox_id": sent_mailbox_id,
						}
					)
				elif response["methodResponses"][1][1].get("notCreated", {}).get(f"submit-{self.name}"):
					kwargs["status"] = "Failed to Submit"
		except Exception:
			failed_count = self.failed_count + 1
			kwargs.update(
				{
					"status": "Failed",
					"failed_count": failed_count,
					"next_retry_after": get_next_retry_after(failed_count),
					"error_log": frappe.get_traceback(with_context=True),
				}
			)

		self._db_set(notify=True, **kwargs)

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
				"header:Message-ID": f"<{self.message_id}>",
			}
		)

		if reply_to := json_loads(self.reply_to):
			mail["header:Reply-To"] = ", ".join(
				[f'"{rt.display_name}" <{rt.email}>' for rt in frappe._dict(reply_to)]
			)

		if self.in_reply_to:
			mail["header:In-Reply-To"] = f"<{self.in_reply_to}>"

		if headers := json_loads(self.headers):
			for key, value in headers.items():
				mail[f"header:{key}"] = value

		mail["bodyValues"] = {}
		if self.text_body:
			mail["textBody"] = [{"partId": "text", "type": "text/plain"}]
			mail["bodyValues"]["text"] = {"value": self.text_body, "charset": "utf-8", "isTruncated": False}
		if self.html_body:
			mail["htmlBody"] = [{"partId": "html", "type": "text/html"}]
			mail["bodyValues"]["html"] = {"value": self.html_body, "charset": "utf-8", "isTruncated": False}

		attachments = []
		for a in json_loads(self.attachments, default=[]):
			attachments.append(
				{
					"name": a["filename"],
					"type": a["type"],
					"cid": a["cid"],
					"blobId": a["blob_id"],
					"disposition": a["disposition"],
				}
			)
		mail["attachments"] = attachments

		return mail

	def _get_recipients(self, type: Literal["To", "Cc", "Bcc"] | None = None) -> list[dict[str, str | None]]:
		"""Returns the recipients."""

		recipients = []
		for rcpt in json_loads(self.recipients, default=[]):
			if type and rcpt["type"] != type:
				continue

			recipients.append({"name": rcpt["display_name"], "email": rcpt["email"]})

		return recipients

	def _db_set(
		self,
		update_modified: bool = True,
		commit: bool = False,
		notify: bool = False,
		**kwargs,
	) -> None:
		"""Updates the document with the given key-value pairs."""

		self.db_set(kwargs, update_modified=update_modified, notify=notify, commit=commit)


def json_loads(data: str | None, default: Any = None) -> list | dict | None:
	"""Loads the given JSON data and returns it as a list or dict."""

	if data:
		return json.loads(data)

	return default


def get_next_retry_after(failed_count: int) -> str:
	"""Returns the next retry after datetime."""

	next_retry_after_minutes = failed_count * (failed_count + 1)  # 2, 6, 12, 20, 30 ...
	return add_to_date(now(), minutes=next_retry_after_minutes)


def process_pending_emails(mails: list[str]) -> None:
	"""Process pending emails."""

	failed_mails = []
	total_count = len(mails)

	for mail in mails:
		doc: "MailQueue" = frappe.get_doc("Mail Queue", mail)
		doc._process()

		if doc.status in ["Failed", "Failed to Draft", "Failed to Submit"]:
			failed_mails.append(mail)

			failed_count = len(failed_mails)
			failure_ratio = failed_count / total_count

			if failure_ratio > 0.33 and failed_count > 50:
				frappe.throw(
					_(
						"Email processing aborted: {failed_count} out of {total_count} emails failed "
						"({failure_rate:.2%} failure rate). Please investigate the issue before retrying."
					).format(failed_count=failed_count, total_count=total_count, failure_rate=failure_ratio)
				)


def enqueue_process_pending_emails(batch_process_size: int = 1_000, max_batch_size: int = 10_000) -> None:
	"""Enqueue process pending emails."""

	MQ = frappe.qb.DocType("Mail Queue")
	mails = (
		frappe.qb.from_(MQ)
		.select(MQ.name)
		.where(
			(MQ.status == "Pending")
			| (
				(MQ.failed_count > 0)
				& (MQ.failed_count < 5)
				& (Now() >= MQ.next_retry_after)
				& (MQ.status.isin(["Failed", "Failed to Draft", "Failed to Submit"]))
			)
			| ((MQ.status == "Queued") & (MQ.queued_at <= (Now() - Interval(minutes=30))))
		)
		.orderby(MQ.creation, MQ.failed_count, order=Order.asc)
		.limit(max_batch_size)
	).run(pluck="name")

	if not mails:
		return

	try:
		(
			frappe.qb.update(MQ)
			.set(MQ.status, "Queued")
			.set(MQ.queued_at, Now())
			.where((MQ.name.isin(mails)) & (MQ.status.notin(["Drafted", "Submitted"])))
		).run()

		for i, batch in enumerate(create_batch(mails, batch_process_size), start=1):
			frappe.enqueue(
				process_pending_emails,
				queue="long",
				job_name=f"process_pending_emails_{i}_{len(batch)}",
				enqueue_after_commit=False,
				mails=batch,
			)

		# Recursively process next batch if the limit was reached.
		if len(mails) == max_batch_size:
			enqueue_process_pending_emails(batch_process_size, max_batch_size)

	except Exception:
		frappe.log_error(
			title="Failed - Enqueue Process Pending Emails", message=frappe.get_traceback(with_context=True)
		)


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

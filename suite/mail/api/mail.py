import re
from collections import defaultdict
from email.utils import parseaddr
from typing import Literal

import frappe
from frappe import _
from frappe.utils import now

from mail.jmap import get_mailboxes_for_account
from mail.mail.doctype.email_message.email_message import EmailMessage
from mail.utils.cache import get_account_for_user
from mail.utils.user import get_user_email_addresses

MailType = Literal["Incoming Mail", "Outgoing Mail"]


@frappe.whitelist()
def get_mailboxes() -> list:
	"""Returns mailboxes for the current user."""

	return get_mailboxes_for_account(frappe.session.user)


def get_mailbox_id(mailbox: str) -> str:
	"""Returns mailbox id for the given role."""

	mailboxes = get_mailboxes()
	if mailbox not in [d["role"] for d in mailboxes]:
		frappe.throw(_("Mailbox {0} does not exist.").format(mailbox))

	return next(d["id"] for d in mailboxes if d["role"] == mailbox)


@frappe.whitelist()
def get_mails_from_mailbox(mailbox: str, limit: int) -> list:
	"""Returns mails from the selected mailbox for the current user."""

	mailbox_id = get_mailbox_id(mailbox)

	return EmailMessage.get_threads(frappe.session.user, [mailbox_id], 0, limit)


@frappe.whitelist()
def get_mail_thread(thread_id: str) -> list[dict]:
	"""Returns mail thread for the given id."""

	EmailMessage = frappe.qb.DocType("Email Message")
	EmailMessageRecipient = frappe.qb.DocType("Email Message Recipient")

	rows = (
		frappe.qb.from_(EmailMessage)
		.left_join(EmailMessageRecipient)
		.on(EmailMessage.name == EmailMessageRecipient.parent)
		.select(
			EmailMessage.name,
			EmailMessage.from_name,
			EmailMessage.from_email,
			EmailMessage.subject,
			EmailMessage.html_body,
			EmailMessage.text_body,
			EmailMessage.received_at,
			EmailMessageRecipient.type,
			EmailMessageRecipient.email,
			EmailMessageRecipient.display_name,
		)
		.where(
			(EmailMessage.account == frappe.session.user)
			& (EmailMessage.thread_id == thread_id)
			& (EmailMessage.destroyed == 0)
		)
	).run(as_dict=True)

	return group_recipients(rows)


def group_recipients(rows: list[dict]) -> list[dict]:
	"""Returns mail thread with grouped recipients."""

	grouped = {}

	for row in rows:
		key = row["name"]
		if key not in grouped:
			# Copy non-recipient fields
			grouped[key] = {
				"name": row["name"],
				"from_name": row["from_name"],
				"from_email": row["from_email"],
				"subject": row["subject"],
				"html_body": row["html_body"],
				"text_body": row["text_body"],
				"received_at": row["received_at"],
				"recipients": defaultdict(list),
			}

		recipient = {"email": row["email"], "display_name": row["display_name"]}
		grouped[key]["recipients"][row["type"]].append(recipient)

	result = []
	for item in grouped.values():
		item["recipients"] = dict(item["recipients"])
		result.append(item)

	return result


@frappe.whitelist()
def get_mail_contacts(txt=None) -> list:
	"""Returns the mail contacts for the current user."""

	filters = {"user": frappe.session.user}
	if txt:
		filters["email"] = ["like", f"%{txt}%"]

	contacts = frappe.get_all("Mail Contact", filters=filters, fields=["email"], page_length=10)

	for contact in contacts:
		details = frappe.db.get_value(
			"User", {"email": contact.email}, ["user_image", "full_name", "email"], as_dict=1
		)
		if details:
			contact.update(details)

	return contacts


@frappe.whitelist()
def update_draft_mail(
	mail_id: str,
	from_: str,
	to: str | list[str],
	subject: str,
	cc: str | list[str] | None = None,
	bcc: str | list[str] | None = None,
	html: str | None = None,
	attachments: list[dict] | None = None,
	do_submit: bool = False,
):
	"""Update draft mail."""

	display_name, from_ = parseaddr(from_)

	doc = frappe.get_doc("Outgoing Mail", mail_id)
	doc.from_ = from_
	doc.display_name = display_name
	doc._update_recipients("To", to)
	doc._update_recipients("Cc", cc)
	doc._update_recipients("Bcc", bcc)
	doc.subject = subject
	doc.body_html = html
	doc.save()
	doc._add_attachment(attachments)

	if do_submit:
		doc.submit()


@frappe.whitelist()
def get_attachments_for_mail(type: MailType, name: str):
	"""Fetches mail attachments."""

	return frappe.get_all(
		"File",
		fields=["name", "file_name", "file_url", "file_size"],
		filters={"attached_to_name": name, "attached_to_doctype": type},
	)


@frappe.whitelist()
def get_user_addresses(user: str | None = None) -> list:
	"""Fetches user email addresses."""

	if not user:
		user = frappe.session.user

	return get_user_email_addresses(user)


@frappe.whitelist()
def get_mime_message(mail_type: MailType, name: str) -> dict:
	"""Fetches mail mime message and related data."""

	doc = frappe.get_doc(mail_type, name)

	def get_mail_recipients(recipient_type):
		return ", ".join([d.email for d in doc.recipients if d.type == recipient_type])

	mail = {
		"message": doc.message,
		"message_id": {"label": _("Message ID"), "value": doc.message_id},
		"created_at": {"label": _("Created at"), "value": doc.created_at},
		"subject": {"label": _("Subject"), "value": doc.subject},
		"from": {"label": _("From"), "value": f"{doc.display_name} <{doc.sender}>"},
		"to": {"label": _("To"), "value": get_mail_recipients("To")},
		"cc": {"label": _("CC"), "value": get_mail_recipients("Cc")},
	}

	if mail_type == "Outgoing Mail":
		mail["bcc"] = {"label": _("BCC"), "value": get_mail_recipients("Bcc")}

	elif doc.type != "DSN Report":
		pass_or_fail = {1: _("'Pass'"), 0: _("'Fail'")}
		mail["spf"] = {
			"label": _("SPF"),
			"value": _("{0} with IP {1}").format(pass_or_fail[doc.spf_pass], doc.from_ip),
		}
		mail["dkim"] = {"label": _("DKIM"), "value": pass_or_fail[doc.dkim_pass]}
		mail["dmarc"] = {"label": _("DMARC"), "value": pass_or_fail[doc.dmarc_pass]}

	return mail


@frappe.whitelist()
def set_seen(thread_ids: list[str], seen: bool) -> dict:
	"""Sets seen for mails."""

	user = frappe.session.user
	messages = EmailMessage.get_message_ids(user, thread_ids)

	if seen:
		EmailMessage.mark_emails_as_seen(user, messages)
	else:
		EmailMessage.mark_emails_as_unseen(user, messages)

	return {"thread_ids": thread_ids, "seen": seen}


@frappe.whitelist()
def set_mails_mailbox(mail_ids: list[str], mailbox: str) -> None:
	"""Sets mailbox for mails."""

	EmailMessage.move_emails_to_mailbox(frappe.session.user, mail_ids, None, mailbox)


@frappe.whitelist()
def empty_mailbox(mailbox: str) -> None:
	"""Empties selected mailbox for current user."""

	mailbox_id = get_mailbox_id(mailbox)

	user = frappe.session.user
	messages = frappe.get_all(
		"Email Message",
		{"account": user, "mailbox_id": ["in", mailbox_id], "destroyed": 0},
		pluck="name",
	)
	EmailMessage.destroy_emails(user, messages)


@frappe.whitelist()
def set_threads_mailbox(thread_ids: list[str], mailbox: str) -> None:
	"""Sets mailbox for threads."""

	user = frappe.session.user
	messages = EmailMessage.get_message_ids(user, thread_ids)
	EmailMessage.move_emails_to_mailbox(user, messages, None, mailbox)


@frappe.whitelist()
def delete_threads(thread_ids: list[str]) -> None:
	"""Destroys mails belonging to the given threads."""

	user = frappe.session.user
	messages = EmailMessage.get_message_ids(user, thread_ids)
	EmailMessage.destroy_emails(user, messages)

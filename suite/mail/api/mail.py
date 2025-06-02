import json
from collections import defaultdict
from typing import Literal

import frappe
from frappe import _
from frappe.query_builder.functions import Count
from frappe.utils import cint, random_string

from mail.jmap import get_mailboxes_for_account
from mail.mail.doctype.email_message.email_message import EmailMessage
from mail.utils.user import get_user_email_addresses


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
def get_mailbox_thread_count(mailbox: str) -> str:
	"""Returns no. of mails for the given mailbox."""

	mailbox_id = get_mailbox_id(mailbox)

	EmailMessage = frappe.qb.DocType("Email Message")

	distinct_threads = (
		frappe.qb.from_(EmailMessage)
		.select(EmailMessage.thread_id)
		.distinct()
		.where(
			(EmailMessage.account == frappe.session.user)
			& (EmailMessage.mailbox_id == mailbox_id)
			& (EmailMessage.destroyed == 0)
		)
	)

	count = (frappe.qb.from_(distinct_threads).select(Count("*").as_("count"))).run()

	return count[0][0]


# todo:
@frappe.whitelist()
def get_mail_thread(thread_id: str, mailbox: str) -> list[dict]:
	"""Returns mail thread for the given id."""

	mailbox_id = get_mailbox_id(mailbox)

	EmailMessage = frappe.qb.DocType("Email Message")
	EmailMessageRecipient = frappe.qb.DocType("Email Message Recipient")

	rows = (
		frappe.qb.from_(EmailMessage)
		.left_join(EmailMessageRecipient)
		.on(EmailMessage.name == EmailMessageRecipient.parent)
		.select(
			EmailMessage.name,
			EmailMessage.message_id,
			EmailMessage._id,
			EmailMessage.from_name,
			EmailMessage.from_email,
			EmailMessage.subject,
			EmailMessage.html_body,
			EmailMessage.text_body,
			EmailMessage.received_at,
			EmailMessage.draft,
			EmailMessage.has_attachment,
			EmailMessageRecipient.type,
			EmailMessageRecipient.email,
			EmailMessageRecipient.display_name,
		)
		.where(
			(EmailMessage.account == frappe.session.user)
			& (EmailMessage.thread_id == thread_id)
			& (EmailMessage.mailbox_id == mailbox_id)
			& (EmailMessage.destroyed == 0)
		)
	).run(as_dict=True)

	return group_recipients_and_add_attachments(rows)


def group_recipients_and_add_attachments(rows: list[dict]) -> list[dict]:
	"""Returns mail thread with attachments and grouped recipients."""

	grouped = {}

	for row in rows:
		key = row["name"]
		if key not in grouped:
			grouped[key] = {
				"name": row["name"],
				"message_id": row["message_id"],
				"_id": row["_id"],
				"from_name": row["from_name"],
				"from_email": row["from_email"],
				"subject": row["subject"],
				"html_body": row["html_body"],
				"text_body": row["text_body"],
				"received_at": row["received_at"],
				"draft": row["draft"],
				"has_attachment": row["has_attachment"],
				"recipients": defaultdict(list),
			}

		recipient = {"email": row["email"], "display_name": row["display_name"]}
		grouped[key]["recipients"][row["type"]].append(recipient)

	result = []
	for item in grouped.values():
		item["recipients"] = dict(item["recipients"])
		if item["has_attachment"]:
			item["attachments"] = frappe.get_all(
				"Email Message Part",
				filters={"parenttype": "Email Message", "parentfield": "attachments", "parent": item["name"]},
				fields=["filename", "blob_id", "type"],
			)
		result.append(item)

	return result


@frappe.whitelist()
def fetch_attachment(message_id: str, blob_id: str) -> bytes:
	"""Returns the content of an attachment."""

	doc = frappe.get_doc("Email Message", message_id)
	return doc.fetch_attachment(None, blob_id)


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
def create_mail(
	from_email: str,
	to: list[str],
	cc: list[str],
	bcc: list[str],
	subject: str | None,
	body: str | None,
	attachments: list[dict] = None,
	in_reply_to: str | None = None,
	in_reply_to_id: str | None = None,
	save_as_draft: bool = False,
):
	doc = frappe.new_doc("Mail Queue")
	doc.account = frappe.session.user
	doc.from_email = from_email
	doc.subject = subject
	doc.html_body = body
	doc.in_reply_to = in_reply_to
	doc.in_reply_to_id = in_reply_to_id
	doc.save_as_draft = cint(save_as_draft)

	doc.attachments = [
		{
			"file_url": d.get("file_url", ""),
			"filename": d.get("file_name", ""),
			"disposition": d.get("disposition", ""),
			"cid": random_string(10),
		}
		for d in attachments
	]
	doc.attachments = json.dumps(doc.attachments)

	doc.recipients = [{"type": "To", "email": email} for email in to]
	doc.recipients += [{"type": "Cc", "email": email} for email in cc]
	doc.recipients += [{"type": "Bcc", "email": email} for email in bcc]
	doc.recipients = json.dumps(doc.recipients)

	doc.save()


@frappe.whitelist()
def update_draft_mail(
	name: str,
	from_email: str,
	to: list[str],
	cc: list[str],
	bcc: list[str],
	subject: str | None,
	body: str | None,
	submit: bool = False,
):
	doc = frappe.get_doc("Email Message", name)
	doc.account = frappe.session.user
	doc.from_email = from_email
	doc.subject = subject
	doc.html_body = body
	doc.recipients = [frappe._dict({"type": "To", "email": email}) for email in to]
	doc.recipients += [frappe._dict({"type": "Cc", "email": email}) for email in cc]
	doc.recipients += [frappe._dict({"type": "Bcc", "email": email}) for email in bcc]

	doc.submit() if submit else doc.save_draft()


# todo:
# @frappe.whitelist()
# def get_attachments_for_mail(type: MailType, name: str):
# 	"""Fetches mail attachments."""

# 	return frappe.get_all(
# 		"File",
# 		fields=["name", "file_name", "file_url", "file_size"],
# 		filters={"attached_to_name": name, "attached_to_doctype": type},
# 	)


@frappe.whitelist()
def get_user_addresses(user: str | None = None) -> list:
	"""Fetches user email addresses."""

	if not user:
		user = frappe.session.user

	return get_user_email_addresses(user)


@frappe.whitelist()
def get_mime_message(name: str) -> dict:
	"""Fetches mail mime message and related data."""

	doc = frappe.get_doc("Email Message", name)

	def get_mail_recipients(recipient_type):
		return ", ".join([d.email for d in doc.recipients if d.type == recipient_type])

	pass_or_fail = {1: _("'Pass'"), 0: _("'Fail'")}

	return {
		"message": doc.get_mime_message(),
		"message_id": {"label": _("Message ID"), "value": doc.message_id},
		"created_at": {"label": _("Created at"), "value": doc.sent_at},
		"subject": {"label": _("Subject"), "value": doc.subject},
		"from": {"label": _("From"), "value": f"{doc.from_name} <{doc.from_email}>"},
		"to": {"label": _("To"), "value": get_mail_recipients("To")},
		"cc": {"label": _("CC"), "value": get_mail_recipients("Cc")},
		"bcc": {"label": _("BCC"), "value": get_mail_recipients("Bcc")},
		"spf": {
			"label": _("SPF"),
			"value": _("{0} with IP {1}").format(pass_or_fail[doc.spf_pass], doc.from_ip),
		},
		"dkim": {"label": _("DKIM"), "value": pass_or_fail[doc.dkim_pass]},
		"dmarc": {"label": _("DMARC"), "value": pass_or_fail[doc.dmarc_pass]},
	}


@frappe.whitelist()
def set_seen(thread_ids: list[str], seen: bool, mailbox: str) -> dict:
	"""Sets seen for mails."""

	user = frappe.session.user
	mailbox_id = get_mailbox_id(mailbox)
	messages = EmailMessage.get_message_ids(user, thread_ids, mailbox_id)
	EmailMessage.mark_emails_as_seen_unseen(user, messages, seen)

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
def set_threads_mailbox(thread_ids: list[str], mailbox: str, move_to_mailbox) -> None:
	"""Sets mailbox for threads."""

	user = frappe.session.user
	mailbox_id = get_mailbox_id(mailbox)
	messages = EmailMessage.get_message_ids(user, thread_ids, mailbox_id)
	EmailMessage.move_emails_to_mailbox(user, messages, None, move_to_mailbox)


@frappe.whitelist()
def delete_threads(thread_ids: list[str], mailbox: str) -> None:
	"""Destroys mails belonging to the given threads."""

	user = frappe.session.user
	mailbox_id = get_mailbox_id(mailbox)
	messages = EmailMessage.get_message_ids(user, thread_ids, mailbox_id)
	EmailMessage.destroy_emails(user, messages)

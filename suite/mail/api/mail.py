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
	"""Returns mailboxes/folders for the current user."""

	return get_mailboxes_for_account(frappe.session.user)


@frappe.whitelist()
def get_mails_from_mailbox(mailbox: str, limit: int) -> list:
	"""Returns mails from the selected mailbox for the current user."""

	mailboxes = get_mailboxes()
	if mailbox not in [d["role"] for d in mailboxes]:
		frappe.throw(_("Mailbox {0} does not exist.").format(mailbox))

	mailbox_id = next(d["id"] for d in mailboxes if d["role"] == mailbox)

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
def set_seen(mails: list[str], seen: bool) -> dict:
	"""Sets seen for mails."""

	if seen:
		EmailMessage.mark_emails_as_seen(frappe.session.user, mails)
	else:
		EmailMessage.mark_emails_as_unseen(frappe.session.user, mails)

	return {"mails": mails, "seen": seen}


@frappe.whitelist()
def set_folder(mail_type: MailType, name: str, move_to_trash: bool = False) -> None:
	"""Sets folder for mail."""

	doc = frappe.get_doc(mail_type, name)

	if move_to_trash:
		doc.db_set("folder", "Trash")
		doc.db_set("trashed_on", now())
	else:
		doc.db_set("trashed_on")
		if mail_type == "Incoming Mail":
			doc.db_set("folder", "Inbox")
		else:
			doc.folder = None
			doc.set_folder(db_set=True)


@frappe.whitelist()
def delete_or_cancel_mails(mails: list[dict]) -> None:
	"""Deletes mail if draft, otherwise cancels it."""

	for d in mails:
		if d["docstatus"] == 0:
			frappe.delete_doc(d["mail_type"], d["name"])
		else:
			frappe.db.set_value(d["mail_type"], d["name"], "docstatus", 2)


@frappe.whitelist()
def empty_folder(folder: str) -> None:
	"""Empties selected folder for current user."""

	account = get_account_for_user(frappe.session.user)

	for doctype in ["Incoming Mail", "Outgoing Mail"]:
		mails = frappe.get_all(
			doctype,
			{
				"receiver" if doctype == "Incoming Mail" else "sender": account,
				"folder": folder,
				"docstatus": ["!=", 2],
			},
			["name", "docstatus", f"'{doctype}' as mail_type"],
		)
		delete_or_cancel_mails(mails)


# @frappe.whitelist()
# def set_folder_for_threads(threads: list[dict], move_to_trash: bool = False) -> None:
# 	"""Moves threads to trash."""

# 	for thread in threads:
# 		for mail in get_mail_thread(thread["name"], thread["mail_type"], True):
# 			set_folder(mail.mail_type, mail.name, move_to_trash)


# @frappe.whitelist()
# def delete_or_cancel_threads(threads: list[dict]) -> None:
# 	"""Cancels or deletes trashed mails in the given threads."""

# 	for thread in threads:
# 		mails = [
# 			d for d in get_mail_thread(thread["name"], thread["mail_type"], True) if d["folder"] == "Trash"
# 		]
# 		delete_or_cancel_mails(mails)

from collections import defaultdict

import frappe
from frappe import _
from frappe.query_builder.functions import Count
from frappe.utils import format_datetime, random_string

from mail.jmap import get_mailboxes_for_account
from mail.mail.doctype.email_message.email_message import EmailMessage, enqueue_fetch_changes
from mail.mail.doctype.mail_queue.mail_queue import MailQueue
from mail.utils.rate_limiter import dynamic_rate_limit
from mail.utils.validation import validate_permission_for_account


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

	EmailMessage = frappe.qb.DocType("Email Message")

	distinct_threads = (
		frappe.qb.from_(EmailMessage)
		.select(EmailMessage.thread_id)
		.distinct()
		.where(
			(EmailMessage.account == frappe.session.user)
			& (EmailMessage.mailbox_role == mailbox)
			& (EmailMessage.destroyed == 0)
		)
	)

	count = (frappe.qb.from_(distinct_threads).select(Count("*").as_("count"))).run()

	return count[0][0]


# todo:
@frappe.whitelist()
def get_mail_thread(thread_id: str) -> list[dict]:
	"""Returns mail thread for the given id."""

	EmailMessage = frappe.qb.DocType("Email Message")
	EmailMessageRecipient = frappe.qb.DocType("Email Message Recipient")
	EmailMessageReplyTo = frappe.qb.DocType("Email Message Reply To")

	rows = (
		frappe.qb.from_(EmailMessage)
		.left_join(EmailMessageRecipient)
		.on(EmailMessage.name == EmailMessageRecipient.parent)
		.left_join(EmailMessageReplyTo)
		.on(EmailMessage.name == EmailMessageReplyTo.parent)
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
			EmailMessage.mailbox_role,
			EmailMessage.has_attachment,
			EmailMessageRecipient.type,
			EmailMessageRecipient.email,
			EmailMessageRecipient.display_name,
			EmailMessageReplyTo.email.as_("reply_to"),
		)
		.where(
			(EmailMessage.account == frappe.session.user)
			& (EmailMessage.thread_id == thread_id)
			& (EmailMessage.destroyed == 0)
		)
	).run(as_dict=True)

	return group_recipients_and_add_attachments(rows)


def group_recipients_and_add_attachments(rows: list[dict]) -> list[dict]:
	"""Returns mail thread with attachments and grouped recipients."""

	grouped = {}
	messages_with_attachments = set()

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
				"mailbox_role": row["mailbox_role"],
				"has_attachment": row["has_attachment"],
				"recipients": defaultdict(list),
				"reply_to": [],
			}

			if row["has_attachment"]:
				messages_with_attachments.add(key)

		if row["email"]:
			recipient = {"email": row["email"], "display_name": row["display_name"]}
			grouped[key]["recipients"][row["type"]].append(recipient)

		if row["reply_to"] and row["reply_to"] not in grouped[key]["reply_to"]:
			grouped[key]["reply_to"].append(row["reply_to"])

	if messages_with_attachments:
		attachments = frappe.get_all(
			"Email Message Part",
			filters={
				"parenttype": "Email Message",
				"parentfield": "attachments",
				"parent": ["in", messages_with_attachments],
			},
			fields=["parent", "filename", "blob_id", "type", "size", "file_url", "disposition"],
		)

		attachments_by_parent = defaultdict(list)
		for attachment in attachments:
			parent = attachment.pop("parent")
			attachments_by_parent[parent].append(attachment)

	result = []
	for item in grouped.values():
		item["recipients"] = dict(item["recipients"])
		if item["has_attachment"]:
			item["attachments"] = attachments_by_parent[item["name"]]
		result.append(item)

	return result


@frappe.whitelist()
def fetch_attachment(blob_id: str) -> bytes:
	"""Returns the content of an attachment."""

	return EmailMessage.fetch_blob(frappe.session.user, blob_id)


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
	html_body: str | None,
	attachments: list[dict] = None,
	in_reply_to: str | None = None,
	in_reply_to_id: str | None = None,
	save_as_draft: bool = False,
) -> None:
	"""Creates new mail queue."""

	account = frappe.session.user
	doc_attachments = [
		{
			"file_url": d.get("file_url"),
			"filename": d.get("file_name", ""),
			"disposition": d.get("disposition"),
			"cid": random_string(10),
		}
		for d in attachments
	]
	recipients = [{"type": "To", "email": email} for email in to]
	recipients += [{"type": "Cc", "email": email} for email in cc]
	recipients += [{"type": "Bcc", "email": email} for email in bcc]

	MailQueue._create(
		account=account,
		from_email=from_email,
		subject=subject,
		html_body=html_body,
		in_reply_to=in_reply_to,
		in_reply_to_id=in_reply_to_id,
		attachments=doc_attachments,
		recipients=recipients,
		save_as_draft=save_as_draft,
	)


@frappe.whitelist()
def update_draft_mail(
	name: str,
	from_email: str,
	to: list[str],
	cc: list[str],
	bcc: list[str],
	subject: str | None,
	html_body: str | None,
	attachments: list[dict] = None,
	submit: bool = False,
) -> None:
	"""Creates new mail queue from existing draft message."""

	doc = frappe.get_doc("Email Message", name)
	doc.check_permission(permtype="write")

	doc.from_email = from_email
	doc.subject = subject
	doc.html_body = html_body

	doc.attachments = []
	for d in attachments or []:
		doc.append(
			"attachments",
			{
				"blob_id": d.get("blob_id", ""),
				"file_url": d.get("file_url", ""),
				"type": d.get("type", ""),
				"size": d.get("size", ""),
				"filename": d.get("filename", ""),
				"disposition": d.get("disposition"),
				"cid": random_string(10),
			},
		)

	doc.recipients = []
	for email in to:
		doc.append("recipients", {"type": "To", "email": email})
	for email in cc:
		doc.append("recipients", {"type": "Cc", "email": email})
	for email in bcc:
		doc.append("recipients", {"type": "Bcc", "email": email})

	doc.submit() if submit else doc.save_draft()


@frappe.whitelist()
def destroy_mail(name: str) -> None:
	"""Destroys the given mail."""

	EmailMessage.destroy_emails(frappe.session.user, [name])


@frappe.whitelist()
def get_mime_message(name: str) -> dict:
	"""Fetches mail mime message and related data."""

	doc = frappe.get_doc("Email Message", name)
	doc.check_permission(permtype="read")

	def get_mail_recipients(recipient_type):
		return ", ".join([d.email for d in doc.recipients if d.type == recipient_type])

	pass_or_fail = {1: _("'Pass'"), 0: _("'Fail'")}

	result = {
		"message": doc.message or doc.get_mime_message(),
		"message_id": {"label": _("Message ID"), "value": doc.message_id},
		"created_at": {
			"label": _("Created at"),
			"value": _("{0} (Delivered after {1} seconds)").format(
				format_datetime(doc.sent_at, "E, MMM d, yyyy 'at' h:mm a"),
				round(doc.received_after),
			),
		},
		"subject": {"label": _("Subject"), "value": doc.subject},
		"from": {"label": _("From"), "value": f"{doc.from_name} <{doc.from_email}>"},
		"to": {"label": _("To"), "value": get_mail_recipients("To")},
		"cc": {"label": _("CC"), "value": get_mail_recipients("Cc")},
		"bcc": {"label": _("BCC"), "value": get_mail_recipients("Bcc")},
	}

	if doc.spf_description:
		result["spf"] = {
			"label": _("SPF"),
			"value": _("{0} with IP {1}").format(pass_or_fail[doc.spf_pass], doc.from_ip),
		}
	if doc.dkim_description:
		result["dkim"] = {"label": _("DKIM"), "value": pass_or_fail[doc.dkim_pass]}
	if doc.dmarc_description:
		result["dmarc"] = {"label": _("DMARC"), "value": pass_or_fail[doc.dmarc_pass]}

	return result


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

	user = frappe.session.user
	messages = frappe.get_all(
		"Email Message",
		{"account": user, "mailbox_role": ["in", mailbox], "destroyed": 0},
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


@frappe.whitelist()
@dynamic_rate_limit()
def fetch_changes() -> None:
	"""Fetches changes for the current user's account."""

	account = frappe.session.user
	validate_permission_for_account(account)
	enqueue_fetch_changes(account)

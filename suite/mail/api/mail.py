import re
from email.utils import parseaddr
from typing import Literal

import frappe
from bs4 import BeautifulSoup
from frappe import _
from frappe.utils import is_html, now

from mail.utils.cache import get_account_for_user
from mail.utils.user import get_user_email_addresses

MailType = Literal["Incoming Mail", "Outgoing Mail"]


@frappe.whitelist()
def get_inbox_mails(start: int = 0) -> list:
	"""Returns inbox mails for the current user."""

	return get_incoming_mails("Inbox", start)


@frappe.whitelist()
def get_sent_mails(start: int = 0) -> list:
	"""Returns sent mails for the current user."""

	return get_outgoing_mails("Sent", start)


@frappe.whitelist()
def get_outbox_mails(start: int = 0) -> list:
	"""Returns outbox mails for the current user."""

	return get_outgoing_mails("Outbox", start)


@frappe.whitelist()
def get_drafts_mails(start: int = 0) -> list:
	"""Returns draft mails for the current user."""

	return get_outgoing_mails("Drafts", start)


@frappe.whitelist()
def get_spam_mails(start: int = 0) -> list:
	"""Returns spam mails for the current user."""

	return get_incoming_mails("Spam", start)


@frappe.whitelist()
def get_trash_mails(start: int = 0) -> list:
	"""Returns trash mails for the current user."""

	trash_mails = get_incoming_mails("Trash", start, False) + get_outgoing_mails("Trash", start, False)
	trash_mails.sort(key=lambda x: x.creation, reverse=True)

	return get_mail_list(trash_mails)


def get_incoming_mails(folder: str, start: int = 0, get_list: bool = True) -> list:
	"""Returns incoming mails for the current user."""

	account = get_account_for_user(frappe.session.user)
	mails = frappe.get_all(
		"Incoming Mail",
		{"receiver": account, "docstatus": 1, "folder": folder},
		[
			"name",
			"sender",
			"body_html",
			"body_plain",
			"display_name",
			"subject",
			"creation",
			"in_reply_to_mail_name",
			"in_reply_to_mail_type",
			"status",
			"type",
			"seen",
			"message_id",
			"'Incoming Mail' as mail_type",
		],
		limit=50,
		start=start,
		order_by="created_at desc",
	)

	return get_mail_list(mails) if get_list else mails


def get_outgoing_mails(folder: str, start: int = 0, get_list: bool = True) -> list:
	"""Returns outgoing mails for the current user."""

	account = get_account_for_user(frappe.session.user)

	if folder == "Drafts":
		order_by = "modified desc"
	else:
		# TODO: fix sorting
		order_by = "created_at desc"

	mails = frappe.get_all(
		"Outgoing Mail",
		{"sender": account, "docstatus": ["!=", 2], "folder": folder},
		[
			"name",
			"subject",
			"sender",
			"body_html",
			"body_plain",
			"creation",
			"display_name",
			"in_reply_to_mail_name",
			"in_reply_to_mail_type",
			"status",
			"message_id",
			"seen",
			"'Outgoing Mail' as mail_type",
		],
		limit=50,
		start=start,
		order_by=order_by,
	)

	return get_mail_list(mails) if get_list else mails


def get_mail_list(mails) -> list:
	"""Returns a list of mails with additional details."""

	attachments = get_attachments([mail.name for mail in mails])

	for mail in mails[:]:
		mail.attachments = [
			attachment for attachment in attachments if attachment.attached_to_name == mail.name
		]
		thread = get_list_thread(mail)
		thread_with_names = [email.name for email in thread]
		mails_in_original_list = [email for email in mails if email.name in thread_with_names]
		if len(mails_in_original_list) > 1:
			latest_mail = max(mails_in_original_list, key=lambda x: x.creation)
			mails_in_original_list.remove(latest_mail)

			for email in mails_in_original_list:
				mails.remove(email)

	for mail in mails:
		mail.latest_content = get_latest_content(mail.body_html, mail.body_plain)
		mail.snippet = get_snippet(mail.latest_content) if mail.latest_content else ""

	return mails


def has_in_reply_to_mail(mail) -> bool:
	"""Check if the mail is a reply to an existing mail."""

	if not mail.in_reply_to_mail_name:
		return False

	return frappe.db.exists(
		mail.in_reply_to_mail_type, {"name": mail.in_reply_to_mail_name, "docstatus": ("!=", 2)}
	)


def get_list_thread(mail) -> list:
	"""Returns a list of mails in the thread."""

	thread = []
	processed = set()

	def add_to_thread(mail):
		if mail.name in processed:
			return
		processed.add(mail.name)
		thread.append(mail)

		if has_in_reply_to_mail(mail):
			reply_mail = get_mail_details(mail.in_reply_to_mail_name, mail.in_reply_to_mail_type, False)
			add_to_thread(reply_mail)
		if mail.message_id:
			replica_name = find_replica(mail, mail.mail_type)
			if replica_name:
				replica = get_mail_details(replica_name, reverse_type(mail.mail_type), False)
				add_to_thread(replica)

	add_to_thread(mail)
	return thread


def get_latest_content(html, plain) -> str:
	"""Returns the latest content from the mail."""

	content = html if html else plain
	if content is None:
		return ""

	if is_html(content):
		soup = BeautifulSoup(content, "html.parser")
		blockquote = soup.find("blockquote")
		if blockquote:
			blockquote.extract()
		return soup.get_text(strip=True)

	return content


def get_snippet(content) -> str:
	"""Returns a snippet of the content."""

	content = re.sub(
		r"(?<=[.,])(?=[^\s])", r" ", content
	)  # add space after . and , if not followed by a space
	return " ".join(content.split()[:50])


@frappe.whitelist()
def get_mail_thread(name: str, mail_type: MailType, just_names: bool = False) -> list:
	"""Returns the mail thread for the given mail."""

	if not frappe.db.exists(mail_type, name):
		frappe.throw(
			_("{0}: {1} does not exist.").format(mail_type, frappe.bold(name)),
			frappe.DoesNotExistError,
		)

	mail = get_mail_details(name, mail_type, True, just_names)
	mail.mail_type = mail_type

	original_replica = find_replica(mail, mail_type)

	thread = []
	visited = set()

	def get_thread(mail, thread):
		thread.append(mail)
		if mail.name in visited:
			return
		visited.add(mail.name)

		if has_in_reply_to_mail(mail):
			reply_mail = get_mail_details(
				mail.in_reply_to_mail_name, mail.in_reply_to_mail_type, True, just_names
			)
			get_thread(reply_mail, thread)

		replica = find_replica(mail, mail.mail_type)
		if replica and replica != name:
			replica_type = reverse_type(mail.mail_type)
			replica_mail = get_mail_details(replica, replica_type, True, just_names)
			replica_mail.mail_type = replica_type
			get_thread(replica_mail, thread)
		else:
			replies = []
			replies += gather_thread_replies(name)
			if original_replica:
				replies += gather_thread_replies(original_replica)

			for reply in replies:
				if reply.name not in visited:
					get_thread(reply, thread)

	get_thread(mail, thread)
	thread = remove_duplicates_and_sort(thread)
	return thread


def reverse_type(mail_type: MailType) -> str:
	"""Returns the reverse mail type."""

	return "Incoming Mail" if mail_type == "Outgoing Mail" else "Outgoing Mail"


def gather_thread_replies(mail_name) -> list:
	"""Gathers all replies in the thread."""

	thread = []
	thread += get_thread_from_replies("Outgoing Mail", mail_name)
	thread += get_thread_from_replies("Incoming Mail", mail_name)
	return thread


def get_thread_from_replies(mail_type: MailType, mail_name) -> list:
	"""Returns the thread from the replies."""

	replies = []
	emails = frappe.get_all(mail_type, {"in_reply_to_mail_name": mail_name, "docstatus": 1}, pluck="name")
	for email in emails:
		reply = get_mail_details(email, mail_type, True)
		reply.mail_type = mail_type
		replies.append(reply)

	return replies


def find_replica(mail, mail_type: MailType) -> str:
	"""Returns the replica of the mail."""

	replica_type = reverse_type(mail_type)
	return frappe.db.exists(replica_type, {"message_id": mail.message_id})


def remove_duplicates_and_sort(thread) -> list:
	"""Removes duplicates and sorts the thread."""

	seen = set()
	thread = [x for x in thread if x["name"] not in seen and not seen.add(x["name"])]
	thread = [x for x in thread if x["message_id"] not in seen and not seen.add(x["message_id"])]
	thread.sort(key=lambda x: x.creation)
	return thread


def get_mail_details(
	name: str, type: str, include_all_details: bool = False, just_names: bool = False
) -> dict:
	"""Returns the mail details."""

	fields = [
		"name",
		"folder",
		"in_reply_to_mail_name",
		"in_reply_to_mail_type",
		"message_id",
		"creation",
		"docstatus",
	]

	if not just_names:
		fields.extend(
			[
				"subject",
				"body_html",
				"body_plain",
				"sender",
				"display_name",
				"modified",
				"reply_to",
				"seen",
			]
		)

		if type == "Outgoing Mail":
			fields.extend(["from_", "status"])
		else:
			fields.extend(["delivered_to", "type"])

	mail = frappe.db.get_value(type, name, fields, as_dict=1)
	mail.mail_type = type

	if just_names:
		return mail

	mail.attachments = get_attachments_for_mail(type, name)

	if not include_all_details:
		return mail

	if not mail.get("display_name"):
		mail.display_name = frappe.db.get_value("User", mail.sender, "full_name")

	mail.user_image = frappe.db.get_value("User", mail.sender, "user_image")
	mail.latest_content = get_latest_content(mail.body_html, mail.body_plain)
	mail.to = get_recipients(name, type, "To")
	mail.cc = get_recipients(name, type, "Cc")
	mail.bcc = get_recipients(name, type, "Bcc")
	mail.body_html = extract_email_body(mail.body_html)
	mail.mail_type = type
	return mail


def extract_email_body(html: str) -> str | None:
	"""Extracts the email body from the html content."""

	if not html:
		return None

	soup = BeautifulSoup(html, "html.parser")
	div = soup.select_one("table.email-body div")

	return div.prettify() if div else html


def get_recipients(name, type, recipient_type) -> list:
	"""Returns the recipients of the mail."""

	recipients = frappe.get_all(
		"Mail Recipient",
		{"parent": name, "parenttype": type, "type": recipient_type},
		["email", "display_name", "type"],
	)

	for recipient in recipients:
		if not recipient.display_name:
			recipient.display_name = frappe.db.get_value("User", recipient.email, "full_name")

	return recipients


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


def get_attachments(names: list[str]):
	"""Fetches mail attachments."""

	return frappe.get_all(
		"File",
		fields=["attached_to_name", "name", "file_name", "file_url", "file_size"],
		filters={
			"attached_to_name": ["in", names],
			"attached_to_doctype": ["in", ["Incoming Mail", "Outgoing Mail"]],
		},
	)


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
def set_seen(mails: list[dict], seen: int) -> dict:
	"""Sets seen for mails."""

	for mail in mails:
		doc = frappe.get_doc(mail["mail_type"], mail["name"])
		doc.db_set("seen", seen)

	return {"names": [d["name"] for d in mails], "seen": seen}


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


@frappe.whitelist()
def set_folder_for_threads(threads: list[dict], move_to_trash: bool = False) -> None:
	"""Moves threads to trash."""

	for thread in threads:
		for mail in get_mail_thread(thread["name"], thread["mail_type"], True):
			set_folder(mail.mail_type, mail.name, move_to_trash)


@frappe.whitelist()
def delete_or_cancel_threads(threads: list[dict]) -> None:
	"""Cancels or deletes trashed mails in the given threads."""

	for thread in threads:
		mails = [
			d for d in get_mail_thread(thread["name"], thread["mail_type"], True) if d["folder"] == "Trash"
		]
		delete_or_cancel_mails(mails)

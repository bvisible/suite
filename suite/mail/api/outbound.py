from email.utils import parseaddr

import frappe
from frappe import _

from mail.mail.doctype.mail_queue.mail_queue import MailQueue
from mail.utils.cache import get_account_for_user
from mail.utils.rate_limiter import dynamic_rate_limit


@frappe.whitelist(methods=["POST"])
@dynamic_rate_limit()
def send(
	from_: str,
	subject: str,
	to: str | list[str] | None = None,
	cc: str | list[str] | None = None,
	bcc: str | list[str] | None = None,
	html: str | None = None,
	text: str | None = None,
	reply_to: str | list[str] | None = None,
	in_reply_to: str | None = None,
	headers: dict | None = None,
	attachments: list[dict] | None = None,
	is_newsletter: bool = False,
	save_as_draft: bool = False,
) -> str:
	"""Send Mail."""

	from_name, from_email = parseaddr(from_)
	doc = MailQueue._create(
		account=get_account(),
		from_name=from_name,
		from_email=from_email,
		subject=subject,
		reply_to=format_reply_to(reply_to),
		headers=headers,
		recipients=format_recipients(to, cc, bcc),
		attachments="",
		html_body=html,
		text_body=text,
		via_api=True,
		in_reply_to=in_reply_to,
		save_as_draft=save_as_draft,
		destroy_after_submission=False,
		delivery_mode="Batch" if is_newsletter else "Enqueue",
	)

	return doc.name


@frappe.whitelist(methods=["POST"])
@dynamic_rate_limit()
def send_raw(
	from_: str,
	to: str | list[str],
	raw_message: str | None = None,
	is_newsletter: bool = False,
) -> str:
	"""Send Raw Mail."""

	from_name, from_email = parseaddr(from_)
	raw_message = raw_message or get_message_from_files()
	if not raw_message:
		frappe.throw(_("The raw message is required."), frappe.MandatoryError)

	doc = MailQueue._create(
		account=get_account(),
		from_name=from_name,
		from_email=from_email,
		recipients=format_recipients(to),
		via_api=True,
		raw_message=raw_message,
		delivery_mode="Batch" if is_newsletter else "Enqueue",
	)

	return doc.name


def get_account() -> str:
	"""Returns the mail account for the current user."""

	user = frappe.session.user

	if account := get_account_for_user(user):
		return account

	frappe.throw(_("No Mail Account found for the user {0}.").format(frappe.bold(user)))


def get_message_from_files() -> str | None:
	"""Returns the message from the files"""

	files = frappe._dict(frappe.request.files)

	if files and files.get("raw_message"):
		return files["raw_message"].read().decode("utf-8")


def format_recipients(
	to: str | list[str] | None = None, cc: str | list[str] | None = None, bcc: str | list[str] | None = None
) -> list[dict]:
	"""Formats the recipients for the mail queue."""

	recipients = []

	if to:
		recipients.extend(_normalize_recipients(to, "To"))
	if cc:
		recipients.extend(_normalize_recipients(cc, "Cc"))
	if bcc:
		recipients.extend(_normalize_recipients(bcc, "Bcc"))

	return recipients


def format_reply_to(reply_to: str | list[str] | None) -> list[dict]:
	"""Formats the reply_to field for the mail queue."""

	if not reply_to:
		return []
	return _normalize_recipients(reply_to)


def _normalize_recipients(
	recipients: str | list[str] | None, recipient_type: str | None = None
) -> list[dict]:
	"""Helper to normalize recipients into a list of dicts."""

	if isinstance(recipients, str):
		recipients = [recipients]

	result = []
	for recipient in recipients:
		name, email = parseaddr(recipient)
		recipient_dict = {"name": name, "email": email}
		if recipient_type:
			recipient_dict["type"] = recipient_type
		result.append(recipient_dict)

	return result

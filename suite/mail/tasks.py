import frappe

from mail.mail.doctype.dns_record.dns_record import verify_all_dns_records
from mail.mail.doctype.incoming_mail.incoming_mail import fetch_emails_from_clusters
from mail.mail.doctype.outgoing_mail.outgoing_mail import delete_newsletters, transfer_mails_to_clusters
from mail.utils import enqueue_job


@frappe.whitelist()
def enqueue_transfer_mails_to_clusters() -> None:
	"Called by the scheduler to enqueue the `transfer_mails_to_clusters` job."

	frappe.session.user = "Administrator"
	enqueue_job(transfer_mails_to_clusters, queue="long", deduplicate=True)


@frappe.whitelist()
def enqueue_delete_newsletters() -> None:
	"Called by the scheduler to enqueue the `delete_newsletters` job."

	frappe.session.user = "Administrator"
	enqueue_job(delete_newsletters, queue="long", deduplicate=True)


@frappe.whitelist()
def enqueue_fetch_emails_from_clusters() -> None:
	"Called by the scheduler to enqueue the `fetch_emails_from_clusters` job."

	frappe.session.user = "Administrator"
	enqueue_job(fetch_emails_from_clusters, queue="long", deduplicate=True)


@frappe.whitelist()
def enqueue_verify_all_dns_records() -> None:
	"Called by the scheduler to enqueue the `verify_all_dns_records` job."

	frappe.only_for("System Manager")

	frappe.session.user = "Administrator"
	enqueue_job(verify_all_dns_records, queue="long", deduplicate=True)

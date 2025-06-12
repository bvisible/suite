import frappe
from frappe.core.api.file import create_new_folder

from mail.mail.doctype.rate_limit.rate_limit import create_rate_limit


def after_install() -> None:
	add_rate_limits()
	create_default_tenant()
	create_new_folder("Frappe Mail", "Home")


def add_rate_limits() -> None:
	"""Add rate limits."""

	rate_limits = [
		# mail.api.account
		{"method_path": "mail.api.account.personal_signup", "limit": 5, "seconds": 60 * 60},
		{"method_path": "mail.api.account.business_signup", "limit": 5, "seconds": 60 * 60},
		{"method_path": "mail.api.account.resend_otp", "limit": 5, "seconds": 60 * 60},
		{"method_path": "mail.api.account.verify_otp", "limit": 5, "seconds": 60 * 60},
		{"method_path": "mail.api.account.get_account_request", "limit": 5, "seconds": 60 * 60},
		{"method_path": "mail.api.account.create_account", "limit": 10, "seconds": 60 * 60},
		{"method_path": "mail.api.account.send_reset_password_link", "limit": 5, "seconds": 60 * 60},
		{"method_path": "mail.api.account.validate_email_assigned", "limit": 10, "seconds": 60 * 60},
		# mail.api.admin
		{"method_path": "mail.api.admin.verify_dns_record", "limit": 10, "seconds": 60 * 60},
		{"method_path": "mail.api.admin.add_member", "limit": 10, "seconds": 60 * 60},
		# mail.api.inbound
		{"method_path": "mail.api.inbound.fetch_blob", "limit": 60, "seconds": 60},
		{"method_path": "mail.api.inbound.pull", "limit": 10, "seconds": 60},
		{"method_path": "mail.api.inbound.pull_raw", "limit": 10, "seconds": 60},
		# mail.api.outbound
		{"method_path": "mail.api.outbound.upload_attachment", "limit": 60, "seconds": 60},
		{"method_path": "mail.api.outbound.send", "limit": 300, "seconds": 60},
		{"method_path": "mail.api.outbound.send_raw", "limit": 300, "seconds": 60},
		# mail.api.spamd
		{"method_path": "mail.api.spamd.scan", "limit": 60, "seconds": 60},
		{"method_path": "mail.api.spamd.get_spam_score", "limit": 60, "seconds": 60},
		# mail.api.mail
		{"method_path": "mail.api.mail.fetch_changes", "limit": 10, "seconds": 60},
	]

	for rl in rate_limits:
		create_rate_limit(**rl)


def create_default_tenant() -> None:
	"""Create the default tenant."""

	tenant = frappe.new_doc("Mail Tenant")
	tenant.tenant_name = "Frappe Mail"
	tenant.user = "Administrator"
	tenant.allow_personal_signup = 1
	tenant.insert(ignore_permissions=True)

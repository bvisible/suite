import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, get_datetime, get_url, now_datetime
from frappe.utils.data import sha256_hash

from mail.mail.doctype.mail_account.mail_account import create_user
from mail.utils.cache import get_default_outgoing_email_for_user
from mail.utils.rate_limiter import dynamic_rate_limit


@frappe.whitelist(allow_guest=True)
@dynamic_rate_limit()
def self_signup(email: str) -> str:
	"""Create a new Mail Account Request for self signup"""

	account_request = frappe.new_doc("Mail Account Request")
	account_request.email = email
	account_request.is_admin = 1
	account_request.send_invite = 1
	account_request.insert(ignore_permissions=True)

	return account_request.name


@frappe.whitelist(allow_guest=True)
@dynamic_rate_limit()
def resend_otp(account_request: str) -> None:
	"""Resend OTP to the user"""

	account_request = frappe.get_doc("Mail Account Request", account_request)
	account_request.set_otp()
	account_request.save(ignore_permissions=True)
	account_request.send_verification_email()


@frappe.whitelist(allow_guest=True)
@dynamic_rate_limit()
def verify_otp(account_request: str, otp: str) -> str:
	"""Verify the OTP and return the request key"""

	otp_hash = frappe.cache.get_value(f"account_request_otp_hash:{account_request}", expires=True)
	if not otp_hash or otp_hash != frappe.utils.sha256_hash(otp):
		frappe.throw(_("Invalid OTP. Please try again."))

	frappe.cache.delete_value(f"account_request_otp_hash:{account_request}")
	return frappe.db.get_value("Mail Account Request", account_request, "request_key")


@frappe.whitelist(allow_guest=True)
@dynamic_rate_limit()
def get_account_request(request_key: str) -> dict | None:
	"""Return the account request details"""

	if account_request := frappe.db.get_value(
		"Mail Account Request",
		{"request_key": request_key},
		["email", "is_verified", "expires_at", "account"],
		as_dict=True,
	):
		is_expired = 0
		if expires_at := account_request["expires_at"]:
			is_expired = cint(get_datetime(expires_at) < now_datetime())
		account_request.pop("expires_at")
		account_request["is_expired"] = is_expired
		return account_request


@frappe.whitelist(allow_guest=True)
@dynamic_rate_limit()
def create_account(request_key: str, first_name: str, last_name: str, password: str) -> None:
	"""Create a new user account"""

	account_request = frappe.get_last_doc("Mail Account Request", {"request_key": request_key})
	account_request.validate_expired()
	account_request.is_verified = 1
	account_request.save(ignore_permissions=True)

	if account_request.account:
		account_request.create_account(first_name, last_name, password)

	else:
		create_user(account_request.email, first_name, last_name, password, ["Mail Admin"])


@frappe.whitelist(allow_guest=True)
def get_user_info() -> dict:
	"""Returns user information."""

	if frappe.session.user == "Guest":
		return None

	user = frappe.db.get_value(
		"User",
		frappe.session.user,
		["name", "email", "enabled", "user_image", "full_name", "user_type", "username", "api_key"],
		as_dict=1,
	)
	user["roles"] = frappe.get_roles(user.name)
	user.tenant = frappe.db.get_value("Mail Tenant Member", {"user": frappe.session.user}, "tenant")
	user.is_mail_user = "Mail User" in user.roles
	user.is_mail_admin = "Mail Admin" in user.roles

	if user.tenant:
		user.tenant_name, tenant_owner = frappe.db.get_value(
			"Mail Tenant", user.tenant, ["tenant_name", "user"]
		)
		user.is_tenant_owner = tenant_owner == frappe.session.user

	user.default_outgoing = get_default_outgoing_email_for_user(frappe.session.user)

	return user


def get_backup_email(email: str) -> str:
	"""Return backup email for a user or the user's email if backup doesn't exist"""

	if backup_email := frappe.db.get_value("Mail Account", email, "backup_email"):
		return backup_email

	if frappe.db.exists("User", email):
		return email

	frappe.throw(_("User {0} does not exist.").format(frappe.bold(email)))


def set_reset_password_key(email: str) -> str:
	"""Generate and store a reset password key for a user"""

	key = frappe.generate_hash()
	hashed_key = sha256_hash(key)
	frappe.db.set_value(
		"User",
		email,
		{"reset_password_key": hashed_key, "last_reset_password_key_generated_on": now_datetime()},
	)
	return key


def censor_email(email: str) -> str:
	"""Censor the email address to protect privacy"""

	username, domain = email.split("@")
	censored_username = username[0] + "*" * (len(username) - 1)
	return f"{censored_username}@{domain}"


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60 * 60)
def send_reset_password_link(email: str) -> str:
	"""Send reset password link to the user"""

	user = get_backup_email(email)
	key = set_reset_password_key(email)

	frappe.sendmail(
		recipients=user,
		subject=_("Reset Password"),
		template="reset_password",
		args={"link": get_url("/mail/reset-password/" + key)},
		now=True,
	)

	if user == email:
		return user
	return censor_email(user)


@frappe.whitelist(allow_guest=True)
def get_user_for_reset_password_key(key: str) -> str:
	"""Return the user for a reset password key"""

	hashed_key = sha256_hash(key)
	return frappe.db.get_value("User", {"reset_password_key": hashed_key}, "name")

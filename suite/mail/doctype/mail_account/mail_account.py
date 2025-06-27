# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from email.utils import parseaddr

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now, random_string, validate_email_address
from frappe.utils.data import convert_utc_to_system_timezone, get_datetime

from mail.backend import MailBackendAccountManager, MailBackendIdentityManager
from mail.jmap import get_jmap_client, invalidate_jmap_cache
from mail.mail.doctype.jmap_sync_state.jmap_sync_state import create_jmap_sync_state
from mail.utils import (
	enqueue_job,
	generate_uuid_style_hash,
	get_postmaster_address,
	hash_password,
	normalize_email,
	user_context,
)
from mail.utils.cache import (
	get_aliases_for_user,
	get_cluster_for_tenant,
	get_tenant_for_domain,
	get_tenant_for_user,
)
from mail.utils.dt import convert_to_utc
from mail.utils.user import has_role, is_system_manager, is_tenant_admin
from mail.utils.validation import (
	is_email_assigned,
	is_subaddressed_email,
	is_valid_email_for_domain,
	validate_domain_is_enabled_and_verified,
	validate_domain_owned_by_tenant,
	validate_permission_for_account,
)


class MailAccount(Document):
	def autoname(self) -> None:
		self.email = self.email.strip().lower()
		self.name = self.email

	def before_validate(self) -> None:
		self.set_tenant()

	def validate(self) -> None:
		self.validate_enabled()
		self.validate_domain()
		self.validate_user()
		self.validate_user_tenant()
		self.validate_tenant_max_accounts()
		self.validate_email()
		self.set_normalized_email()
		self.validate_password()
		self.validate_default_outgoing_email()
		self.validate_display_name()
		self.validate_reply_to()
		self.validate_backup_email()
		self.validate_vacation_response()

	def after_insert(self) -> None:
		create_jmap_sync_state(self.name)

	def on_update(self) -> None:
		self.clear_cache()

		if self.enabled:
			if self.has_value_changed("enabled") or self.has_value_changed("email"):
				MailBackendAccountManager("Mail Cluster", get_cluster_for_tenant(self.tenant)).create(
					self.email, self.display_name, self.secret
				)
			elif self.has_value_changed("display_name") or self.has_value_changed("secret"):
				MailBackendAccountManager("Mail Cluster", get_cluster_for_tenant(self.tenant)).update(
					self.email, self.display_name, self.secret, self.get_doc_before_save().secret
				)

				if self.has_value_changed("secret"):
					invalidate_jmap_cache(self.name)

			vacation_response_updated = False
			if previous_doc := self.get_doc_before_save():
				for field in [
					"vacation_response_enabled",
					"vacation_from_date",
					"vacation_to_date",
					"vacation_response_subject",
					"vacation_response_text_body",
					"vacation_response_html_body",
				]:
					if getattr(self, field) != getattr(previous_doc, field):
						vacation_response_updated = True
						break

			if vacation_response_updated:
				from_date = convert_to_utc(self.vacation_from_date).isoformat()
				to_date = convert_to_utc(self.vacation_to_date).isoformat()

				try:
					client = get_jmap_client(self.name)
					response = client.vacation_response_set(
						bool(self.vacation_response_enabled),
						from_date,
						to_date,
						self.vacation_response_subject,
						self.vacation_response_text_body,
						self.vacation_response_html_body,
					)
					self._db_set(vacation_response_state=response["newState"])
				except Exception:
					frappe.log_error(
						title=_("Failed to create or update vacation response"),
						message=frappe.get_traceback(with_context=True),
					)
					frappe.throw(_("Failed to create or update vacation response."))

		elif self.has_value_changed("enabled"):
			MailBackendAccountManager("Mail Cluster", get_cluster_for_tenant(self.tenant)).delete(self.email)

	def on_trash(self) -> None:
		self.clear_cache()

		if self.enabled:
			MailBackendAccountManager("Mail Cluster", get_cluster_for_tenant(self.tenant)).delete(self.email)

	def set_tenant(self) -> None:
		"""Sets the tenant based on the domain."""

		if not self.tenant:
			self.tenant = get_tenant_for_domain(self.domain_name)

	def validate_enabled(self) -> None:
		"""Validates the enabled field."""

		if self.enabled:
			return

		if alias := frappe.db.exists(
			"Mail Alias", {"enabled": 1, "alias_for_type": self.doctype, "alias_for_name": self.name}
		):
			frappe.throw(
				_("The account is linked to Mail Alias {0}. Please disable it first.").format(
					frappe.bold(alias)
				)
			)

		if frappe.db.exists("Mailing List Member", {"member_type": self.doctype, "member_name": self.name}):
			frappe.throw(_("The account is linked to a Mailing List as a member. Please remove it first."))

	def validate_domain(self) -> None:
		"""Validates the domain."""

		validate_domain_owned_by_tenant(self.domain_name, self.tenant)
		validate_domain_is_enabled_and_verified(self.domain_name)

	def validate_user(self) -> None:
		"""Validates the user."""

		if not has_role(self.user, "Mail User"):
			frappe.throw(_("User {0} does not have Mail User role.").format(frappe.bold(self.user)))

	def validate_user_tenant(self) -> None:
		"""Validates the user tenant."""

		if self.is_new() or self.enabled:
			if self.tenant != get_tenant_for_user(self.user):
				frappe.throw(
					_("Domain {0} and User {1} must belong to the same tenant.").format(
						frappe.bold(self.domain_name), frappe.bold(self.user)
					)
				)

	def validate_tenant_max_accounts(self) -> None:
		"""Validates the Tenant Max Accounts."""

		total_accounts = frappe.db.count("Mail Account", filters={"tenant": self.tenant, "enabled": 1})
		max_accounts = frappe.db.get_value("Mail Tenant", self.tenant, "max_accounts")
		if total_accounts >= max_accounts:
			frappe.throw(
				_("You have reached the maximum limit of {0} accounts for the tenant.").format(
					frappe.bold(max_accounts)
				)
			)

	def validate_email(self) -> None:
		"""Validates the email address."""

		if not self.email:
			frappe.throw(_("Email is mandatory."))
		is_subaddressed_email(self.email, raise_exception=True)
		is_email_assigned(self.email, self.doctype, raise_exception=True)
		is_valid_email_for_domain(self.email, self.domain_name, raise_exception=True)

	def set_normalized_email(self) -> None:
		"""Sets the normalized email."""

		if not self.normalized_email:
			self.normalized_email = normalize_email(self.email)

	def validate_password(self) -> None:
		"""Generates secret if password is changed"""

		if not self.password:
			self._generate_password()

		if not self.is_new():
			if previous_doc := self.get_doc_before_save():
				if previous_doc.get_password("password") == self.get_password("password"):
					return

		self.generate_secret()

	def validate_default_outgoing_email(self) -> None:
		"""Validates the default outgoing email."""

		if not self.default_outgoing_email:
			self.default_outgoing_email = self.email
		else:
			if self.default_outgoing_email not in [self.email] + get_aliases_for_user(self.user):
				frappe.throw(_("Default Email must be one of the email addresses assigned to the user."))

	def validate_display_name(self) -> None:
		"""Validates the display name."""

		if self.is_new() and not self.display_name:
			self.display_name = frappe.db.get_value("User", self.user, "full_name")

	def validate_reply_to(self) -> None:
		"""Validates the reply-to addresses."""

		if not self.reply_to:
			return

		reply_to = {}
		for rt in self.reply_to.split(","):
			rt = rt.strip()
			display_name, email = parseaddr(rt)

			if not email:
				frappe.throw(_("Invalid reply-to address: {0}").format(frappe.bold(rt)))

			reply_to[email] = display_name

		self.reply_to = ", ".join([f"{display_name} <{email}>" for email, display_name in reply_to.items()])

	def validate_backup_email(self) -> None:
		"""Validates the backup email."""

		validate_email_address(self.backup_email, True)

	def validate_vacation_response(self) -> None:
		"""Validates the vacation response settings."""

		if self.is_new():
			self.vacation_response_enabled = 0
			self.vacation_from_date = None
			self.vacation_to_date = None
			self.vacation_response_subject = None
			self.vacation_response_text_body = None
			self.vacation_response_html_body = None
		else:
			if self.vacation_response_enabled:
				if not self.vacation_from_date:
					frappe.throw(_("Vacation - {0} is required.").format(frappe.bold(_("From Date"))))
				if not self.vacation_to_date:
					frappe.throw(_("Vacation - {0} is required.").format(frappe.bold(_("To Date"))))
				elif self.vacation_to_date < now():
					frappe.throw(_("Vacation - {0} cannot be in the past.").format(frappe.bold(_("To Date"))))
				elif self.vacation_from_date >= self.vacation_to_date:
					frappe.throw(
						_("Vacation - {0} cannot be before Vacation - {1}.").format(
							frappe.bold(_("To Date")), frappe.bold(_("From Date"))
						)
					)

	def clear_cache(self) -> None:
		"""Clears the Cache."""

		frappe.cache.hdel(f"user|{self.user}", ["account", "default_outgoing_email"])
		frappe.cache.hdel(f"email|{self.email}", "account")

	def generate_secret(self) -> None:
		"""Generates secret from password"""

		password = self.get_password("password")
		self.secret = hash_password(password)

	@frappe.whitelist()
	def get_account_password(self) -> str:
		"""Returns the password for the Mail Account."""

		validate_permission_for_account(self.name)
		return self.get_password("password")

	@frappe.whitelist()
	def sync_jmap_identities(self) -> None:
		"""Syncs JMAP identities for the Mail Account."""

		frappe.only_for("System Manager")
		self._sync_jmap_identities()

	@frappe.whitelist()
	def regenerate_password(self) -> None:
		"""Regenerates the password for the Mail Account."""

		validate_permission_for_account(self.name)
		self._generate_password()
		self.save()

		frappe.msgprint(_("Password has been regenerated."), alert=True, indicator="green")

	def _generate_password(self) -> None:
		"""Generates a random password for the Mail Account."""

		self.password = random_string(length=20)

	def _sync_jmap_identities(self) -> None:
		"""Syncs JMAP identities for the Mail Account."""

		account_id = get_jmap_client(self.name).account_id
		aliases = frappe.db.get_all(
			"Mail Alias",
			{"enabled": 1, "alias_for_type": "Mail Account", "alias_for_name": self.name},
			pluck="email",
		)

		reply_to = []
		if self.reply_to:
			for rt in self.reply_to.split(","):
				rt = rt.strip()
				display_name, email = parseaddr(rt)
				reply_to.append({"name": display_name, "email": email})

		identities = {
			generate_uuid_style_hash(self.email): {
				"name": self.display_name,
				"email": self.email,
				"replyTo": reply_to or None,
				"bcc": None,
				"textSignature": None,
				"htmlSignature": None,
			}
		}

		for alias in aliases:
			identities[generate_uuid_style_hash(alias)] = {
				"name": self.display_name,
				"email": alias,
				"replyTo": reply_to or None,
				"bcc": None,
				"textSignature": None,
				"htmlSignature": None,
			}

		MailBackendIdentityManager("Mail Cluster", get_cluster_for_tenant(self.tenant)).sync(
			account_id, identities
		)

		invalidate_jmap_cache(self.name)

	def _db_set(
		self,
		update_modified: bool = True,
		commit: bool = False,
		notify: bool = False,
		**kwargs,
	) -> None:
		"""Updates the document with the given key-value pairs."""

		self.db_set(kwargs, update_modified=update_modified, notify=notify, commit=commit)


def _create_user_for_mail_account(
	email: str,
	first_name: str,
	last_name: str | None = None,
	password: str | None = None,
	is_admin: bool = False,
) -> str:
	"""Creates a User for Mail Account"""

	if frappe.db.exists("User", {"email": email}):
		frappe.throw(_("User with email {0} already exists.").format(frappe.bold(email)))

	roles = ["Mail User"]
	if is_admin:
		roles.append("Mail Admin")

	return create_user(email, first_name, last_name, password, roles)


def create_user(
	email: str,
	first_name: str,
	last_name: str | None = None,
	password: str | None = None,
	roles: list[str] | None = None,
) -> str:
	"""Creates a User document"""

	user = frappe.new_doc("User")
	user.first_name = first_name
	user.last_name = last_name
	user.username = email
	user.email = email
	user.owner = email
	user.send_welcome_email = 0
	if roles:
		user.append_roles(*roles)
	if password:
		user.new_password = password
	user.insert(ignore_permissions=True)

	return user.name


def _add_user_to_tenant(tenant: str, user: str, is_admin: bool) -> None:
	"""Adds a User to a Tenant"""

	tenant = frappe.get_doc("Mail Tenant", tenant)
	tenant.add_member(user, is_admin)


def create_mail_account(
	tenant: str,
	email: str,
	backup_email: str,
	first_name: str,
	last_name: str | None = None,
	password: str | None = None,
	is_admin: bool = False,
) -> "MailAccount":
	"""Creates a Mail Account"""

	if frappe.db.exists("Mail Account", email):
		frappe.throw(_("Mail Account {0} already exists.").format(frappe.bold(email)))

	user = _create_user_for_mail_account(email, first_name, last_name, password, is_admin)
	_add_user_to_tenant(tenant, user, is_admin)
	account = frappe.new_doc("Mail Account")
	account.domain_name = email.split("@")[1]
	account.user = user
	account.backup_email = backup_email
	account.insert(ignore_permissions=True)

	return account


def create_postmaster_account(tenant: str) -> None:
	"""Creates a Postmaster account."""

	frappe.flags.ignore_domain_validation = True
	postmaster_address = get_postmaster_address()
	create_mail_account(
		tenant=tenant, email=postmaster_address, backup_email=postmaster_address, first_name="Postmaster"
	)


def sync_jmap_identities(account: str) -> None:
	"""Sync JMAP identities for the given mail account."""

	if not frappe.db.exists("Mail Account", account):
		return

	doc = frappe.get_doc("Mail Account", account)
	doc._sync_jmap_identities()


def enqueue_sync_jmap_vacation_response(account: str, new_state: str | None = None) -> None:
	"""Enqueue a job to sync JMAP vacation response for the given mail account."""

	with user_context("Administrator"):
		enqueue_job(
			sync_jmap_vacation_response,
			account=account,
			new_state=new_state,
			queue="short",
			deduplicate=True,
			enqueue_after_commit=True,
		)


@frappe.whitelist()
def sync_jmap_vacation_response(
	account: str, new_state: str | None = None, raise_exception: bool = False
) -> None:
	"""Sync JMAP vacation response for the given mail account."""

	if not frappe.db.exists("Mail Account", account):
		return

	doc = frappe.get_doc("Mail Account", account)

	if new_state and doc.vacation_response_state == new_state:
		return

	try:
		client = get_jmap_client(doc.name)
		response, new_state = client.vacation_response_get()

		if response:
			from_date = (
				convert_utc_to_system_timezone(get_datetime(response["fromDate"]))
				if response["fromDate"]
				else None
			)
			to_date = (
				convert_utc_to_system_timezone(get_datetime(response["toDate"]))
				if response["toDate"]
				else None
			)
			doc._db_set(
				vacation_response_enabled=cint(response["isEnabled"]),
				vacation_from_date=from_date,
				vacation_to_date=to_date,
				vacation_response_subject=response["subject"],
				vacation_response_text_body=response["textBody"],
				vacation_response_html_body=response["htmlBody"],
				vacation_response_state=new_state,
				notify=True,
			)
	except Exception:
		frappe.log_error(
			title=_("Failed to sync JMAP vacation response"),
			message=frappe.get_traceback(with_context=True),
		)

		if raise_exception:
			frappe.throw(_("Failed to sync JMAP vacation response."))


def has_permission(doc: "Document", ptype: str, user: str | None = None) -> bool:
	if doc.doctype != "Mail Account":
		return False

	user = user or frappe.session.user

	if is_system_manager(user):
		return True

	if is_tenant_admin(doc.tenant, user):
		return True

	if has_role(user, "Mail User"):
		return user == doc.user

	return False


def get_permission_query_condition(user: str | None = None) -> str:
	user = user or frappe.session.user

	if is_system_manager(user):
		return ""

	if has_role(user, "Mail Admin"):
		if tenant := get_tenant_for_user(user):
			return f"(`tabMail Account`.`tenant` = {frappe.db.escape(tenant)})"

	if has_role(user, "Mail User"):
		return f"(`tabMail Account`.`user` = {frappe.db.escape(user)})"

	return "1=0"

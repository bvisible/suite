import frappe
from frappe import _


def get_root_domain_name() -> str | None:
	"""Returns the root domain name."""

	def generator() -> str | None:
		return frappe.db.get_single_value("Mail Settings", "root_domain_name")

	return frappe.cache.hget("mail-settings", "root_domain_name", generator)


def get_smtp_limits() -> dict:
	"""Returns the SMTP limits."""

	def generator() -> dict:
		mail_settings = frappe.get_doc("Mail Settings")
		return {
			"max_connections": mail_settings.smtp_max_connections,
			"max_messages": mail_settings.smtp_max_messages,
			"session_duration": mail_settings.smtp_session_duration,
			"inactivity_timeout": mail_settings.smtp_inactivity_timeout,
			"cleanup_interval": mail_settings.smtp_cleanup_interval,
		}

	return frappe.cache.hget("mail-settings", "smtp_limits", generator)


def get_imap_limits() -> dict:
	"""Returns the IMAP limits."""

	def generator() -> dict:
		mail_settings = frappe.get_doc("Mail Settings")
		return {
			"max_connections": mail_settings.imap_max_connections,
			"authenticated_timeout": mail_settings.imap_authenticated_timeout,
			"unauthenticated_timeout": mail_settings.imap_unauthenticated_timeout,
			"idle_timeout": mail_settings.imap_idle_timeout,
			"cleanup_interval": mail_settings.imap_cleanup_interval,
		}

	return frappe.cache.hget("mail-settings", "imap_limits", generator)


def get_personal_signup_domains() -> list:
	"""Returns the personal signup domains."""

	def generator() -> list:
		mail_settings = frappe.get_doc("Mail Settings")
		return [signup_domain.domain_name for signup_domain in mail_settings.personal_signup_domains]

	return frappe.cache.hget("mail-settings", "personal_signup_domains", generator)


def get_cluster_for_tenant(tenant: str) -> str | None:
	"""Returns the cluster for the tenant."""

	def generator() -> str | None:
		return frappe.db.get_value("Mail Tenant", tenant, "cluster")

	return frappe.cache.hget(f"tenant|{tenant}", "cluster", generator)


def get_domains_owned_by_tenant(tenant: str) -> list:
	"""Returns the domains owned by the tenant."""

	def generator() -> list:
		return frappe.db.get_all("Mail Domain", filters={"tenant": tenant}, pluck="name")

	return frappe.cache.hget(f"tenant|{tenant}", "domains", generator)


def get_groups_owned_by_tenant(tenant: str) -> list:
	"""Returns the groups owned by the tenant."""

	def generator() -> list:
		return frappe.db.get_all("Mail Group", filters={"tenant": tenant}, pluck="name")

	return frappe.cache.hget(f"tenant|{tenant}", "groups", generator)


def get_tenant_for_domain(domain_name: str) -> str | None:
	"""Returns the tenant for the domain."""

	def generator() -> str | None:
		return frappe.db.get_value("Mail Domain", domain_name, "tenant")

	return frappe.cache.hget(f"domain|{domain_name}", "tenant", generator)


def get_tenant_for_group(group: str) -> str | None:
	"""Returns the tenant for the group."""

	def generator() -> str | None:
		return frappe.db.get_value("Mail Group", group, "tenant")

	return frappe.cache.hget(f"group|{group}", "tenant", generator)


def get_tenant_for_user(user: str) -> str | None:
	"""Returns the tenant of the user."""

	def generator() -> str | None:
		return frappe.db.get_value("Mail Tenant Member", {"user": user}, "tenant")

	return frappe.cache.hget(f"user|{user}", "tenant", generator)


def get_account_for_user(user: str) -> str | None:
	"""Returns the account of the user."""

	def generator() -> str | None:
		return frappe.db.get_value("Mail Account", {"user": user, "enabled": 1}, "name")

	return frappe.cache.hget(f"user|{user}", "account", generator)


def get_account_for_email(email: str) -> str | None:
	"""Returns the account for the email."""

	def generator() -> str | None:
		if account := frappe.db.exists("Mail Account", {"email": email}):
			return account
		elif alias := frappe.db.exists("Mail Alias", {"email": email, "alias_for_type": "Mail Account"}):
			return frappe.db.get_value("Mail Alias", alias, "alias_for_name")

	return frappe.cache.hget(f"email|{email}", "account", generator)


def get_aliases_for_user(user: str) -> list:
	"""Returns the aliases of the user."""

	def generator() -> list:
		account = get_account_for_user(user)

		if not account:
			return []

		MAIL_ALIAS = frappe.qb.DocType("Mail Alias")
		return (
			frappe.qb.from_(MAIL_ALIAS)
			.select("name")
			.where(
				(MAIL_ALIAS.enabled == 1)
				& (MAIL_ALIAS.alias_for_type == "Mail Account")
				& (MAIL_ALIAS.alias_for_name == account)
			)
		).run(pluck="name")

	return frappe.cache.hget(f"user|{user}", "aliases", generator)


def get_default_outgoing_email_for_user(user: str) -> str | None:
	"""Returns the default outgoing email of the user."""

	def generator() -> str | None:
		return frappe.db.get_value("Mail Account", {"user": user, "enabled": 1}, "default_outgoing_email")

	return frappe.cache.hget(f"user|{user}", "default_outgoing_email", generator)


def get_rate_limits(method_path: str) -> list:
	"""Returns the rate limits for the method path."""

	def generator() -> list:
		RATE_LIMIT = frappe.qb.DocType("Rate Limit")
		rate_limits = (
			frappe.qb.from_(RATE_LIMIT)
			.select(
				RATE_LIMIT.ignore_in_developer_mode,
				RATE_LIMIT.key_.as_("key"),
				RATE_LIMIT.limit,
				RATE_LIMIT.seconds,
				RATE_LIMIT.methods,
				RATE_LIMIT.ip_based,
				RATE_LIMIT.allowed_ips,
				RATE_LIMIT.blocked_ips,
			)
			.where((RATE_LIMIT.enabled == 1) & (RATE_LIMIT.method_path == method_path))
		).run(as_dict=True)

		if not rate_limits:
			return []

		for rl in rate_limits:
			rl["ignore_in_developer_mode"] = bool(rl["ignore_in_developer_mode"])
			rl["methods"] = rl["methods"].split("\n")
			rl["ip_based"] = bool(rl["ip_based"])

			if len(rl["methods"]) == 1 and rl["methods"][0] == "ALL":
				rl["methods"] = "ALL"

			rl["allowed_ips"] = rl["allowed_ips"].split("\n") if rl["allowed_ips"] else []
			rl["blocked_ips"] = rl["blocked_ips"].split("\n") if rl["blocked_ips"] else []

		return rate_limits

	return frappe.cache.hget("rate_limits", method_path, generator)

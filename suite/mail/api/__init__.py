import frappe
from frappe.apps import get_apps as get_permitted_apps
from frappe.translate import get_all_translations
from frappe.utils.caching import redis_cache

from mail.utils.cache import get_personal_signup_domains


@frappe.whitelist(allow_guest=True)
def get_signup_settings() -> dict:
	"""Returns client signup settings."""

	return frappe.db.get_value(
		"Mail Settings", None, ["allow_self_signup", "allow_personal_signup"], as_dict=True
	)


@frappe.whitelist(allow_guest=True)
def get_signup_domains() -> dict:
	"""Returns personal signup domains."""

	return get_personal_signup_domains()


@frappe.whitelist(allow_guest=True)
def get_branding() -> dict:
	"""Returns branding information."""

	return frappe.db.get_value("Website Settings", None, ["app_name", "brand_html", "favicon"], as_dict=True)


@frappe.whitelist(allow_guest=True)
def get_translations() -> dict:
	"""Returns translations for the current user's language."""

	if frappe.session.user != "Guest":
		language = frappe.db.get_value("User", frappe.session.user, "language")
	else:
		language = frappe.db.get_single_value("System Settings", "language")

	return get_all_translations(language)


@frappe.whitelist()
@redis_cache()
def get_apps():
	apps = get_permitted_apps()
	app_list = [
		{
			"name": "frappe",
			"logo": "/assets/mail/images/desk.png",
			"title": "Desk",
			"route": "/app",
		}
	]
	app_list += [app for app in apps if app.get("name") != "mail"]

	return app_list

import frappe


def get_context():
	context = {"boot": {"csrf_token": frappe.sessions.get_csrf_token(), "site_name": frappe.local.site}}
	return context

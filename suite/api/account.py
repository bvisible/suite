import frappe


@frappe.whitelist()
def is_setup_complete() -> bool:
	return bool(frappe.is_setup_complete())


@frappe.whitelist()
def mark_setup_complete() -> None:
	frappe.only_for("System Manager")

	from frappe.desk.page.setup_wizard.setup_wizard import enable_setup_wizard_complete

	enable_setup_wizard_complete("frappe")
	enable_setup_wizard_complete("suite")
	frappe.db.set_single_value("System Settings", "setup_complete", 1)


@frappe.whitelist()
def get_logged_in_user() -> dict | None:
	user = frappe.session.user
	if user == "Guest":
		return None

	user_doc = frappe.get_doc("User", user)
	return {
		"name": user_doc.name,
		"email": user_doc.email,
		"full_name": user_doc.full_name,
		"avatar": user_doc.user_image,
		"roles": [role.role for role in user_doc.roles],
	}

import frappe


def check_app_permission():
	if frappe.session.user == "Administrator":
		return True

	return is_slides_user()


@frappe.whitelist()
def is_slides_user():
	user = frappe.session.user
	if user == "Guest":
		return False

	return "Slides User" in frappe.get_roles(user)

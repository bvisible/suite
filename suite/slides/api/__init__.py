import frappe


def check_app_permission():
	if frappe.session.user == "Administrator":
		return True

	return frappe.has_permission("Presentation", ptype="write")


@frappe.whitelist()
def is_slides_user():
	user = frappe.session.user
	if user == "Guest":
		return False

	return "Slides User" in frappe.get_roles(user)

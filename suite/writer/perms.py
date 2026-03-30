import frappe
from drive.api.permissions import user_has_permission


def has_permission(doc, ptype, user=None):
    if ptype == "create":
        return True
    file = frappe.get_value("Drive File", {"doc": doc.name}, "name")
    if not file:
        return False
    return user_has_permission(file, ptype, user)

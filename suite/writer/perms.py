import frappe
from suite.drive.api.permissions import user_has_permission


def has_permission(doc, ptype, user=None):
    if ptype == "create":
        return True
    file = frappe.get_value(
        "File", {"content_docname": doc.name, "content_doctype": "Writer Document"}, "name"
    )
    if not file:
        return False
    return user_has_permission(file, ptype, user)

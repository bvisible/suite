from drive.api.permissions import user_has_permission


def has_permission(doc, ptype, user=None):
    entity = frappe.get_value("Drive File", {"document": doc.name}, "name")
    if ptype == "create" or not entity:
        return True
    return user_has_permission(entity, ptype, user)

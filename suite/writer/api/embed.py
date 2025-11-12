import frappe
from drive.api.files import upload_file, get_file_internal
from drive.api.permissions import user_has_permission


@frappe.whitelist()
def add(file_id):
    file_doc = frappe.get_doc("Drive File", file_id)
    file = frappe.request.files["file"]
    file.filename = f"{file_doc.name} embed -{file.filename}"
    embed = upload_file(file_doc.team, parent=file_doc.name, embed=1)
    return {"file_url": f"/api/method/writer.api.embed.get?id={embed.name}"}


@frappe.whitelist(allow_guest=True)
def get(id):
    embed = frappe.get_cached_doc("Drive File", id)
    parent = frappe.db.get_value(
        "Drive File", embed.parent_entity, ["name", "doc"], as_dict=True
    )
    if not parent.doc:
        frappe.throw("This is not an embed", ValueError)
    if not user_has_permission(parent.name, "read"):
        frappe.throw(
            "You do not have permission to view this file", frappe.PermissionError
        )
    return get_file_internal(embed)

from drive.api.permissions import user_has_permission
import frappe
from drive.utils.files import get_s3_url


@frappe.whitelist(allow_guest=True)
def fetch(path: str):
    file = frappe.get_doc("File", {"file_url": get_s3_url(path)})
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = "/api/method/drive.api.files.get_file_content?entity_name=" + file.name
    return

#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe
from frappe import _

from suite.drive.api.files import get_file_content, get_s3_url


@frappe.whitelist(allow_guest=True)
def fetch(path: str):
    name = frappe.db.get_value("File", {"file_url": get_s3_url(path)})
    if not name:
        frappe.throw(_("Not found"), frappe.DoesNotExistError)
    try:
        return get_file_content(name)
    except (frappe.PermissionError, frappe.DoesNotExistError):
        frappe.throw(_("Not found"), frappe.DoesNotExistError)

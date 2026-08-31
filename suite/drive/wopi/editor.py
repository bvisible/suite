# //// Neoffice: new file — Collabora/WOPI port (from drive_wopi), maintained by Neoffice ////
"""API endpoints for the Collabora editor integration (native File backend)."""

from __future__ import annotations

import os
import shutil

import frappe
from frappe import _

from suite.drive.utils import create_drive_file, get_file_type, get_user_folder
from suite.drive.utils.files import FileManager, get_s3_key, get_s3_url

from .discovery import check_collabora_status, is_file_supported

OFFICE_MIME_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


@frappe.whitelist()
def can_edit_file(file_id: str) -> dict:
    """Check if a file can be edited with Collabora."""
    if not frappe.db.exists("File", file_id):
        return {"can_edit": False, "reason": _("File not found")}

    file_name = frappe.db.get_value("File", file_id, "file_name") or ""

    if not is_file_supported(file_name):
        return {"can_edit": False, "reason": _("File type not supported")}

    status = check_collabora_status()
    if status.get("status") != "ok":
        return {
            "can_edit": False,
            "reason": status.get("message", _("Collabora server not available")),
        }

    return {"can_edit": True, "reason": None}


@frappe.whitelist()
def get_supported_extensions() -> list:
    """Get the list of file extensions supported by Collabora."""
    status = check_collabora_status()
    return status.get("supported_formats", [])


@frappe.whitelist()
def create_office_file(file_type: str, title: str, parent: str = None) -> dict:
    """Create a new blank Office file in the Drive.

    Args:
        file_type: 'docx', 'xlsx' or 'pptx'
        title: file name (extension optional)
        parent: parent folder File id (defaults to the caller's private folder)

    Note: simple annotations on purpose — v15's whitelist arg coercion
    breaks on union types (`str | None`) for HTTP-sent values.
    """
    file_type = (file_type or "").lower()
    mime_type = OFFICE_MIME_TYPES.get(file_type)
    if not mime_type:
        frappe.throw(_("Unsupported file type. Use 'docx', 'xlsx', or 'pptx'."))

    extension = f".{file_type}"
    if not title.endswith(extension):
        title = f"{title}{extension}"

    template_path = os.path.join(frappe.get_app_path("suite"), "templates", "files", f"blank.{file_type}")
    if not os.path.exists(template_path):
        frappe.throw(_("Template file not found"))

    # Resolve the parent folder, same defaults as the Drive upload flow:
    # an explicit folder, else the caller's private folder.
    #//// Neoffice — rewritten for the de-teamed Drive (upstream 4df6ee65a /
    #//// f3cf5206c, merged 31.08.2026). Drive Team and Drive Team Member are gone,
    #//// get_home_folder(team)/get_default_team() with them, and storage is now
    #//// one folder per user under a single site root. create_drive_file also lost
    #//// its leading `team` argument — calling it positionally as before would not
    #//// have raised, it would have silently shifted every argument by one and
    #//// created files named after a team id.
    if parent:
        if not frappe.db.exists("File", parent):
            frappe.throw(_("Parent folder not found"))
    else:
        parent = get_user_folder()["name"]

    file_size = os.path.getsize(template_path)
    manager = FileManager()

    drive_file = create_drive_file(
        title,
        parent,
        get_file_type(mime_type),
        lambda file: "/" + str(manager.get_disk_path(file)),
        mime_type,
        file_size,
    )

    # Write the blank template into place. Not manager.upload_file: that
    # os.rename()s and assumes the destination directory already exists,
    # which is not guaranteed for a team home nobody has uploaded into yet.
    from suite.drive.utils.files import storage_key

    key = storage_key(drive_file.file_url)
    if manager.s3_enabled:
        manager.conn.upload_file(template_path, manager.bucket, get_s3_key(drive_file.file_url))
    else:
        dest = manager.site_folder / key
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(template_path, dest)

    if manager.s3_enabled:
        drive_file.file_url = get_s3_url(get_s3_key(drive_file.file_url))
        drive_file.save(ignore_permissions=True)

    frappe.db.commit()

    return {
        "file_id": drive_file.name,
        "file_name": title,
    }

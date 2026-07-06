"""API endpoints for the Collabora editor integration (native File backend)."""

from __future__ import annotations

import os
import shutil
import tempfile

import frappe
from frappe import _

from suite.drive.utils import create_drive_file, get_default_team, get_file_type, get_home_folder
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
def create_office_file(file_type: str, title: str, parent: str | None = None) -> dict:
    """Create a new blank Office file in the Drive.

    Args:
        file_type: 'docx', 'xlsx' or 'pptx'
        title: file name (extension optional)
        parent: parent folder File id (defaults to the user's home folder)
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

    # Resolve team + parent folder (same defaults as the Drive upload flow)
    if parent:
        if not frappe.db.exists("File", parent):
            frappe.throw(_("Parent folder not found"))
        team = frappe.db.get_value("File", parent, "team")
        home_folder = get_home_folder(team)
    else:
        team = get_default_team()
        if not team:
            frappe.throw(_("No team found. Please set up your Drive first."))
        home_folder = get_home_folder(team)
        parent = home_folder["name"]

    file_size = os.path.getsize(template_path)
    manager = FileManager()

    drive_file = create_drive_file(
        team,
        title,
        parent,
        get_file_type(mime_type),
        lambda file: "/" + str(manager.get_disk_path(file, home_folder)),
        mime_type,
        file_size,
    )

    # upload_file MOVES the source into place (os.rename) — hand it a
    # disposable copy created on the SAME filesystem as the site folder,
    # otherwise the rename fails with EXDEV when /tmp is a separate mount.
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=extension, dir=manager.site_folder)
    tmp.close()
    shutil.copyfile(template_path, tmp.name)
    manager.upload_file(tmp.name, drive_file, create_thumbnail=False)

    if manager.s3_enabled:
        drive_file.file_url = get_s3_url(get_s3_key(drive_file.file_url))
        drive_file.save(ignore_permissions=True)

    frappe.db.commit()

    return {
        "file_id": drive_file.name,
        "file_name": title,
    }

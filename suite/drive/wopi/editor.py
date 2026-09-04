# //// Neoffice: new file — Collabora/WOPI port (from drive_wopi), maintained by Neoffice ////
"""API endpoints for the Collabora editor integration (native File backend)."""

from __future__ import annotations

import os
import shutil

import frappe
from frappe import _

#//// Neoffice — rate limiting for can_edit_file, which may start coolwsd.
from frappe.rate_limiter import rate_limit

from suite.drive.utils import create_drive_file, get_file_type, get_user_folder
from suite.drive.utils.files import FileManager, get_s3_key, get_s3_url

#//// Neoffice — collabora_status replaces the whitelisted check_collabora_status:
#//// the endpoint is read-only now, this callable is what may wake the daemon.
from .discovery import EDITOR_RATE, collabora_status, is_file_supported

OFFICE_MIME_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


#//// Neoffice — rate limited, and it now requires read access on the document.
#//// This is the editor pre-flight the Drive preview calls, so it is one of the two
#//// endpoints allowed to wake coolwsd (see discovery.get_discovery_xml); without a
#//// limit it was a free "hold a web worker for 20 s" primitive. The read check
#//// closes the smaller half of the same hole: the reply used to tell any signed-in
#//// user whether an arbitrary File id existed and whether it was an Office document.
#//// An unreadable id answers exactly like a missing one, so the difference leaks
#//// nothing either.
@frappe.whitelist()
@rate_limit(key=EDITOR_RATE["key"], limit=EDITOR_RATE["limit"], seconds=EDITOR_RATE["seconds"])
def can_edit_file(file_id: str) -> dict:
    """Check if a file can be edited with Collabora."""
    #//// Neoffice — read access required; see the block above the decorators.
    from suite.drive.api.permissions import user_has_permission

    if not frappe.db.exists("File", file_id) or not user_has_permission(file_id, "read"):
        return {"can_edit": False, "reason": _("File not found")}

    file_name = frappe.db.get_value("File", file_id, "file_name") or ""

    #//// Neoffice — `start_if_down=True`: the user has opened an Office document and
    #//// is waiting on the answer, so this is the moment to wake the daemon.
    if not is_file_supported(file_name, start_if_down=True):
        return {"can_edit": False, "reason": _("File type not supported")}

    #//// Neoffice — the editor pre-flight is allowed to wake coolwsd.
    status = collabora_status(start_if_down=True)
    if status.get("status") != "ok":
        #//// Neoffice — tell the caller WHETHER COLLABORA IS SUPPOSED TO BE THERE.
        #////
        #//// The frontend falls back to Microsoft's Office viewer when it cannot
        #//// edit, which ships the document to view.officeapps.live.com. That is
        #//// acceptable when this instance has no Collabora at all; it is NOT when
        #//// Collabora is deployed and merely waking up: coolwsd is stopped after
        #//// 15 idle minutes (lifecycle.stop_if_idle), and a cold start under swap
        #//// pressure can outrun COLLABORA_START_TIMEOUT_SECONDS. Measured on osiris
        #//// 31.08.2026: the first click after two idle weeks offered to send the
        #//// document to Microsoft. On a client instance that would happen several
        #//// times a day, on their documents. Same intent as 850e41c0c.
        #////
        #//// `wopi_enabled` lets the caller keep waiting instead of leaving the
        #//// site; `retryable` says the daemon is on its way up.
        return {
            "can_edit": False,
            "reason": status.get("message", _("Collabora server not available")),
            "wopi_enabled": status.get("status") != "disabled",
            "retryable": status.get("status") != "disabled",
        }

    return {"can_edit": True, "reason": None, "wopi_enabled": True, "retryable": False}


@frappe.whitelist()
def get_supported_extensions() -> list:
    """Get the list of file extensions supported by Collabora."""
    #//// Neoffice — read-only: listing the formats is not a reason to boot a daemon.
    status = collabora_status(start_if_down=False)
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
        #//// Neoffice — `parent` comes from the caller and was checked for EXISTENCE
        #//// only, while create_drive_file below inserts with ignore_permissions=True:
        #//// any signed-in user could drop a file into anybody else's folder just by
        #//// passing its id. Same guard as every other "create in this folder" entry
        #//// point — sheets.api.create_sheet, slides create_presentation,
        #//// writer.api.docs.create_document. The is_folder check is ours too: a
        #//// File id that is not a folder would have been accepted as a parent and
        #//// produced an entry nothing can list.
        from suite.drive.api.permissions import user_has_permission

        parent_doc = frappe.db.get_value("File", parent, ["name", "is_folder"], as_dict=True)
        if not parent_doc:
            frappe.throw(_("Parent folder not found"), frappe.DoesNotExistError)
        if not parent_doc.is_folder:
            frappe.throw(_("The parent must be a folder"), frappe.ValidationError)
        if not user_has_permission(parent, "upload"):
            frappe.throw(
                _("Cannot access folder due to insufficient permissions"),
                frappe.PermissionError,
            )
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

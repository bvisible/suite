# //// Neoffice: new file — Collabora/WOPI port (from drive_wopi), maintained by Neoffice ////
"""WOPI REST endpoints for Collabora Online, backed by the native File doctype.

Ported from the Neoffice `drive_wopi` app (which targeted the standalone
drive app's "Drive File" doctype). Storage goes through suite's FileManager
so both local disk and S3 backends work.

Documentation: https://learn.microsoft.com/en-us/microsoft-365/cloud-storage-partner-program/rest/
"""

from __future__ import annotations

import os

import frappe
from frappe import _

from suite.drive.utils.files import FileManager, storage_key

from .lock_manager import acquire_lock, get_lock, refresh_lock, release_lock, unlock_expired
from .token import validate_wopi_token

CONTENT_TYPES = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".odp": "application/vnd.oasis.opendocument.presentation",
    ".doc": "application/msword",
    ".xls": "application/vnd.ms-excel",
    ".ppt": "application/vnd.ms-powerpoint",
}


def set_response_header(key: str, value: str):
    """Set a response header, initializing headers dict if needed."""
    if frappe.response.headers is None:
        frappe.response.headers = {}
    frappe.response.headers[key] = value


def get_wopi_file(file_id: str):
    """Get the native File document behind a WOPI file id."""
    if not frappe.db.exists("File", file_id):
        frappe.throw(_("File not found"), frappe.DoesNotExistError)

    file = frappe.get_doc("File", file_id)
    if file.is_folder:
        frappe.throw(_("Cannot open a folder in the editor"), frappe.ValidationError)
    return file


# //// Neoffice — added: the token is not the permission.
# ////
# //// generate_wopi_token() freezes `file_id` and `can_write` at the instant the
# //// editor opened and signs them for jwt_expiry_hours. Nothing here re-read the
# //// Drive permissions afterwards, so unsharing a document — or revoking a
# //// collaborator's write access, or moving the file — changed nothing for anyone
# //// who already had the editor open, or who kept the token: they went on reading
# //// and SAVING for the whole life of the token. Revocation has to be immediate to
# //// mean anything, so every read and every write re-checks the live permission of
# //// the user the token names. The token remains what authenticates the caller
# //// (Collabora holds no session); it is no longer what authorises the operation.
def check_token_permission(file, token_data: dict, ptype: str) -> bool:
    """True if the token's user still holds `ptype` on `file` right now."""
    from suite.drive.api.permissions import user_has_permission

    # WOPI requests carry no session: `frappe.session.user` is Guest here, so the
    # user must be taken from the token and passed explicitly.
    user = token_data.get("user_id") or "Guest"
    return bool(user_has_permission(file, ptype, user=user))


def require_token_permission(file, token_data: dict, ptype: str) -> None:
    """Refuse the WOPI operation if the token's user lost `ptype` on `file`."""
    if not check_token_permission(file, token_data, ptype):
        frappe.throw(_("You don't have permission to access this file"), frappe.PermissionError)


def read_file_content(file) -> bytes:
    """Read the file bytes through FileManager (handles local disk and S3)."""
    buf = FileManager().get_file(file)
    return buf.read()


def write_file_content(file, content: bytes) -> None:
    """Write the file bytes back to storage (local disk or S3)."""
    manager = FileManager()
    key = storage_key(file.file_url)
    if manager.s3_enabled:
        # //// Neoffice — one bucket for the site since the de-teaming (4df6ee65a):
        # //// FileManager.get_bucket(team) is gone, the bucket is now an attribute.
        manager.conn.put_object(Bucket=manager.bucket, Key=key, Body=content)
    else:
        path = manager.site_folder / key
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)


def validate_access_token(file_id: str) -> dict:
    """Validate access token from request and return token data."""
    # Token comes via X-WOPI-Access-Token header or query param
    access_token = frappe.request.headers.get("X-WOPI-Access-Token")
    if not access_token:
        access_token = frappe.request.args.get("access_token")
    if not access_token:
        frappe.throw(_("Access token missing"), frappe.AuthenticationError)

    token_data = validate_wopi_token(access_token)

    if token_data.get("file_id") != file_id:
        frappe.throw(_("Invalid token for this file"), frappe.AuthenticationError)

    return token_data


@frappe.whitelist(allow_guest=True)
def check_file_info(file_id: str):
    """WOPI CheckFileInfo endpoint — GET /wopi/files/{file_id}."""
    token_data = validate_access_token(file_id)

    file = get_wopi_file(file_id)

    # //// Neoffice — see check_token_permission above. Collabora asks this first and
    # //// builds its whole UI from the answer, so re-deciding `UserCanWrite` here is
    # //// what turns a revoked share into a read-only editor rather than into a save
    # //// that fails minutes later on a document the user believed was theirs.
    require_token_permission(file, token_data, "read")

    user_id = token_data.get("user_id", "anonymous")
    # //// Neoffice — the token's `can_write` AND the live permission, not either one.
    can_write = bool(token_data.get("can_write", False)) and check_token_permission(file, token_data, "write")

    user_name = user_id
    if user_id and user_id != "Guest" and frappe.db.exists("User", user_id):
        user_name = frappe.db.get_value("User", user_id, "full_name") or user_id

    file_size = file.file_size
    if not file_size:
        file_size = len(read_file_content(file))

    response = {
        # Identifiers
        "BaseFileName": file.file_name or file.name,
        "OwnerId": file.owner,
        "Size": file_size,
        "Version": str(file.modified),
        # Current user
        "UserId": user_id,
        "UserFriendlyName": user_name,
        "UserCanWrite": can_write,
        "UserCanNotWriteRelative": True,
        # Capabilities
        "SupportsLocks": True,
        "SupportsUpdate": True,
        "SupportsGetLock": True,
        "SupportsExtendedLockLength": True,
        # UI options
        "DisablePrint": False,
        "DisableExport": False,
        "DisableCopy": False,
        "HideSaveOption": False,
        "HideExportOption": False,
        "HidePrintOption": False,
    }

    frappe.response.update(response)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_file(file_id: str):
    """WOPI GetFile endpoint — GET /wopi/files/{file_id}/contents."""
    # //// Neoffice — the token data is kept: the read is re-authorised below.
    token_data = validate_access_token(file_id)

    file = get_wopi_file(file_id)
    # //// Neoffice — see check_token_permission above: a token outlives the share it
    # //// was minted under, so the read is re-authorised against the live permission.
    require_token_permission(file, token_data, "read")

    content = read_file_content(file)

    file_name = file.file_name or ""
    extension = os.path.splitext(file_name)[1].lower()

    frappe.response.filename = file_name
    frappe.response.filecontent = content
    frappe.response.type = "binary"
    set_response_header("Content-Type", CONTENT_TYPES.get(extension, "application/octet-stream"))
    set_response_header("X-WOPI-ItemVersion", str(file.modified))


@frappe.whitelist(allow_guest=True, methods=["POST"])
def put_file(file_id: str):
    """WOPI PutFile endpoint — POST /wopi/files/{file_id}/contents."""
    token_data = validate_access_token(file_id)

    if not token_data.get("can_write"):
        frappe.throw(_("Write permission denied"), frappe.PermissionError)

    file = get_wopi_file(file_id)

    # //// Neoffice — see check_token_permission above. `can_write` in the token says
    # //// what was true when the editor opened, up to jwt_expiry_hours ago; this says
    # //// what is true now, and it is the one that decides whether bytes land.
    require_token_permission(file, token_data, "write")

    # Verify lock
    wopi_lock = frappe.request.headers.get("X-WOPI-Lock", "")
    current_lock = get_lock(file_id)

    if current_lock and current_lock.get("lock_id") != wopi_lock:
        frappe.local.response.http_status_code = 409
        set_response_header("X-WOPI-Lock", current_lock.get("lock_id", ""))
        return {"error": "Lock mismatch"}

    content = frappe.request.get_data()

    # Keep the previous bytes so a failed write can be rolled back
    try:
        previous = read_file_content(file)
    except Exception:
        previous = None

    try:
        write_file_content(file, content)
        file.db_set(
            {"file_size": len(content), "file_modified": frappe.utils.now()},
            update_modified=True,
        )
        frappe.db.commit()
        set_response_header("X-WOPI-ItemVersion", str(file.modified))
    except Exception as e:
        if previous is not None:
            try:
                write_file_content(file, previous)
            except Exception:
                pass
        frappe.log_error("WOPI PutFile Error", str(e))
        raise

    return {}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def handle_lock(file_id: str):
    """Handle WOPI lock operations — POST /wopi/files/{file_id}.

    Headers: X-WOPI-Override: LOCK | UNLOCK | REFRESH_LOCK | GET_LOCK | UNLOCK_AND_RELOCK
    """
    token_data = validate_access_token(file_id)

    operation = frappe.request.headers.get("X-WOPI-Override", "").upper()
    lock_id = frappe.request.headers.get("X-WOPI-Lock", "")
    old_lock_id = frappe.request.headers.get("X-WOPI-OldLock", "")
    user = token_data.get("user_id", "anonymous")

    result = {"success": True, "status": 200}

    if operation == "LOCK":
        result = acquire_lock(file_id, lock_id, user)
    elif operation == "UNLOCK":
        result = release_lock(file_id, lock_id)
    elif operation == "REFRESH_LOCK":
        result = refresh_lock(file_id, lock_id)
    elif operation == "GET_LOCK":
        current = get_lock(file_id)
        set_response_header("X-WOPI-Lock", current.get("lock_id", "") if current else "")
        return {"status": 200}
    elif operation == "UNLOCK_AND_RELOCK":
        result = unlock_expired(file_id, old_lock_id, lock_id, user)
    else:
        frappe.throw(_("Unsupported WOPI operation: {0}").format(operation), frappe.ValidationError)

    if not result.get("success"):
        frappe.local.response.http_status_code = result.get("status", 409)
        if result.get("current_lock"):
            set_response_header("X-WOPI-Lock", result["current_lock"])

    return result


# =============================================================================
# Nginx-routable wrapper endpoints — the nginx wopi.conf snippet rewrites
# /wopi/files/{id}[/contents] onto these two methods.
# =============================================================================


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def handle_file_info(file_id: str):
    """Handle /wopi/files/{file_id} — GET = CheckFileInfo, POST = lock ops."""
    if frappe.request.method == "GET":
        return check_file_info(file_id)
    elif frappe.request.method == "POST":
        return handle_lock(file_id)


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def handle_contents(file_id: str):
    """Handle /wopi/files/{file_id}/contents — GET = GetFile, POST = PutFile."""
    if frappe.request.method == "GET":
        return get_file(file_id)
    elif frappe.request.method == "POST":
        return put_file(file_id)

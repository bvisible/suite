# //// Neoffice — added file (no upstream equivalent): the content endpoints of the Drive's Office editors ////
"""WOPI-style content endpoints of the Craft editors, backed by the native File doctype.

Ported from the Neoffice `drive_wopi` app, which served Collabora Online. Collabora is gone (maintenance#1570)
and what is left is what the Craft editors call: read the document, write it back, each with the signed token
that ``craft.get_craft_editor_config`` hands out and a live permission check. Storage goes through suite's
FileManager so both local disk and S3 backends work.
"""

from __future__ import annotations

import os

import frappe
from frappe import _

from suite.drive.utils.files import FileManager, storage_key

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
# //// (the request carries no session); it is no longer what authorises the operation.
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


# //// Neoffice — what the content of a file is at this moment, for the editors' optimistic concurrency (craft.py).
# //// `modified` moves for any change of the row, a rename or a share included: a document somebody else only
# //// renamed would read as "changed since you opened it". The content's own time and size move only when the
# //// bytes do (PutFile, an upload, a WebDAV PUT).
def content_version(file) -> str:
    return f"{file.file_modified}|{file.file_size}"


# //// Neoffice — an HTTP header the page can read. `set_response_header` above writes `frappe.response.headers`,
# //// a key of the response dict that nothing turns into a header; the real ones are `frappe.local.response_headers`
# //// (v16 natively, v15 through suite_core/v15_response_headers.py). Measured on osiris, 14.10.2026: the page read
# //// `null` for the header set the first way.
def send_content_version(file) -> None:
    headers = getattr(frappe.local, "response_headers", None)
    if headers is not None:
        headers["X-Neoffice-Content-Version"] = content_version(file)


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
    # //// Neoffice — the version the editor says it opened when it saves (see put_file).
    send_content_version(file)


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

    # //// Neoffice — optimistic concurrency (craft.py). The editor saving from the Drive page holds no lock, so two
    # //// people editing the same document would overwrite each other without a word. It says which content it
    # //// opened in X-Neoffice-Base-Version: when the file has changed since, nothing is written (409) and the page
    # //// offers a copy. A save that names no version (the person chose to replace) writes without the check.
    # //// The lock calls of the WOPI protocol (LOCK, UNLOCK…) went with Collabora, the only client that used them.
    base_version = frappe.request.headers.get("X-Neoffice-Base-Version")
    if base_version and base_version != content_version(file):
        frappe.local.response.http_status_code = 409
        send_content_version(file)
        return {"error": "The file changed since it was opened"}

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
        # //// Neoffice — the version the next save of the same editor builds on.
        send_content_version(file)
    except Exception as e:
        if previous is not None:
            try:
                write_file_content(file, previous)
            except Exception:
                pass
        frappe.log_error("WOPI PutFile Error", str(e))
        raise

    return {}


# =============================================================================
# Nginx-routable wrapper endpoint — the nginx wopi.conf snippet rewrites
# /wopi/files/{id}/contents onto this method.
# =============================================================================


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def handle_contents(file_id: str):
    """Handle /wopi/files/{file_id}/contents — GET = GetFile, POST = PutFile."""
    if frappe.request.method == "GET":
        return get_file(file_id)
    elif frappe.request.method == "POST":
        return put_file(file_id)

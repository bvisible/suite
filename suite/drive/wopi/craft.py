# //// Neoffice — added file (no upstream equivalent): the Craft editors, the Drive's Office editors.
"""Open an Office document in a Craft editor (NeoWrite, NeoSheet, NeoSlides, NeoPDF): the Drive's Office editors.

The browser builds of the editors (Neoffice's forks of storytold's Craft apps, built in their own
repositories) are static files under ``suite/public/craft/<folder>/``, put there by
``craft_install`` from the list pinned in ``craft_editors.json``. The Drive page frames an editor in
an iframe of its own origin and hands it the file (``postMessage``, ``?host=parent``). What the
editor saves goes back through the WOPI endpoints of this package (``endpoints.py``), with the token
minted here, and the live permission check is made on every read and every write.

Nothing here needs a server beside this site: Collabora Online, which the Drive used before these
editors, is gone (maintenance#1570).
"""

from __future__ import annotations

import os
import re

import frappe
from frappe import _

# //// Neoffice — one call per document open.
from frappe.rate_limiter import rate_limit

from suite.drive.utils import create_drive_file, get_file_type, get_new_file_name
from suite.drive.utils.files import FileManager, get_s3_key, get_s3_url, storage_key

from .token import generate_wopi_token

# //// Neoffice — the budget of the editor pre-flight, kept from the endpoint that used to share it with Collabora's.
# ////
# //// Keyed on `file_id`, so the identity frappe.rate_limiter counts is "<ip>:<document>" and not the bare IP: a
# //// whole office sits behind one public address, and a per-IP budget would be spent by whoever opened a
# //// document first. Per document it stays generous for people (opening the same file 20 times a minute is not
# //// something anybody does) while a loop hammering one document, which mints a token per call, runs out at once.
EDITOR_RATE = {"key": "file_id", "limit": 20, "seconds": 60}

# Editor -> the folder of its build under suite/public/craft/, and the extensions it opens AND writes
# back in the same format. A format an editor can only read would come back under another name: that
# is a copy, not an edit in place.
EDITORS = {
    "word": {"folder": "wordcraft", "extensions": ("docx",)},
    "sheet": {"folder": "gridcraft", "extensions": ("xlsx",)},
    "deck": {"folder": "deckcraft", "extensions": ("pptx",)},
    "pdf": {"folder": "pdfcraft", "extensions": ("pdf",)},
}

# What the Drive opens in an editor on its own: every type an editor writes back, the PDF editor included (a PDF
# opens in it directly, as a document opens in its own editor; the preview upstream has is the fallback of a site without
# the build, see PdfWithEditor.vue).
DEFAULT_EDITORS = ("word", "sheet", "deck", "pdf")

# Where Frappe serves the public folder of this app from.
ASSETS_URL = "/assets/suite/craft/"

# Largest copy Save As stores (the editors themselves cap what they open and write).
MAX_COPY_BYTES = 256 * 1024 * 1024

MIME_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "pdf": "application/pdf",
}


def build_dir(editor: str) -> str:
    """Where the browser build of ``editor`` is (or would be) installed."""
    return frappe.get_app_path("suite", "public", "craft", EDITORS[editor]["folder"])


def installed_version(editor: str) -> str | None:
    """The version of the installed build of ``editor``, or None when there is none."""
    folder = build_dir(editor)
    if not os.path.isfile(os.path.join(folder, "index.html")):
        return None
    try:
        with open(os.path.join(folder, "VERSION"), encoding="utf-8") as handle:
            return handle.read().strip() or "unknown"
    except OSError:
        return "unknown"


def extension_of(file_name: str) -> str:
    return file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""


def editor_for(file_name: str, requested: str | None = None) -> str | None:
    """The editor that opens ``file_name``: the one asked for if it handles the type, else the default one."""
    extension = extension_of(file_name)
    for editor in (requested,) if requested else DEFAULT_EDITORS:
        if editor in EDITORS and extension in EDITORS[editor]["extensions"]:
            return editor
    return None


def nora_for_the_person() -> bool:
    """Whether the editor gets Nora's pane: the site has Nora, and the person is staff (a System User).

    The line is the one Nora's own endpoints draw: a portal account (Website User) is refused by every
    nora method (nora/utils/portal_guard.py), her tools act for staff only, and a visitor has no session
    to call her with. The page offers the pane on this answer alone, so a person whose every message
    would be refused never sees it.
    """
    user = frappe.session.user
    if not user or user == "Guest" or "nora" not in frappe.get_installed_apps():
        return False
    return frappe.db.get_value("User", user, "user_type") == "System User"


@frappe.whitelist()
def get_installed_editors() -> dict:
    """The Craft editors this site has a build of, with their versions: what the page can offer."""
    return {editor: version for editor in EDITORS if (version := installed_version(editor))}


# `requested` is `str = ""`, not `str | None`: v15's whitelist argument coercion breaks on union
# types for values sent over HTTP (same note as editor.create_office_file). Empty = the default editor.
@frappe.whitelist(allow_guest=True)
@rate_limit(key=EDITOR_RATE["key"], limit=EDITOR_RATE["limit"], seconds=EDITOR_RATE["seconds"])
def get_craft_editor_config(file_id: str, requested: str = "") -> dict:
    """What the Drive page needs to open ``file_id`` in a Craft editor, or why it cannot.

    ``available`` is false, with a ``reason``, when the file cannot be read, when no editor opens its
    type (the page then goes on to upstream's viewer, which asks the person first), or when this site
    has no build of the editor (``editor`` is then named: the page says so and offers the file, and
    never sends it to an outside service). A file the caller cannot read answers exactly like a
    missing one. ``requested`` names an editor to use instead of the default one for the type
    (``pdf``: the PDF editor, which the Drive does not open on its own).
    """
    from suite.drive.api.permissions import user_has_permission

    if not frappe.db.exists("File", file_id):
        return {"available": False, "reason": _("File not found")}
    file = frappe.get_doc("File", file_id)
    if file.is_folder or not user_has_permission(file, "read"):
        return {"available": False, "reason": _("File not found")}

    file_name = file.file_name or ""
    editor = editor_for(file_name, requested or None)
    if not editor:
        return {"available": False, "reason": _("File type not supported")}
    version = installed_version(editor)
    if not version:
        return {"available": False, "editor": editor, "reason": _("The editor is not installed on this site")}

    can_write = bool(user_has_permission(file, "write"))
    token = generate_wopi_token(file_id, can_write=can_write)
    return {
        "available": True,
        "editor": editor,
        "base_url": f"{ASSETS_URL}{EDITORS[editor]['folder']}/",
        # The build is cached by the browser: its version in the URL makes a new build load.
        "version": version,
        "file_name": file_name,
        "can_write": can_write,
        "access_token": token["access_token"],
        "access_token_ttl": token["access_token_ttl"],
        # Same origin as the Drive page: the endpoints of endpoints.py, by path.
        "wopi_src": f"/wopi/files/{file_id}",
        "author": frappe.utils.get_fullname(frappe.session.user) if frappe.session.user != "Guest" else "",
        # Nora's pane in the editor, through this page's session (CraftEditor.vue, utils/craftNora.js).
        "nora": nora_for_the_person(),
    }


def clean_file_name(file_name: str) -> str:
    """A name safe to store: no path, no control characters, at most 140 characters."""
    name = os.path.basename((file_name or "").replace("\\", "/"))
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    stem, extension = os.path.splitext(name)
    if len(name) > 140:
        name = stem[: 140 - len(extension)] + extension
    return name


@frappe.whitelist(methods=["POST"])
def save_copy(file_id: str, file_name: str) -> dict:
    """Store the body of the request as a new file next to ``file_id``: Save As in an editor.

    The name is made unique in the folder, and the type stays the one of the source: a docx document
    saved as ``other.docx`` is a new docx document, never a way to put anything else in the Drive.
    """
    from suite.drive.api.permissions import user_has_permission

    if not frappe.db.exists("File", file_id) or not user_has_permission(file_id, "read"):
        frappe.throw(_("File not found"), frappe.DoesNotExistError)
    source = frappe.db.get_value("File", file_id, ["file_name", "folder", "is_folder"], as_dict=True)
    if source.is_folder:
        frappe.throw(_("File not found"), frappe.DoesNotExistError)

    parent = source.folder
    if not parent or not user_has_permission(parent, "upload"):
        frappe.throw(_("Cannot access folder due to insufficient permissions"), frappe.PermissionError)

    extension = extension_of(source.file_name or "")
    title = clean_file_name(file_name)
    if not title or extension_of(title) != extension or extension not in MIME_TYPES:
        frappe.throw(_("A copy keeps the type of the document"), frappe.ValidationError)

    content = frappe.request.get_data()
    if not content:
        frappe.throw(_("The document is empty"), frappe.ValidationError)
    if len(content) > MAX_COPY_BYTES:
        frappe.throw(_("The document is too large"), frappe.ValidationError)

    title = get_new_file_name(title, parent)
    mime_type = MIME_TYPES[extension]
    manager = FileManager()
    drive_file = create_drive_file(
        title,
        parent,
        get_file_type(mime_type),
        lambda file: "/" + str(manager.get_disk_path(file)),
        mime_type,
        len(content),
    )

    # Same placement as create_office_file: not manager.upload_file, which renames and assumes the
    # destination folder exists.
    if manager.s3_enabled:
        manager.conn.put_object(Bucket=manager.bucket, Key=get_s3_key(drive_file.file_url), Body=content)
        drive_file.file_url = get_s3_url(get_s3_key(drive_file.file_url))
        drive_file.save(ignore_permissions=True)
    else:
        destination = manager.site_folder / storage_key(drive_file.file_url)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with open(destination, "wb") as handle:
            handle.write(content)

    frappe.db.commit()
    return {"file_id": drive_file.name, "file_name": title}

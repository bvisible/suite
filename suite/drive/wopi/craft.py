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

import contextlib
import hashlib
import os
import re

import frappe
from frappe import _

# //// Neoffice — one call per document open.
from frappe.rate_limiter import rate_limit
from frappe.utils import cint

from suite.drive.utils import (
    STATUS_ACTIVE,
    apply_file_size_delta,
    create_drive_file,
    free_file_name,
    get_file_type,
    hold_folder_names,
)
from suite.drive.utils.files import FileManager, get_s3_key, get_s3_url, storage_key

from .token import generate_wopi_token

# //// Neoffice — the budget of the editor pre-flight, kept from the endpoint that used to share it with Collabora's.
# ////
# //// Keyed on `file_id`, so the identity frappe.rate_limiter counts is "<ip>:<document>" and not the bare IP: a
# //// whole office sits behind one public address, and a per-IP budget would be spent by whoever opened a
# //// document first. Per document it stays generous for people (opening the same file 20 times a minute is not
# //// something anybody does) while a loop hammering one document, which mints a token per call, runs out at once.
EDITOR_RATE = {"key": "file_id", "limit": 20, "seconds": 60}

# Editor -> the folder of its build under suite/public/craft/; `extensions`, the types it opens AND writes back in the
# same format (edited in place); `imports`, the types it opens and saves only as its own type, the first of `extensions`:
# a new file next to the original, which stays as it was (save_import). What each build takes, read from its bridge:
#   - GridCraft imports .xls, .xlsb and .ods (a workbook titled `<stem> (imported).xlsx`) and reads .csv and .tsv as
#     data; framed by a page, its Save is always an .xlsx (`file.saveBytes`), named `<stem> (imported).xlsx` or
#     `<stem>.xlsx`.
#   - WordCraft imports .doc (its Save comes back as `<stem>.docx`); it also reads .odt and .rtf: told the file is an import
#     (`imported` of `wordcraft:open`, CraftEditor.vue), a build that says `savesImports` makes `<stem>.docx` on Save too;
#     an earlier one writes them in their own type under their own name, and only its Save As comes back as `<stem>.docx`
#     (the page keeps the original and says to use Save As).
#   - DeckCraft's bridge takes nothing but its own packages, PdfCraft nothing but a PDF.
EDITORS = {
    "word": {"folder": "wordcraft", "extensions": ("docx",), "imports": ("doc", "odt", "rtf")},
    "sheet": {
        "folder": "gridcraft",
        "extensions": ("xlsx",),
        "imports": ("xls", "xlsb", "ods", "csv", "tsv"),
    },
    "deck": {"folder": "deckcraft", "extensions": ("pptx",), "imports": ()},
    "pdf": {"folder": "pdfcraft", "extensions": ("pdf",), "imports": ()},
}

# How an Office package begins: a ZIP archive, or an OLE container when it is saved with a password (an encrypted
# .docx). A save of an import is stored only if it is one: the new file is of the editor's type, never another.
PACKAGE_SIGNATURES = (b"PK\x03\x04", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")

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


def importer_for(file_name: str, requested: str | None = None) -> str | None:
    """The editor that imports ``file_name``: it opens it and saves it as its own type only (EDITORS, `imports`)."""
    extension = extension_of(file_name)
    for editor in (requested,) if requested else DEFAULT_EDITORS:
        if editor in EDITORS and extension in EDITORS[editor]["imports"]:
            return editor
    return None


# The longest name a new file of the editors gets: a File's name holds 140 characters, and a taken one gets ` (n)` added.
MAX_NEW_NAME = 130


def fit_name(file_name: str) -> str:
    """``file_name`` cut to MAX_NEW_NAME characters, its extension kept."""
    if len(file_name) <= MAX_NEW_NAME:
        return file_name
    stem, extension = os.path.splitext(file_name)
    return stem[: MAX_NEW_NAME - len(extension)] + extension


def native_name(file_name: str, editor: str) -> str:
    """The name an import is saved under: its own, in the editor's type (``Budget.xls`` -> ``Budget.xlsx``)."""
    stem = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
    return fit_name(clean_file_name(f"{stem}.{EDITORS[editor]['extensions'][0]}"))


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


def opened_extensions() -> dict:
    """Which file extension opens in which editor on this site, ``{"docx": "word", "doc": "word", "csv": "sheet", …}``:
    the types the editors this site has a build of write back and the ones they import alike, in lower case and without
    the dot. What another app offers to open in the Drive (NeoMail's « Open in … » on an attachment) is read here, in
    Python: not a web method (a page asks get_craft_editor_config of its file). The Drive page opens an import only when
    it asks for imports (get_craft_editor_config)."""
    installed = get_installed_editors()
    return {
        extension: editor
        for editor in DEFAULT_EDITORS
        if editor in installed
        for extension in (*EDITORS[editor]["extensions"], *EDITORS[editor]["imports"])
    }


# `requested` is `str = ""`, not `str | None`: v15's whitelist argument coercion breaks on union
# types for values sent over HTTP (same note as editor.create_office_file). Empty = the default editor.
@frappe.whitelist(allow_guest=True)
@rate_limit(key=EDITOR_RATE["key"], limit=EDITOR_RATE["limit"], seconds=EDITOR_RATE["seconds"])
def get_craft_editor_config(file_id: str, requested: str = "", imports: int = 0) -> dict:
    """What the Drive page needs to open ``file_id`` in a Craft editor, or why it cannot.

    ``available`` is false, with a ``reason``, when the file cannot be read, when no editor opens its
    type (the page then goes on to upstream's viewer, which asks the person first), or when this site
    has no build of the editor (``editor`` is then named: the page says so and offers the file, and
    never sends it to an outside service). A file the caller cannot read answers exactly like a
    missing one. ``requested`` names an editor to use instead of the default one for the type
    (``pdf``: the PDF editor, which the Drive does not open on its own).

    ``imports``: the caller also opens a type an editor imports (EDITORS, `imports`), which only a page that knows how
    to save it asks for (CraftEditor.vue: a new native file through save_import); any other caller (Neodesk's window,
    which writes in place) is told the type is not supported, as before. The answer then says ``imported: true`` and
    ``save_as``, the name the save takes before it is made free in the folder; its token never writes, the original
    stays as it was, and ``can_write`` says whether the person may add a file to the original's folder. An import
    whose editor this site has no build of is not supported either, never « not installed »: the page shows the type
    as it did before the editors imported it.
    """
    from suite.drive.api.permissions import user_has_permission

    if not frappe.db.exists("File", file_id):
        return {"available": False, "reason": _("File not found")}
    file = frappe.get_doc("File", file_id)
    # //// Neoffice — nor a row whose bytes the Drive does not store, a link above all (endpoints.get_wopi_file, GHSA-73gm)
    if file.is_folder or file._not_in_disk() or not user_has_permission(file, "read"):
        return {"available": False, "reason": _("File not found")}

    file_name = file.file_name or ""
    editor = editor_for(file_name, requested or None)
    imported = False
    if not editor and cint(imports):
        editor = importer_for(file_name, requested or None)
        imported = bool(editor)
    if not editor:
        return {"available": False, "reason": _("File type not supported")}
    version = installed_version(editor)
    if not version and imported:
        return {"available": False, "reason": _("File type not supported")}
    if not version:
        return {"available": False, "editor": editor, "reason": _("The editor is not installed on this site")}

    if imported:
        # The person adds the native file next to the original (save_import asks for the same right), never writes it.
        can_write = (
            frappe.session.user != "Guest"
            and bool(file.folder)
            and bool(user_has_permission(file.folder, "upload"))
        )
        token = generate_wopi_token(file_id, can_write=False)
    else:
        can_write = bool(user_has_permission(file, "write"))
        token = generate_wopi_token(file_id, can_write=can_write)
    answer = {
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
        # The locale the editor shows numbers in (`?locale=`, see editor_locale).
        "locale": editor_locale(),
    }
    if imported:
        answer.update({"imported": True, "save_as": native_name(file_name, editor)})
    return answer


def editor_locale() -> str:
    """The locale the editor shows numbers in, ``fr-CH``: the person's language and the country of the system's
    settings, as Excel takes the separators of numbers from the regional settings (``CHF 5'478.45`` in
    Switzerland). The editor reads it from ``?locale=`` (NeoSheet; an editor that does not know it ignores it).
    ``""`` when no country is set: the editor then takes the browser's."""
    country = frappe.db.get_single_value("System Settings", "country")
    code = str((frappe.db.get_value("Country", country, "code") if country else "") or "")
    language = str(getattr(frappe.local, "lang", "") or "en").replace("_", "-").split("-")[0]
    return f"{language}-{code.upper()}" if len(code) == 2 and code.isalpha() and language.isalpha() else ""


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

    content = request_body()
    drive_file = store_new_file(title, parent, MIME_TYPES[extension], content)
    return {"file_id": drive_file.name, "file_name": drive_file.file_name}


@frappe.whitelist(methods=["POST"])
def save_import(file_id: str) -> dict:
    """Store the body of the request as the document ``file_id`` was imported into: a new file next to it, of the type
    of the editor that imports it (EDITORS, `imports`), named after it (``Budget.xls`` -> ``Budget.xlsx``, or the first
    free ``Budget (n).xlsx``). The original is never written. Its name, its folder and the type come from the original,
    never from the request; the body must be an Office package (PACKAGE_SIGNATURES).

    Who may: whoever reads the original and may add a file to its folder (the right upload_file asks for). The new
    file is the person's own and private, as an upload of theirs, and counts against their quota.
    """
    from suite.drive.api.permissions import user_has_permission

    if not frappe.db.exists("File", file_id) or not user_has_permission(file_id, "read"):
        frappe.throw(_("File not found"), frappe.DoesNotExistError)
    source = frappe.db.get_value("File", file_id, ["file_name", "folder", "is_folder"], as_dict=True)
    if source.is_folder:
        frappe.throw(_("File not found"), frappe.DoesNotExistError)
    editor = importer_for(source.file_name or "")
    if not editor:
        frappe.throw(_("No editor imports this type of document"), frappe.ValidationError)

    parent = source.folder
    if not parent or not user_has_permission(parent, "upload"):
        frappe.throw(_("Cannot access folder due to insufficient permissions"), frappe.PermissionError)

    content = request_body()
    if not content.startswith(PACKAGE_SIGNATURES):
        frappe.throw(_("The document is not of the editor's type"), frappe.ValidationError)
    native = EDITORS[editor]["extensions"][0]

    # //// Neoffice — which file this save made from `file_id`, in the same transaction (saved_from reads it).
    def record(drive_file):
        if frappe.db.table_exists(SAVED_IMPORT):
            frappe.get_doc(
                {
                    "doctype": SAVED_IMPORT,
                    "original": file_id,
                    "saved_file": drive_file.name,
                    "editor": editor,
                }
            ).insert(ignore_permissions=True)

    drive_file = store_new_file(
        native_name(source.file_name, editor), parent, MIME_TYPES[native], content, then=record
    )
    return {"file_id": drive_file.name, "file_name": drive_file.file_name}


# The record of a save of an import (save_import): the original and the file the save made.
SAVED_IMPORT = "Drive Saved Import"


def saved_from(file_id: str) -> list[str]:
    """The files a save of the imported document ``file_id`` made (save_import), newest first: the ids of those that are
    still Active, in no folder in the trash, and that the session's person may write. Not a web method: NeoMail's server
    reads it to reopen, for an attachment it copied into the Drive before, the file its person saved from that copy."""
    from suite.drive.api.permissions import user_has_permission

    if not file_id or not isinstance(file_id, str) or not frappe.db.table_exists(SAVED_IMPORT):
        return []
    saved = frappe.get_all(
        SAVED_IMPORT, filters={"original": file_id}, pluck="saved_file", order_by="creation desc, name desc"
    )
    if not saved:
        return []
    active = set(
        frappe.get_all("File", filters={"name": ["in", saved], "status": STATUS_ACTIVE}, pluck="name")
    )
    return [
        name
        for name in saved
        if name in active and in_active_tree(name) and user_has_permission(name, "write")
    ]


def in_active_tree(name: str) -> bool:
    """Whether the entry ``name`` and every folder above it are Active (none in the trash)."""
    entry, seen = name, set()
    while entry and entry not in seen:
        seen.add(entry)
        status, entry = frappe.db.get_value("File", entry, ["status", "folder"]) or (None, None)
        if status != STATUS_ACTIVE:
            return False
    return True


def request_body() -> bytes:
    """The document a save sends: not empty, and not larger than MAX_COPY_BYTES."""
    content = frappe.request.get_data()
    if not content:
        frappe.throw(_("The document is empty"), frappe.ValidationError)
    if len(content) > MAX_COPY_BYTES:
        frappe.throw(_("The document is too large"), frappe.ValidationError)
    return content


def store_new_file(title: str, parent: str, mime_type: str, content: bytes, then=None):
    """Store ``content`` in ``parent`` as a new private file of the session's person, named ``title`` or the first free
    ``title (n).ext``, on the rules of the Drive's own upload (api/files.py, upload_file): a folder in the trash, or
    inside one, takes nothing; the name is given out while this request holds the folder's names, free in the folder
    and on the disk; the bytes count against the person's quota, under their storage lock; the folders' sizes grow; the
    pages that show the folder hear of it. ``then(drive_file)``, when given, writes what goes with the file in the same
    transaction (a failure there stores nothing). The caller checked the right to upload in ``parent``. Commits."""
    from suite.drive.api.files import _free_on_disk
    from suite.drive.api.storage import acquire_owner_storage_lock, validate_quota
    from suite.drive.utils.api import prettify_file

    if not in_active_tree(parent):
        frappe.throw(_("This folder is in the trash"), frappe.ValidationError)

    # Nothing of this request is written yet: the commit hold_folder_names makes shows it the names the requests that
    # held them before made, and comes before the storage lock, which a commit would release (upload_file).
    hold_folder_names(parent, commit=True)
    acquire_owner_storage_lock(frappe.session.user)
    validate_quota(incoming_size=len(content))

    manager = FileManager()
    title = _free_on_disk(free_file_name(fit_name(title), parent, locking=False), parent, manager)
    drive_file = create_drive_file(
        title,
        parent,
        get_file_type(mime_type),
        lambda file: "/" + str(manager.get_disk_path(file)),
        mime_type,
        len(content),
    )
    # The WebDAV's ETag and checksums are built from it (webdav/properties.py), as for an upload.
    drive_file.db_set("content_hash", hashlib.sha256(content).hexdigest(), update_modified=False)

    # Same placement as create_office_file: not manager.upload_file, which moves a file staged on the disk and assumes
    # the destination folder exists. The bytes are placed before the commit: a failure before it takes them away again,
    # never leaving bytes no row names (which would also push the next save of the name to `title (1)`).
    placed_key, placed_path = None, None

    def discard():
        if placed_path is not None:
            placed_path.unlink(missing_ok=True)
        if placed_key is not None:
            with contextlib.suppress(Exception):
                manager.conn.delete_object(Bucket=manager.bucket, Key=placed_key)

    try:
        if manager.s3_enabled:
            key = get_s3_key(drive_file.file_url)
            manager.conn.put_object(Bucket=manager.bucket, Key=key, Body=content)
            placed_key = key
            drive_file.file_url = get_s3_url(key)
            drive_file.flags.drive_sets_url = (
                True  # //// Neoffice — the Drive gives the address (File.validate)
            )
            drive_file.save(ignore_permissions=True)
        else:
            # //// Neoffice — in the files folders or nowhere (place_in_tree, GHSA-73gm): a copy into a folder frappe's own
            # //// API made, which has no address, landed at the top of the site's folder
            destination = manager.place_in_tree(storage_key(drive_file.file_url))
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            # "xb": never over bytes already there (_free_on_disk gave a free place; a request racing past it fails here,
            # and the bytes it found are not taken away)
            with open(destination, "xb") as handle:
                placed_path = destination
                handle.write(content)
        apply_file_size_delta(parent, len(content))
        if then is not None:
            then(drive_file)
    except Exception:
        discard()
        frappe.db.rollback()
        raise
    try:
        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        # What failed may come after the commit (its callbacks: a lock that had expired): the row then names the bytes,
        # which stay. Only a commit that did not happen takes them away.
        if not frappe.db.exists("File", drive_file.name):
            discard()
            raise
        frappe.log_error(
            "Drive: a new file was stored, a callback of its commit failed", frappe.get_traceback()
        )

    added = {"file": prettify_file(drive_file.as_dict())}
    frappe.publish_realtime("list-add", added, doctype="File", docname=parent)
    frappe.publish_realtime("list-add", added, user=frappe.session.user)
    return drive_file

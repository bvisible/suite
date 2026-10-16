# //// Neoffice — added file (no upstream equivalent): the second rows that two uploads of one name at once left
# //// before suite 34e7a552e go to the Drive's trash (maintenance#1598).
"""Rows of the Drive whose file is gone while a twin holds it.

Two uploads of one name into one folder at once made two rows for one blob (suite/drive/utils, hold_folder_names, ended
that). Once either row moved, its blob went with it and the other row pointed at nothing: the Drive lists it, its GET
answers « File content is missing », and every synchronised computer leaves it out. Such a row goes to the Drive's
trash here when its twin is there: an Active row of the same name, size and owner, made within a minute of it, whose
file is on the disk and whose content, when both rows know theirs, is the same. Nothing of it is lost: the twin holds it.

A row without its file and without such a twin is only named in the Error Log (« Drive: rows without content »): its
content may be on a computer that synchronised it, and trashing the row would make that computer delete its copy.
Attachments of documents, and files stored elsewhere than on this site's disk, are not looked at.

Run once by `bench migrate`. Nothing here may stop a migration: what fails is named in the Error Log, and the rest goes on.
"""

from __future__ import annotations

import frappe

from suite.drive.utils import STATUS_ACTIVE
from suite.drive.utils.files import FileManager, stored_on_disk

#: a twin was made by the same upload, at the same moment (68 ms apart on the instance where it was found)
TWIN_WINDOW_SECONDS = 60
#: how many rows without a twin the Error Log names
NAMED = 200


def execute():
    try:
        sweep()
    except Exception:
        frappe.log_error("Drive: sweep of the rows without content", frappe.get_traceback())


def sweep(only: list[str] | None = None) -> dict:
    """Trashes the rows without content that have a twin, names the others. `only`: the rows looked at (tests)."""
    manager = FileManager()
    rows = _rows(only)
    present: dict[tuple, list[frappe._dict]] = {}
    gone: list[frappe._dict] = []
    for row in rows:
        if not stored_on_disk(row.file_url):
            continue
        try:
            path = manager.get_local_path(row.file_url)
        except Exception:
            continue
        if path.is_file():
            present.setdefault(_key(row), []).append(row)
        elif not path.exists():
            gone.append(row)

    trashed, lone = [], []
    for row in gone:
        twin = next((other for other in present.get(_key(row), []) if _twins(row, other)), None)
        if twin is None:
            lone.append(row)
            continue
        frappe.db.savepoint("drive_sweep")
        try:
            _trash(row.name, manager)
            trashed.append(row.name)
        except Exception:
            # what this row's trashing wrote goes, the rest of the sweep stays
            frappe.db.rollback(save_point="drive_sweep")
            frappe.log_error(f"Drive: could not trash {row.name}", frappe.get_traceback())

    if lone:
        frappe.log_error(
            "Drive: rows without content",
            f"{len(lone)} row(s) of the Drive have no file where they say and no Active twin that holds it. They are "
            "left as they are: their content may be on a computer that synchronised them, or in the trash store "
            "(`.trash/<row>/…`) of a row that shared their file and went to the trash (two rows for one file or one "
            "folder, before suite 34e7a552e).\n\n"
            + "\n".join(f"{row.name}  {row.owner}  {row.file_name}" for row in lone[:NAMED]),
        )
    return {"trashed": trashed, "lone": [row.name for row in lone]}


def _rows(only: list[str] | None) -> list[frappe._dict]:
    restrict = "AND `name` IN %(only)s" if only is not None else ""
    if only is not None and not only:
        return []
    return frappe.db.sql(
        f"""
        SELECT `name`, file_name, file_size, `owner`, `creation`, file_url, content_hash
        FROM `tabFile`
        WHERE is_folder = 0
          AND `status` = %(active)s
          AND (attached_to_doctype IS NULL OR attached_to_doctype = '')
          AND content_doctype IS NULL
          AND (file_type IS NULL OR file_type != 'Link')
          AND file_url IS NOT NULL AND file_url != ''
          {restrict}
        """,
        {"active": STATUS_ACTIVE, "only": tuple(only or ())},
        as_dict=True,
    )


def _key(row: frappe._dict) -> tuple:
    return (row.file_name, int(row.file_size or 0), row.owner)


def _sha256(row: frappe._dict) -> str | None:
    value = (row.content_hash or "").strip().lower()
    return value if len(value) == 64 and all(char in "0123456789abcdef" for char in value) else None


def _twins(gone: frappe._dict, other: frappe._dict) -> bool:
    if gone.name == other.name:
        return False
    if abs((gone.creation - other.creation).total_seconds()) > TWIN_WINDOW_SECONDS:
        return False
    # both know their content: it must be the same
    mine, theirs = _sha256(gone), _sha256(other)
    return mine is None or theirs is None or mine == theirs


def _trash(name: str, manager: FileManager) -> None:
    """The Drive's own trash (recoverable from the web page), as a DELETE of the WebDAV makes it."""
    from suite.drive.api.files import toggle_entity_status

    toggle_entity_status(frappe.get_doc("File", name), manager, set())

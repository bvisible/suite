# //// Neoffice — added file (no upstream equivalent): the rows trashed or deleted before maintenance#1820 give up their
# //// url in the tree, as the rows trashed or deleted since do (FileManager.get_trash_url).
"""Rows of the Drive that left the tree and still hold its urls.

Until maintenance#1820, a row that went to the trash kept its file_url on its folder's path and its name, and a deleted
row kept its url for the 30 days it stays (clear_deleted_files). The next file of that name in that folder got the same
url, and frappe's check on private files refused it as a row reaching another owner's bytes. The files of a trashed
folder stayed Active with their old urls too.

Here, in the tree on the site's disk (flat storage keys every row by its id, and a site on S3 is flat):
- a trashed row that holds its place in the tree takes its place in the trash, where move_to_trash took its bytes, and
  the Active files of a trashed folder follow it there (repoint_descendants), as they followed its directory;
- a deleted private row takes its place in the trash, which names no bytes: its own were deleted with it.

Only urls change: no byte is moved, and `modified` stays (it times the purge of a deleted row). The rows are read in
batches, their fields only, with their folders' urls in one query per batch, and written in one UPDATE per batch; a
trashed folder and its files change together, in a savepoint of their own. Run once by `bench migrate`. What fails is
named in the Error Log and the rest goes on; nothing here stops a migration.
"""

from __future__ import annotations

from pathlib import Path

import frappe

from suite.drive.utils import STATUS_REMOVED, STATUS_TRASHED, WRITER_CONTENT_DOCTYPE
from suite.drive.utils.files import (
    TRASH_PREFIX,
    FileManager,
    escape_component,
    repoint_descendants,
    storage_key,
)

FIELDS = [
    "name",
    "status",
    "file_url",
    "folder",
    "file_name",
    "is_folder",
    "is_private",
    "file_type",
    "content_doctype",
]
BATCH = 500


def execute():
    try:
        release()
    except Exception:
        frappe.log_error("Drive: rows out of the tree kept their url", frappe.get_traceback())


def release(only: list[str] | None = None, batch: int = BATCH) -> dict:
    """Gives the rows out of the tree their place in the trash; returns how many rows of each kind changed, and how many
    failed. `only`: the rows looked at (tests)."""
    manager = FileManager()
    counts = {"trashed": 0, "removed": 0, "followed": 0, "failed": 0}
    if manager.flat or manager.s3_enabled:
        return counts
    trash = Path(storage_key(manager.get_root_storage_key())) / TRASH_PREFIX

    filters = {"status": ("in", [STATUS_TRASHED, STATUS_REMOVED]), "file_url": ("is", "set")}
    if only is not None:
        filters["name"] = ("in", only or [""])
    # decided on the urls the rows hold now, before any of them changes: a trashed row's place in the tree is its
    # folder's url and its name, and that folder may be one of these rows
    files, folders = [], []
    start = 0
    while True:
        rows = frappe.get_all(
            "File",
            filters=filters,
            fields=FIELDS,
            order_by="name",
            limit_start=start,
            limit_page_length=batch,
        )
        if not rows:
            break
        start += len(rows)
        parents = {row.folder for row in rows if row.folder}
        parent_urls = (
            dict(
                frappe.get_all(
                    "File", filters={"name": ("in", list(parents))}, fields=["name", "file_url"], as_list=True
                )
            )
            if parents
            else {}
        )
        for row in rows:
            content_without_storage = row.content_doctype and row.content_doctype != WRITER_CONTENT_DOCTYPE
            if row.file_type == "Link" or content_without_storage:
                continue
            key = Path(storage_key(row.file_url))
            if key == trash / row.name:
                continue
            if row.status == STATUS_TRASHED:
                tree = Path(storage_key(parent_urls.get(row.folder) or "")) / escape_component(row.file_name)
                if key != tree:
                    continue
                kind = "trashed"
            elif row.is_private:
                kind = "removed"
            else:
                continue
            (folders if kind == "trashed" and row.is_folder else files).append((row, kind))

    prefix = trash.as_posix() + "/"
    for start in range(0, len(files), batch):
        chunk = files[start : start + batch]
        frappe.db.savepoint("drive_rows_out_of_the_tree")
        try:
            frappe.db.sql(
                "UPDATE `tabFile` SET `file_url` = CONCAT(%s, `name`, IF(`is_folder`, '/', '')) WHERE `name` IN %s",
                (prefix, tuple(row.name for row, _kind in chunk)),
            )
            for _row, kind in chunk:
                counts[kind] += 1
        except Exception:
            frappe.db.rollback(save_point="drive_rows_out_of_the_tree")
            counts["failed"] += len(chunk)
            frappe.log_error("Drive: rows out of the tree kept their url (a batch)", frappe.get_traceback())

    for row, kind in folders:
        # a folder and the files that follow it change together, or not at all
        frappe.db.savepoint("drive_rows_out_of_the_tree")
        try:
            new_url = manager.get_trash_url(row)
            frappe.db.sql("UPDATE `tabFile` SET `file_url` = %s WHERE `name` = %s", (new_url, row.name))
            counts["followed"] += repoint_descendants(row.name, row.file_url, new_url)
            counts[kind] += 1
        except Exception:
            frappe.db.rollback(save_point="drive_rows_out_of_the_tree")
            counts["failed"] += 1
            frappe.log_error(
                f"Drive: could not give folder {row.name} its place in the trash", frappe.get_traceback()
            )
    frappe.clear_document_cache("File")
    return counts

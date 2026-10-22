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

Only urls change: no byte is moved, and `modified` stays (it times the purge of a deleted row). Run once by
`bench migrate`. A row that fails is named in the Error Log and the others go on; nothing here stops a migration.
"""

from __future__ import annotations

import frappe

from suite.drive.utils import STATUS_REMOVED, STATUS_TRASHED
from suite.drive.utils.files import FileManager, repoint_descendants


def execute():
    try:
        release()
    except Exception:
        frappe.log_error("Drive: rows out of the tree kept their url", frappe.get_traceback())


def release(only: list[str] | None = None) -> dict:
    """Gives the rows out of the tree their place in the trash; returns how many rows of each kind changed, and how many
    failed. `only`: the rows looked at (tests)."""
    manager = FileManager()
    counts = {"trashed": 0, "removed": 0, "followed": 0, "failed": 0}
    if manager.flat or manager.s3_enabled:
        return counts

    filters = {"status": ("in", [STATUS_TRASHED, STATUS_REMOVED]), "file_url": ("is", "set")}
    if only is not None:
        filters["name"] = ("in", only or [""])
    # decided on the urls the rows hold now, before any of them changes: a trashed row's place in the tree is its
    # folder's url and its name, and that folder may be one of these rows
    plan = []
    for name in frappe.get_all("File", filters=filters, pluck="name", order_by="name"):
        try:
            row = frappe.get_doc("File", name)
            if row._not_in_disk() or manager.holds_trash_url(row):
                continue
            if row.status == STATUS_TRASHED and manager.holds_tree_url(row):
                plan.append((row, "trashed"))
            elif row.status == STATUS_REMOVED and row.is_private:
                plan.append((row, "removed"))
        except Exception:
            counts["failed"] += 1
            frappe.log_error(f"Drive: could not look at row {name} out of the tree", frappe.get_traceback())

    for row, kind in plan:
        # a row and the files that follow it change together, or not at all
        frappe.db.savepoint("drive_row_out_of_the_tree")
        try:
            old_url, new_url = row.file_url, manager.get_trash_url(row)
            frappe.db.set_value("File", row.name, "file_url", new_url, update_modified=False)
            followed = (
                repoint_descendants(row.name, old_url, new_url) if kind == "trashed" and row.is_folder else 0
            )
            counts[kind] += 1
            counts["followed"] += followed
        except Exception:
            frappe.db.rollback(save_point="drive_row_out_of_the_tree")
            counts["failed"] += 1
            frappe.log_error(
                f"Drive: could not give row {row.name} its place in the trash", frappe.get_traceback()
            )
    return counts

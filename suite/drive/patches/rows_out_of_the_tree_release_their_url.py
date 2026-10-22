# //// Neoffice — added file (no upstream equivalent): the rows trashed or deleted before maintenance#1820 give up their
# //// url in the tree, as the rows trashed or deleted since do (FileManager.get_trash_url).
"""Rows of the Drive that left the tree and still hold its urls.

Until maintenance#1820, a row that went to the trash kept its file_url on its folder's path and its name, and a deleted
row kept its url for the 30 days it stays (clear_deleted_files). The next file of that name in that folder got the same
url, and frappe's check on private files refused it as a row reaching another owner's bytes. The files of a trashed
folder stayed Active with their old urls too.

Here, in the tree layout:
- a trashed row that holds its place in the tree takes its place in the trash, where move_to_trash took its bytes, and
  the Active files of a trashed folder follow it there, as they followed the folder's directory on the disk;
- a deleted private row takes its place in the trash, which names no bytes: its own were deleted with it.

Only urls change: no byte is moved, and `modified` stays (it times the purge of a deleted row). Run once by
`bench migrate`. Nothing here may stop a migration: what fails is named in the Error Log.
"""

from __future__ import annotations

from pathlib import Path

import frappe

from suite.drive.utils import STATUS_ACTIVE, STATUS_REMOVED, STATUS_TRASHED
from suite.drive.utils.files import FileManager, storage_key


def execute():
    try:
        release()
    except Exception:
        frappe.log_error("Drive: rows out of the tree kept their url", frappe.get_traceback())


def release(only: list[str] | None = None) -> dict:
    """Gives the rows out of the tree their place in the trash; returns how many rows of each kind changed. `only`: the
    rows looked at (tests)."""
    manager = FileManager()
    counts = {"trashed": 0, "removed": 0, "followed": 0}
    if manager.flat:
        return counts

    filters = {"status": ("in", [STATUS_TRASHED, STATUS_REMOVED]), "file_url": ("is", "set")}
    if only is not None:
        filters["name"] = ("in", only or [""])
    # decided on the urls the rows hold now, before any of them changes: a trashed row's place in the tree is its
    # folder's url and its name, and that folder may be one of these rows
    plan = []
    for name in frappe.get_all("File", filters=filters, pluck="name", order_by="name"):
        row = frappe.get_doc("File", name)
        if row._not_in_disk() or manager.holds_trash_url(row):
            continue
        if row.status == STATUS_TRASHED and manager.holds_tree_url(row):
            plan.append((row, "trashed"))
        elif row.status == STATUS_REMOVED and row.is_private:
            plan.append((row, "removed"))

    for row, kind in plan:
        old_key = Path(storage_key(row.file_url))
        frappe.db.set_value("File", row.name, "file_url", manager.get_trash_url(row), update_modified=False)
        counts[kind] += 1
        if kind == "trashed" and row.is_folder:
            counts["followed"] += _follow(row.name, old_key, manager.get_trash_path(row))
    return counts


def _follow(folder: str, old_key: Path, new_key: Path) -> int:
    """The Active rows under `folder` whose url is under `old_key` move under `new_key`, as recursive_path_move repoints
    them, without moving any byte (the folder's directory carried them). A row out of the tree is left to its own entry
    in the plan: its bytes are in its own place in the trash."""
    moved = 0
    for child in frappe.get_all(
        "File", filters={"folder": folder, "status": STATUS_ACTIVE}, fields=["name", "file_url"]
    ):
        if not child.file_url:
            continue
        key = Path(storage_key(child.file_url))
        if not key.is_relative_to(old_key):
            # an adopted framework upload, or a link: its url was never under the folder's
            continue
        new_child_key = new_key / key.relative_to(old_key)
        url = (
            ("/" if child.file_url.startswith("/") else "")
            + str(new_child_key)
            + ("/" if child.file_url.endswith("/") else "")
        )
        frappe.db.set_value("File", child.name, "file_url", url, update_modified=False)
        moved += 1 + _follow(child.name, key, new_child_key)
    return moved

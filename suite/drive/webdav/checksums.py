# //// Neoffice — added file (no upstream equivalent): the catch-up of the SHA-256 of the files the Drive held before it
# //// stamped one (maintenance#1598).
"""The SHA-256 of every file of the Drive, caught up in the background.

The WebDAV tells a synchronising client the SHA-256 of a file (`oc:checksums`) and builds its strong ETag from it
(webdav/properties.py), both from `File.content_hash`. A WebDAV PUT, an upload of the web page and an editor's save
stamp it as they write; the files that were there before, and what the framework or an app wrote without it, hold
nothing or an MD5. This job fills them in, a few at a time, so that a client that compares files by their sum has one
for all of them.

Nothing here changes a file: only the column is written, and only when the row is what it was when its bytes were
read (a file saved meanwhile stamps itself). Bytes that are not on this site's disk (S3, a file that went missing) are
not read: a missing file is marked `unreadable` once, so that it does not come back at every run.

Hourly (hooks.py). `drive_checksum_backfill: 0` in the site's configuration stops it.
"""

from __future__ import annotations

import hashlib
import time

import frappe

from suite.drive.utils import STATUS_ACTIVE
from suite.drive.utils.files import FileManager, storage_key, stored_on_disk

#: what one run may spend, and the most files it looks at
TIME_BUDGET_SECONDS = 90
BATCH = 1000
#: written for a file whose bytes cannot be read, so that it is not asked for again
UNREADABLE = "unreadable"
CHUNK = 1024 * 1024


def _pending(limit: int, names: list[str] | None = None) -> list[frappe._dict]:
    """Files that hold no SHA-256 yet: nothing, an MD5, or anything that is not 64 characters (newest first)."""
    only = ""
    values: dict = {"active": STATUS_ACTIVE, "unreadable": UNREADABLE, "limit": int(limit)}
    if names is not None:
        if not names:
            return []
        only = "AND `name` IN %(names)s"
        values["names"] = tuple(names)
    return frappe.db.sql(
        f"""
        SELECT `name`, file_url, `modified`
        FROM `tabFile`
        WHERE is_folder = 0
          AND content_doctype IS NULL
          AND (file_type IS NULL OR file_type != 'Link')
          AND `status` = %(active)s
          AND file_url IS NOT NULL AND file_url != ''
          AND (
            content_hash IS NULL OR content_hash = ''
            OR (CHAR_LENGTH(content_hash) != 64 AND content_hash != %(unreadable)s)
          )
          {only}
        ORDER BY `modified` DESC
        LIMIT %(limit)s
        """,
        values,
        as_dict=True,
    )


def sha256_of_path(path, deadline: float | None = None) -> str | None:
    """The SHA-256 of a file, or None when it is not there or the time ran out before its end."""
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as handle:
            while block := handle.read(CHUNK):
                digest.update(block)
                if deadline is not None and time.monotonic() > deadline:
                    return None
    except OSError:
        return UNREADABLE
    return digest.hexdigest()


def _stamp(name: str, modified, value: str) -> bool:
    """Writes the column when the row is still the one whose bytes were read; says whether it did."""
    frappe.db.sql(
        "UPDATE `tabFile` SET content_hash = %(value)s WHERE `name` = %(name)s AND `modified` = %(modified)s",
        {"value": value, "name": name, "modified": modified},
    )
    return frappe.db.get_value("File", name, "content_hash") == value


def backfill(limit: int = BATCH, names: list[str] | None = None, budget: float = TIME_BUDGET_SECONDS) -> dict:
    """One run of the catch-up. `names` narrows it to those files (tests, a repair by hand)."""
    if frappe.conf.get("drive_checksum_backfill") in (0, "0", False):
        return {"skipped": "switched off"}

    manager = FileManager()
    deadline = time.monotonic() + budget
    done = {"hashed": 0, "unreadable": 0, "changed_meanwhile": 0, "elsewhere": 0, "out_of_time": False}
    for row in _pending(limit, names):
        if time.monotonic() > deadline:
            done["out_of_time"] = True
            break
        if not stored_on_disk(row.file_url):
            # S3, or a url that is no blob of this disk: not read here (a download of the whole Drive is no job for an
            # hourly task), and not stamped either.
            done["elsewhere"] += 1
            continue
        path = manager.site_folder / storage_key(row.file_url)
        value = sha256_of_path(path, deadline)
        if value is None:
            done["out_of_time"] = True
            break
        if not _stamp(row.name, row.modified, value):
            done["changed_meanwhile"] += 1
        elif value == UNREADABLE:
            done["unreadable"] += 1
        else:
            done["hashed"] += 1
        if (done["hashed"] + done["unreadable"]) % 50 == 0:
            frappe.db.commit()
    frappe.db.commit()
    return done

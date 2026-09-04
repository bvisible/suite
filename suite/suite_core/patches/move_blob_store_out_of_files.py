#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import os
import shutil

import frappe
from frappe.utils import get_bench_path

from suite.store import get_blob_base_path


def execute() -> None:
    """Relocate the blob store from ``private/files/blob-store`` to the current blob base path.

    The blob store used to live inside ``private/files``, so every files backup tarred the whole
    blob cache. It now sits at ``get_blob_base_path()`` (the site directory root), which backups
    do not include. Migrating is a single directory move — the internal layout is unchanged.

    Best-effort: blobs are a cache refetched on demand, so if the new directory already exists
    (an interrupted earlier run, or stores already created at the new location) the old directory
    is simply dropped rather than merged.
    """

    old_path = os.path.join(get_bench_path(), "sites", frappe.local.site, "private", "files", "blob-store")
    if not os.path.isdir(old_path) or os.path.islink(old_path):
        return

    new_path = get_blob_base_path()
    if os.path.exists(new_path):
        shutil.rmtree(old_path, ignore_errors=True)
        return

    #//// Neoffice — shutil.move, not os.rename.
    #////
    #//// os.rename cannot cross filesystems, and on this fleet it always does: the
    #//// site's `private` and `public` are symlinks onto a separate data volume
    #//// (/mnt/neoffice), while the site directory itself lives on the system disk.
    #//// The move therefore died on `OSError: [Errno 18] Invalid cross-device link`
    #//// and took the whole migration with it (measured on osiris, 31.08.2026).
    #//// shutil.move falls back to copy+unlink when the two ends are on different
    #//// devices, and is a plain rename when they are not — so it costs nothing on a
    #//// single-volume host. Both blob-store patches carry the same shortcut.
    shutil.move(old_path, new_path)

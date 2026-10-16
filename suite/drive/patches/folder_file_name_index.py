# //// Neoffice — added patch (no upstream equivalent): the index through which the names of a folder are given out
# //// (suite/drive/utils, lock_folder_names: a locking read by folder and name, maintenance#1598). Without it that read
# //// would lock every row of tabFile, so until it exists names are given out as before. New sites get it at install
# //// (drive/install.py).
from __future__ import annotations

import frappe

from suite.drive.utils import FOLDER_NAME_INDEX


def execute():
    # idempotent: add_index checks the index before issuing the DDL
    frappe.db.add_index("File", ["folder", "file_name"], FOLDER_NAME_INDEX)

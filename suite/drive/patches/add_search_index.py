# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe


def execute():
    """Ensure the FULLTEXT index used by search exists on migrated sites."""
    index_check = frappe.db.sql("""SHOW INDEX FROM `tabFile` WHERE Key_name = 'drive_file_name_fts_idx'""")
    if not index_check:
        frappe.db.sql("""ALTER TABLE `tabFile` ADD FULLTEXT INDEX drive_file_name_fts_idx (file_name)""")

# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe
from frappe.model.document import Document

from suite.drive.api.notifications import notify_share
from suite.drive.utils import GENERAL_USER, GROUP_PREFIX


class DrivePermission(Document):
    def after_insert(self):
        # `notify_share` runs inline and emails per row; a migration rewriting
        # historical grants would mail everyone about folders they already had.
        if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_patch:
            return
        # //// Neoffice — an owner's own grant is not a share. grant_owner_access() stores
        # //// ownership as a Drive Permission row, so the private folder get_user_folder()
        # //// makes for every NEW account (portal customers included, through
        # //// create_drive_settings) mailed its owner « Frappe Drive - Folder Shared » about a
        # //// folder nobody shared (#363, osiris 2026-09-11). create_drive_file() sets the
        # //// folder's owner before that grant is written, so the test below holds.
        if self.user and frappe.db.get_value("File", self.entity, "owner") == self.user:
            return
        # Only individual users get notified — "" (anyone with the link),
        # $GENERAL (site users) and $GROUP: rows are not email addresses.
        if self.user and self.user != GENERAL_USER and not self.user.startswith(GROUP_PREFIX):
            frappe.enqueue(
                notify_share,
                queue="short",
                job_id=f"fdocperm_{self.name}",
                deduplicate=True,
                timeout=None,
                enqueue_after_commit=True,
                at_front=False,
                entity_name=self.entity,
                docperm_name=self.name,
            )

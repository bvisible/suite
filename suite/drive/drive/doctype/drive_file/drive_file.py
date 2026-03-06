from __future__ import annotations

import shutil
from pathlib import Path

import frappe
from frappe.model.document import Document
from frappe.utils import now
from frappe.rate_limiter import rate_limit

from drive.api.activity import create_new_activity_log
from drive.api.permissions import get_user_access, user_has_permission


class DriveFile(Document):
    def after_insert(self):
        full_name = frappe.db.get_value("User", {"name": frappe.session.user}, ["full_name"])
        message = f"{full_name} created {self.file_name}"
        create_new_activity_log(
            entity=self.name,
            activity_type="create",
            activity_message=message,
            document_field="file_name",
            field_new_value=self.file_name,
        )

    def on_trash(self):
        frappe.db.delete("Drive Favourite", {"entity": self.name})
        frappe.db.delete("Drive Entity Log", {"entity_name": self.name})
        frappe.db.delete("Drive Permission", {"entity": self.name})
        frappe.db.delete("Drive Notification", {"notif_doctype_name": self.name})
        frappe.db.delete("Drive Entity Activity Log", {"entity": self.name})

        if self.is_folder or self.document:
            for child in self.get_children():
                has_write_access = user_has_permission(self, "write")
                child.delete(ignore_permissions=has_write_access)

    def after_delete(self):
        """Cleanup after entity is deleted"""
        if self.document:
            frappe.delete_doc("Drive Document", self.document)

        # Don't delete files on disk
        # if self.path:
        #     self.manager.delete_file(self)

    def on_rollback(self):
        if self.flags.file_created:
            shutil.rmtree(self.path) if self.is_folder else self.path.unlink()





def on_doctype_update():
    frappe.db.add_index("Drive File", ["file_name"])

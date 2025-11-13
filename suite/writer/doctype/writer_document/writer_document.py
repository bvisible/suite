# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from datetime import datetime, timedelta

import frappe
from frappe.model.document import Document
import base64
import pycrdt
from writer.writer.dev import timing

COLLISION_ERRORS = (
    frappe.exceptions.QueryDeadlockError,
    frappe.exceptions.TimestampMismatchError,
)


class WriterDocument(Document):
    @timing
    def add_yjs_update(self, update_b64):
        """Add a YJS update to this document"""
        try:
            self.append("updates", {"data": update_b64})
            self.compact_yjs_updates()
            frappe.response["data"] = {"success": True}
        except COLLISION_ERRORS:
            frappe.response["data"] = {"skipped": True}
            return
        try:
            self.update_file(file_size=len(self.content))
        except COLLISION_ERRORS:
            pass

    def compact_yjs_updates(self):
        server_doc = pycrdt.Doc()
        server_doc.get("default", type=pycrdt.XmlFragment)
        if self.content:
            server_doc.apply_update(base64.b64decode(self.content))

        for upd in self.updates:
            server_doc.apply_update(base64.b64decode(upd.data))

        self.content = base64.b64encode(server_doc.get_update()).decode()
        self.updates = []
        self.save()

    def maybe_create_version(self, current_doc):
        """Create a version if 10 minutes have passed since last version"""
        # Check if we need to create a version
        if self.versions:
            last_creation = self.versions[-1].creation
            if (datetime.now() - last_creation) >= timedelta(minutes=10):
                return
        self.create_version(current_doc, manual=False)
        
    def create_version(self, doc=None, manual=False, title=None):
        """Create a new version of the document"""
        
        # If no doc provided, reconstruct from current state
        if doc is None:
            doc = pycrdt.Doc()
            doc.get("default", type=pycrdt.XmlFragment)
            if self.content:
                doc.apply_update(base64.b64decode(self.content))
            for upd in self.updates:
                doc.apply_update(base64.b64decode(upd.data))
        
        # Create snapshot
        snapshot_b64 = base64.b64encode(doc.get_update()).decode()
        
        # Get previous version for diff computation (optional for now)
        prev_version = frappe.get_all(
            "Writer Version",
            filters={"document": self.name},
            fields=["name", "snapshot"],
            order_by="creation desc",
            limit=1
        )
        
        # Create version document
        version = frappe.get_doc({
            "doctype": "Writer Version",
            "document": self.name,
            "snapshot": snapshot_b64,
            "manual": manual,
            "title": title or frappe.utils.now(),
            # Add metadata
            "character_count": self.get_character_count(doc),
        })
        
        version.insert()
        frappe.db.commit()  # Commit immediately so it's available
        
        return version.name
    def update_file(self, **kwargs):
        file = frappe.db.get_value("Drive File", {"doc": self.name}, "name")
        doc = frappe.get_doc("Drive File", file)
        for k in kwargs:
            setattr(doc, k, kwargs[k])
        doc._modified = frappe.utils.now()
        doc.save()

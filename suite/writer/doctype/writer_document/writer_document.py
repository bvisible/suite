# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

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

        # 1) if we have an existing snapshot, apply it first
        if self.content:
            server_doc.apply_update(base64.b64decode(self.content))

        # 2) load pending updates (ordered)
        for upd in self.updates:
            server_doc.apply_update(base64.b64decode(upd.data))

        # 4) produce a new snapshot (binary)
        # depending on pycrdt version the method to get full state might be get_update() or get_state()
        new_snapshot_b64 = base64.b64encode(server_doc.get_update()).decode()
        # 5) persist the snapshot and clear applied updates
        self.content = new_snapshot_b64

        # delete all pending updates (we applied them)
        self.updates = []
        self.save()

    def update_file(self, **kwargs):
        file = frappe.db.get_value("Drive File", {"doc": self.name}, "name")
        doc = frappe.get_doc("Drive File", file)
        for k in kwargs:
            setattr(doc, k, kwargs[k])
        doc._modified = frappe.utils.now()
        doc.save()

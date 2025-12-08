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

AUTOVERSION_DURATION = 10


class WriterDocument(Document):
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

    def save_yjs(self, data):
        try:
            self.content = data
            self.save()
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

    def new_version(self, html, title):
        """Create a new version of the document"""
        manual = bool(title)
        if not manual:
            now_time = frappe.utils.now_datetime()
            auto_versions = [v for v in self.versions if not v.manual]
            if auto_versions:
                prev_time = datetime.strptime(
                    auto_versions[-1].title,
                    "%Y-%m-%d %H:%M",
                )
                diff = now_time - prev_time
                if diff < timedelta(minutes=AUTOVERSION_DURATION):
                    frappe.response["data"] = False
            title = datetime.strftime(now_time, "%Y-%m-%d %H:%M")

        self.append(
            "versions",
            {
                "snapshot": html,
                "manual": manual,
                "title": title,
            },
        )
        self.save()
        frappe.response["data"] = self.versions[-1].as_dict()

    def update_file(self, **kwargs):
        file = frappe.db.get_value("Drive File", {"doc": self.name}, "name")
        doc = frappe.get_doc("Drive File", file)
        for k in kwargs:
            setattr(doc, k, kwargs[k])
        doc._modified = frappe.utils.now()
        doc.save()

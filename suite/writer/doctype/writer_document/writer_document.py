# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from datetime import datetime, timedelta
from drive.api.notifications import create_notification, get_link

import frappe
from frappe.model.document import Document
import base64
import pycrdt


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

    def save_doc(self, data, html=None):
        try:
            frappe.db.set_value("Writer Document", self.name, "content", data)
            if html is not None:
                frappe.db.set_value("Writer Document", self.name, "html", html)
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
            last_auto_version = frappe.db.get_value(
                "Writer Version",
                filters={
                    "doc": self.name,
                    "manual": 0,
                },
                fieldname=["title", "name", "creation"],
                order_by="creation desc",
                as_dict=True,
            )

            if last_auto_version:
                prev_time = datetime.strptime(
                    last_auto_version.title,
                    "%Y-%m-%d %H:%M",
                )
                diff = now_time - prev_time
                if diff < timedelta(minutes=AUTOVERSION_DURATION):
                    frappe.response["data"] = False
                    return

            title = datetime.strftime(now_time, "%Y-%m-%d %H:%M")

        # Create a new Writer Version document
        version = frappe.get_doc(
            {
                "doctype": "Writer Version",
                "doc": self.name,
                "snapshot": html,
                "manual": manual,
                "title": title,
            }
        )
        version.insert()

        frappe.response["data"] = version.as_dict()

    def update_file(self, **kwargs):
        file = frappe.db.get_value("Drive File", {"doc": self.name}, "name")
        doc = frappe.get_doc("Drive File", file)
        for k in kwargs:
            setattr(doc, k, kwargs[k])
        doc._modified = frappe.utils.now()
        doc.save()

    def save_comments(self, data, file):
        try:
            frappe.db.set_value("Writer Document", self.name, "ycomments", data)

            # Go over every comment in the YJS data and check replies for mentions
            comments_doc = pycrdt.Doc()
            comments_doc.apply_update(base64.b64decode(data))
            comments_map = comments_doc.get("comments", type=pycrdt.Map)
            for comment_id, comment_data in comments_map.items():
                mentions = [
                    {**k, "owner": comment_data["owner"]}
                    for k in comment_data.get("mentions", [])
                ]
                for reply in comment_data["replies"]:
                    mentions.extend(
                        [
                            {**k, "owner": reply["owner"]}
                            for k in reply.get("mentions", [])
                        ]
                    )
                print(mentions)
                if mentions:
                    frappe.enqueue(
                        notify_comments,
                        job_id=f"doc_comments_{self.name}_{comment_id}",
                        now=True,
                        deduplicate=True,
                        mentions=mentions,
                        file=file,
                    )
        except COLLISION_ERRORS:
            pass
    def rename(self):
        frappe.get_value({'doc': self.name}).rename()


def notify_comments(file, mentions):
    for mention in mentions:
        from_owner = frappe.get_cached_value("User", mention["owner"], "full_name")
        create_notification(
            mention["owner"],
            mention["id"],
            "Mention",
            file,
            f'{from_owner} mentioned you in a comment in "{file.title}".',
        )
        print("Shared with", mention["owner"])
        try:
            frappe.sendmail(
                recipients=[mention["id"]],
                subject=f"Frappe Drive - Mention in {file.title}",
                template="drive_comment",
                args={
                    "message": f"{from_owner} mentioned you in a comment.",
                    "doc": file.title,
                    "link": get_link(file),
                },
                now=True,
            )
        except:
            frappe.log_error(frappe.get_traceback())

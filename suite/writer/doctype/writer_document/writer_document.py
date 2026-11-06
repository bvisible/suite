# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import base64
from datetime import datetime, timedelta

import frappe
import pycrdt
from frappe import _  # //// Neoffice — for check_comment_changes below
from frappe.model.document import Document
from frappe.utils.html_utils import sanitize_html  # //// Neoffice — for clean_html below

from suite.drive.api.notifications import create_notification, get_link
from suite.suite_core import suite_email

COLLISION_ERRORS = (
    frappe.exceptions.QueryDeadlockError,
    frappe.exceptions.TimestampMismatchError,
)

AUTOVERSION_DURATION = 10


# //// Neoffice — the stored `html` is drawn as markup (the Writer home's grid view, v-html) and indexed for the
# //// search snippets, so it goes through frappe's XSS filter on every path. save_doc writes it with
# //// db.set_value, which skips Document._sanitize_content; and that filter returns any value that parses as JSON
# //// unchanged (a JSON string literal holding a tag included), hence always_sanitize. Ordinary formatting
# //// (headings, lists, tables, links, images, inline styles) is on the filter's allow list and is kept.
def clean_html(html: str | None) -> str | None:
    if not html:
        return html
    return sanitize_html(html, always_sanitize=True)


# //// Neoffice — what a comment-only reader may change in the comments blob (save_comments below).
def read_comments(data: str | None) -> dict:
    """The comments of a stored Y.js comments blob, as plain data: {comment id: comment}."""
    if not data:
        return {}
    comments_doc = pycrdt.Doc()
    comments_doc.apply_update(base64.b64decode(data))
    return comments_doc.get("comments", type=pycrdt.Map).to_py() or {}


def comment_entries(comments: dict) -> dict:
    """{entry id: (owner, text)} for every comment and every reply of a comments map."""
    entries = {}
    for comment_id, comment in comments.items():
        if not isinstance(comment, dict):
            continue
        entries[comment_id] = (comment.get("owner"), comment.get("text"))
        for reply in comment.get("replies") or []:
            if isinstance(reply, dict) and (reply.get("id") or reply.get("name")):
                entries[reply.get("id") or reply.get("name")] = (reply.get("owner"), reply.get("text"))
    return entries


def check_comment_changes(old: dict, new: dict, user: str) -> None:
    """A reader who may only comment adds and edits their own comments and replies, and nobody else's."""
    before, after = comment_entries(old), comment_entries(new)
    for entry_id, (owner, text) in before.items():
        if owner != user and after.get(entry_id) != (owner, text):
            frappe.throw(_("You can only change your own comments."), frappe.PermissionError)
    for entry_id, (owner, _text) in after.items():
        if entry_id not in before and owner != user:
            frappe.throw(_("A new comment must be written in your own name."), frappe.PermissionError)


class WriterDocument(Document):
    def on_trash(self):
        # Versions are a standalone doctype linking back here, so the framework's
        # link check would refuse the delete before anything cleaned them up —
        # and nothing outside this document references a version.
        frappe.db.delete("Writer Version", {"doc": self.name})

    @frappe.whitelist(methods=["POST"])
    def save_doc(self, data: str, html: str | None = None):
        self.check_permission("write")
        try:
            frappe.db.set_value("Writer Document", self.name, "content", data)
            if html is not None:
                # //// Neoffice — filtered as on save(): see clean_html
                frappe.db.set_value("Writer Document", self.name, "html", clean_html(html))
            self.update_file(file_size=len(self.content))
        except COLLISION_ERRORS:
            pass

    @frappe.whitelist(methods=["POST"])
    def new_version(self, data: str, title: str | None = None):
        """Create a new version of the document"""
        self.check_permission("write")
        if not data or not data.strip() or data.strip() == "<p></p>":
            frappe.response["data"] = False
            return

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
                "snapshot": data,
                "manual": manual,
                "title": title,
            }
        )
        version.insert()

        frappe.response["data"] = version.as_dict()

    @frappe.whitelist(methods=["POST"])
    def update_settings(self, data: str):
        self.check_permission("write")
        self.settings = data
        self.save()

    @frappe.whitelist(methods=["POST"])
    def save_html(self, html: str):
        self.check_permission("write")
        # //// Neoffice — the JSON-shaped value save() would let through: clean_html
        self.html = clean_html(html)
        self.update_file()
        self.save()

    def update_file(self, **kwargs):
        file = frappe.db.get_value(
            "File", {"content_docname": self.name, "content_doctype": "Writer Document"}, "name"
        )
        doc = frappe.get_doc("File", file)
        for k in kwargs:
            setattr(doc, k, kwargs[k])
        doc.file_modified = frappe.utils.now()
        doc.save(ignore_permissions=True)

    def save_comments(self, data, file, can_write: bool = True):
        # //// Neoffice — the blob is built by the client, owners included. A reader who may only comment can
        # //// no longer rewrite or delete the others' comments nor add one in another name (check_comment_changes);
        # //// and a mention is announced only for the comments and replies of the person saving, so no e-mail
        # //// goes out as "<someone else> mentioned you". Each author's own save announces their mentions (the
        # //// notification is created once: create_notification skips one that exists).
        user = frappe.session.user
        comments_map = read_comments(data)
        if not can_write:
            check_comment_changes(read_comments(self.ycomments), comments_map, user)
        try:
            frappe.db.set_value("Writer Document", self.name, "ycomments", data)

            # Go over every comment in the YJS data and check replies for mentions
            # //// Neoffice — read once above (read_comments); only the saver's own comments and replies count
            for comment_id, comment_data in comments_map.items():
                if not isinstance(comment_data, dict):
                    continue
                mentions = (
                    [{**k, "owner": user} for k in comment_data.get("mentions") or []]
                    if comment_data.get("owner") == user
                    else []
                )
                for reply in comment_data.get("replies") or []:
                    if isinstance(reply, dict) and reply.get("owner") == user:
                        mentions.extend([{**k, "owner": user} for k in reply.get("mentions") or []])
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

    def as_dict(self, *args, **kwargs):
        result = super().as_dict(*args, **kwargs)
        result.pop("versions")
        return result


def notify_comments(file, mentions):
    for mention in mentions:
        from_owner = frappe.get_cached_value("User", mention["owner"], "full_name")
        new_notification = create_notification(
            mention["owner"],
            mention["id"],
            "Mention",
            file,
            f'{from_owner} mentioned you in a comment in "{file.file_name}".',
        )
        if new_notification:
            try:
                link = frappe.utils.get_url(get_link(file))
                suite_email.enqueue(
                    "writer-mention",
                    mention["id"],
                    {"author": from_owner, "document": file.file_name, "link": link},
                    local={
                        "subject": f"Frappe Drive - Mention in {file.file_name}",
                        "template": "drive_comment",
                        "args": {
                            "message": f"{from_owner} mentioned you in a comment.",
                            "doc": file.file_name,
                            "link": link,
                        },
                    },
                )
            except Exception:
                frappe.log_error(frappe.get_traceback())

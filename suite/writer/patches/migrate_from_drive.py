import frappe
from pycrdt import Doc, Map
import base64


def migrate_doc(file):
    try:
        old_doc = frappe.get_doc("Drive Document", file.document)
        new_doc = frappe.get_doc(
            {
                "doctype": "Writer Document",
                "content": old_doc.content,
                "settings": old_doc.settings,
            }
        )
        new_doc.insert()
        if file.comments:
            commentsDoc = Doc()
            comments = commentsDoc.get("comments", type=Map)
            for comment in file.comments:
                comments[comment.name] = {
                    "id": comment.name,
                    "creation": comment.creation.timestamp() * 1000,
                    "owner": comment.owner,
                    "text": comment.content,
                    "replies": [],
                    "anchor": {},
                }
            new_doc.ycomments = base64.b64encode(commentsDoc.get_update()).decode()
            new_doc.save()

        file.doc = new_doc.name
        file.save()
    except:
        print("Failed to migrate:", file.name)


def execute():
    documents = frappe.get_all("Drive File", {"mime_type": "frappe_doc"})
    for file in documents:
        migrate_doc(file)

import frappe
import json
from pycrdt import Doc, Map
import base64

ACCEPTED_SETTINGS = [
    "minimal",
    "wide",
    "lock",
    "font_family",
    "font_size",
    "line_height",
]


def migrate_doc(file):
    try:
        old_doc = frappe.get_doc("Drive Document", file.document)
        settings = json.loads(old_doc.settings)
        collab = settings.get("collab", 0)
        for key in list(settings):
            if key not in ACCEPTED_SETTINGS:
                settings.pop(key)
        settings["old_schema"] = True

        new_doc = frappe.get_doc(
            {
                "doctype": "Writer Document",
                "content": old_doc.content,
                "html": old_doc.raw_content,
                "settings": json.dumps(settings),
                "collab": int(collab),
            }
        )

        new_doc.insert()
        if file.comments:
            commentsDoc = Doc()
            comments = commentsDoc.get("comments", type=Map)
            for comment in file.comments:
                replies = []
                reply_docs = frappe.get_all(
                    "Drive Comment",
                    filters={"parenttype": "Drive Comment", "parent": comment.name},
                    fields=["content", "owner", "creation", "name"],
                )
                for r in reply_docs:
                    replies.append(
                        {
                            "id": r.name,
                            "creation": r.creation.timestamp() * 1000,
                            "owner": r.owner,
                            "text": r.content,
                        }
                    )

                comments[comment.name] = {
                    "id": comment.name,
                    "creation": comment.creation.timestamp() * 1000,
                    "owner": comment.owner,
                    "text": comment.content,
                    "replies": replies,
                    "resolved": comment.resolved,
                    "anchor": {},
                }
            new_doc.ycomments = base64.b64encode(commentsDoc.get_update()).decode()
            new_doc.save()

        frappe.db.set_value(
            "Writer Document",
            new_doc.name,
            "owner",
            old_doc.owner,
            update_modified=False,
        )
        frappe.db.set_value(
            "Writer Document",
            new_doc.name,
            "creation",
            old_doc.creation,
            update_modified=False,
        )
        frappe.db.set_value(
            "Writer Document",
            new_doc.name,
            "modified",
            old_doc.modified,
            update_modified=False,
        )

        file.doc = new_doc.name
        file.save()
    except BaseException as e:
        print(f"{e}\nFailed to migrate:", file.name)


def execute():
    documents = frappe.get_all("Drive File", {"mime_type": "frappe_doc"}, pluck="name")
    for file in documents:
        migrate_doc(frappe.get_doc("Drive File", file))

from pathlib import Path

import frappe
from drive.utils import (
    create_drive_file,
    default_team,
    get_home_folder,
)
from drive.api.files import get_new_title
from drive.api.permissions import user_has_permission
from drive.utils.files import FileManager


@frappe.whitelist()
@default_team
def create_document_entity(team, title=None, parent=None, template=None):
    home_directory = get_home_folder(team)
    parent = parent or home_directory.name
    parent_doc = frappe.get_cached_doc("Drive File", parent)
    team = frappe.db.get_value("Drive File", parent, "team")
    if not title:
        title = get_new_title("Untitled Document", parent)

    if not user_has_permission(parent, "upload"):
        frappe.throw(
            "Cannot access folder due to insufficient permissions",
            frappe.PermissionError,
        )
    drive_doc = frappe.new_doc("Drive Document")
    drive_doc.title = title
    if template:
        drive_doc.template = template
    drive_doc.settings = (
        '{"collab": true}'
        if not template
        else '{"collab": true, "template": "' + template + '"}'
    )
    print(drive_doc.settings)
    drive_doc.save()

    manager = FileManager()
    path = manager.create_folder(
        frappe._dict(
            {
                "title": title,
                "parent_path": Path(parent_doc.path or ""),
                "team": team,
                "parent_entity": parent_doc.name,
            }
        ),
        home_directory,
    )
    manager.create_folder(
        frappe._dict(
            {
                "title": ".embeds",
                "team": team,
                "parent_path": path,
            }
        ),
        home_directory,
    )

    entity = create_drive_file(
        team,
        title,
        parent,
        "frappe_doc",
        lambda _: path,
        document=drive_doc.name,
    )
    return entity

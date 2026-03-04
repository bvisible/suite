"""
Create `File` records of all existing `Drive File`s
"""

import frappe
from drive.utils import get_file_type


def execute(files=[]):
    if not files:
        root_files = frappe.get_all("Drive File", filters={"folder": ""}, pluck="name")

    for file_id in root_files:
        folder = frappe.get_doc("Drive File", file_id)
        migrate_folder(folder)


def migrate_folder(folder):
    print(f"Migrating folder {folder}")
    migrate_file(folder)

    for child in folder.get_children():
        if child.is_group or child.doc:
            migrate_folder(child)
        else:
            migrate_file(child)


def migrate_file(file):
    if frappe.db.exists("File", {"is_drive_file": 1, "name": file.name}):
        return

    ff_file = frappe.get_doc(
        {
            "doctype": "File",
            "is_drive_file": 1,
            "_name": file.name,
            "file_name": file.title,
            # rename field
            "drive_team": file.team,
            "file_url": file.path,
            "folder": file.folder,
            "is_folder": file.is_group,
            "file_size": file.file_size,
            "last_modified": file._modified,
            "status": file.is_active,
            "is_private": 1,
        }
    )

    if file.doc:
        ff_file.special_file = "Writer Document"
        ff_file.special_file_doc = file.doc

    # Attachment
    if frappe.db.get_value("Drive File", file.folder, "doc"):
        ff_file.attached_to_doctype = "File"
        ff_file.attached_to_name = file.folder
    # Write eq code for slides

    # Calculate file type
    ff_file.file_type = get_file_type(file.as_dict())

    settings = {}
    if file.color:
        settings["color"] = file.color
    if not file.allow_download:
        settings["forbid_download"] = 1
    ff_file.settings = settings
    ff_file.insert()

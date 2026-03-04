"""
Create `File` records of all existing `Drive File`s
"""

import frappe
from drive.utils import get_file_type


def execute(files=[]):
    if not files:
        files = frappe.get_all("Drive File", pluck=["name"])
    for file in files:
        file = frappe.get_doc("Drive File", file)
        ff_file = frappe.get_doc(
            {
                "doctype": "File",
                "is_drive_file": 1,
                "_name": file.name,
                "file_name": file.title,
                "team": file.team,
                "file_url": file.path,
                "folder": file.parent_entity,
                "is_folder": file.is_group,
                "file_size": file.file_size,
                "_modified": file._modified,
                "status": file.is_active,
                "is_private": 1,
            }
        )


        if file.doc:
            ff_file.special_file = "Writer Document"
            ff_file.special_file_doc = file.doc
        # Write eq code for link, slides
        # Calculate file type
        ff_file.file_type = get_file_type(file.as_dict())
        
        settings = {}
        if file.color:
            settings["color"] = file.color
        if not file.allow_download:
            settings["forbid_download"] = 1
        ff_file.settings = settings
        ff_file.insert()

import frappe

"""
Migrate Writer Document versions from child table to independent Writer Version doctype
"""


def execute():
    writer_docs = frappe.get_all("Writer Document", pluck="name")

    for doc_name in writer_docs:
        doc = frappe.get_doc("Writer Document", doc_name)

        if doc.versions:
            for version in doc.versions:
                # Create new Writer Version document
                new_version = frappe.get_doc(
                    {
                        "doctype": "Writer Version",
                        "doc": doc.name,
                        "snapshot": version.snapshot,
                        "title": version.title,
                        "manual": version.manual,
                    }
                )
                new_version.insert(ignore_permissions=True)
                frappe.db.set_value(
                    "Writer Version",
                    new_version.name,
                    "creation",
                    version.creation,
                    update_modified=False,
                )
            doc.versions = []
            doc.save(ignore_permissions=True)

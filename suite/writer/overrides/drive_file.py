from drive.drive.doctype.drive_file.drive_file import DriveFile
import frappe


class WriterDriveFile(DriveFile):
    @frappe.whitelist()
    def add_yjs_update(self, update_b64):
        return frappe.get_cached_doc("Writer Document", self.doc).add_yjs_update(
            update_b64
        )

    @frappe.whitelist()
    def new_version(self, data, title=False):
        return frappe.get_cached_doc("Writer Document", self.doc).new_version(
            data, title
        )

    @frappe.whitelist()
    def save_comments(self, data):
        doc = frappe.get_cached_doc("Writer Document", self.doc)
        doc.ycomments = data
        doc.save()

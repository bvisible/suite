from drive.drive.doctype.drive_file.drive_file import DriveFile
import frappe


class WriterDriveFile(DriveFile):
    @frappe.whitelist()
    def add_yjs_update(self, update_b64):
        frappe.get_cached_doc("Writer Document", self.doc).add_yjs_update(update_b64)
        frappe.response["docs"] = None

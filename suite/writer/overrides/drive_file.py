from drive.drive.doctype.drive_file.drive_file import DriveFile
import frappe

from drive.api.permissions import requires


class WriterDriveFile(DriveFile):
    @frappe.whitelist(allow_guest=True)
    @requires("write")
    def add_yjs_update(self, update_b64):
        return frappe.get_doc("Writer Document", self.doc).add_yjs_update(update_b64)

    @frappe.whitelist(allow_guest=True)
    @requires("write")
    def save_doc(self, data, html):
        frappe.get_doc("Writer Document", self.doc).save_doc(data, html)

    @frappe.whitelist(allow_guest=True)
    @requires("write")
    def new_version(self, data, title=False):
        return frappe.get_doc("Writer Document", self.doc).new_version(data, title)

    @frappe.whitelist(allow_guest=True, permissions=["comment"])
    @requires("comment")
    def save_comments(self, data):
        return frappe.get_doc("Writer Document", self.doc).save_comments(data, self)

    @frappe.whitelist(allow_guest=True)
    def update_settings(self, data):
        doc = frappe.get_doc("Writer Document", self.doc)
        doc.settings = data
        doc.save()

    @frappe.whitelist(allow_guest=True)
    def save_html(self, html):
        doc = frappe.get_doc("Writer Document", self.doc)
        doc.html = html
        doc.save()
        self._modified = frappe.utils.now()
        self.save()

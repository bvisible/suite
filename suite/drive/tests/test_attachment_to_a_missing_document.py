# //// Neoffice — added file (no upstream equivalent). A file attached to a document that does not exist gives no
# //// access and breaks nothing: frappe.db.exists answers yes when the name is the doctype's own (it takes the pair
# //// for a Single), get_doc then raised in _ref_doc_access, and the person's whole Drive search with it
# //// (neoffice-maintenance#2960).
from __future__ import annotations

import frappe
from frappe.tests import IntegrationTestCase

from suite.drive.api.permissions import _ref_doc_access


class TestAnAttachmentToAMissingDocument(IntegrationTestCase):
    def setUp(self):
        frappe.flags.mute_drive_activity_log = True

    def tearDown(self):
        frappe.flags.mute_drive_activity_log = False
        super().tearDown()

    def _attached(self, doctype, name):
        file_name = f"attachment-{frappe.generate_hash(length=6)}.txt"
        return frappe.get_doc(
            {
                "doctype": "File",
                "file_name": file_name,
                "content": file_name.encode(),
                "is_private": 1,
                "attached_to_doctype": doctype,
                "attached_to_name": name,
            }
        ).insert(ignore_permissions=True)

    def test_a_file_attached_to_its_doctypes_own_name_gives_no_access_and_raises_nothing(self):
        # ToDo is no Single and no ToDo is named « ToDo », yet frappe.db.exists answers « ToDo »
        self.assertIsNone(frappe.db.get_value("ToDo", {"name": "ToDo"}))
        self.assertEqual(frappe.db.exists("ToDo", "ToDo"), "ToDo")
        doc = self._attached("ToDo", "ToDo")
        before = len(frappe.local.message_log)
        access = _ref_doc_access(doc, "Guest")
        self.assertEqual((access["read"], access["write"], access["upload"]), (0, 0, 0))
        self.assertEqual(len(frappe.local.message_log), before, "no « not found » message reaches the person")

    def test_a_file_attached_to_a_single_still_follows_it(self):
        doc = self._attached("System Settings", "System Settings")
        access = _ref_doc_access(doc, "Administrator")
        self.assertEqual((access["read"], access["write"]), (1, 1))

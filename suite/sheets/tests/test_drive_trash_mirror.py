# //// Neoffice — added file (no upstream equivalent): the Drive's trash reaches the workbook the row stands for
# //// (suite/drive/api/files.py, _mirror_trash_to_content_doc; maintenance#1600).
from __future__ import annotations

import frappe
from frappe.tests import IntegrationTestCase

from suite.drive.api.files import toggle_entity_status
from suite.drive.overrides.file import File as DriveFile
from suite.drive.utils import STATUS_ACTIVE, STATUS_TRASHED
from suite.drive.utils.files import FileManager
from suite.sheets.api import create_sheet, list_sheets, list_trash
from suite.tests.utils import ensure_user

OWNER = "sheets-trash-mirror-owner@example.com"


class TestDriveTrashMirror(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_user(OWNER)

    def setUp(self):
        frappe.flags.mute_drive_activity_log = True
        self.manager = FileManager()
        with self.set_user(OWNER):
            self.sheet = create_sheet(f"Trash mirror {frappe.generate_hash(length=6)}")
        self.file_name = DriveFile.get_for_doc("Sheet", self.sheet)

    def tearDown(self):
        frappe.flags.mute_drive_activity_log = False
        super().tearDown()

    def toggle_from_drive(self):
        """What the Drive's « Supprimer » (remove_or_restore) does to the row of the workbook."""
        with self.set_user(OWNER):
            toggle_entity_status(frappe.get_doc("File", self.file_name), self.manager, set())

    def listed_in_sheets(self):
        with self.set_user(OWNER):
            return self.sheet in [row["name"] for row in list_sheets()["sheets"]]

    def in_sheets_trash(self):
        with self.set_user(OWNER):
            return self.sheet in [row["name"] for row in list_trash()["sheets"]]

    def test_a_workbook_trashed_from_the_drive_leaves_the_list_of_sheets(self):
        self.assertTrue(self.listed_in_sheets())

        self.toggle_from_drive()

        self.assertEqual(frappe.db.get_value("File", self.file_name, "status"), STATUS_TRASHED)
        trashed = frappe.db.get_value(
            "Sheet", self.sheet, ["trashed", "trashed_on", "trashed_by"], as_dict=True
        )
        self.assertEqual(trashed.trashed, 1)
        self.assertTrue(trashed.trashed_on, "the retention clock of Sheets starts")
        self.assertEqual(trashed.trashed_by, OWNER)
        self.assertFalse(self.listed_in_sheets())
        self.assertTrue(self.in_sheets_trash(), "it can be restored from the trash of Sheets too")

    def test_a_workbook_restored_from_the_drive_comes_back_in_the_list_of_sheets(self):
        self.toggle_from_drive()

        self.toggle_from_drive()

        self.assertEqual(frappe.db.get_value("File", self.file_name, "status"), STATUS_ACTIVE)
        trashed = frappe.db.get_value(
            "Sheet", self.sheet, ["trashed", "trashed_on", "trashed_by"], as_dict=True
        )
        self.assertEqual((trashed.trashed, trashed.trashed_on, trashed.trashed_by), (0, None, None))
        self.assertTrue(self.listed_in_sheets())
        self.assertFalse(self.in_sheets_trash())

    def test_the_trash_of_sheets_still_reaches_the_drive(self):
        from suite.sheets.api import delete_sheet

        with self.set_user(OWNER):
            delete_sheet(self.sheet)

        self.assertEqual(frappe.db.get_value("File", self.file_name, "status"), STATUS_TRASHED)
        self.assertFalse(self.listed_in_sheets())

    def test_a_row_that_stands_for_no_document_is_trashed_as_before(self):
        with self.set_user(OWNER):
            folder_row = frappe.get_doc("File", self.file_name)
        # a row that holds no document: the same row, with the link to its workbook cut in memory only
        folder_row.content_doctype = None
        folder_row.content_docname = None

        from suite.drive.api.files import _mirror_trash_to_content_doc

        _mirror_trash_to_content_doc(folder_row, STATUS_TRASHED)

        self.assertEqual(frappe.db.get_value("Sheet", self.sheet, "trashed"), 0)

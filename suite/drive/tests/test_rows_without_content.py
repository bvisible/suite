# //// Neoffice — added file (no upstream equivalent): the sweep of the rows of the Drive whose file is gone
# //// (suite/drive/patches/trash_rows_without_content.py; maintenance#1598).
from __future__ import annotations

import hashlib
import shutil

import frappe
from frappe.tests import IntegrationTestCase

from suite.drive.patches.trash_rows_without_content import sweep
from suite.drive.utils import STATUS_ACTIVE, STATUS_TRASHED, create_drive_file, get_user_folder
from suite.drive.utils.files import FileManager
from suite.tests.utils import ensure_user

OWNER = "drive-sweep-owner@example.com"


class TestRowsWithoutContent(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_user(OWNER)
        with cls.set_user(OWNER):
            cls.home = get_user_folder(OWNER).name

    def setUp(self):
        frappe.flags.mute_drive_activity_log = True
        self.manager = FileManager()
        with self.set_user(OWNER):
            self.folder = create_drive_file(
                f"Sweep-{frappe.generate_hash(length=6)}",
                self.home,
                "Folder",
                lambda file: self.manager.create_folder(file),
            )

    def tearDown(self):
        directory = self.manager.get_local_path(self.folder.file_url)
        if directory.is_dir() and self.folder.file_name in str(directory):
            shutil.rmtree(directory)
        frappe.flags.mute_drive_activity_log = False
        super().tearDown()

    def row(self, file_name, content=b"twelve bytes", on_disk=True, known=True, **fields):
        """A file of the test folder: its file on the disk or not; its SHA-256 known, or `unreadable` (the checksum job's
        mark for a file it could not read)."""
        with self.set_user(OWNER):
            doc = create_drive_file(
                file_name,
                self.folder.name,
                "Text",
                f"{self.folder.file_url}{frappe.generate_hash(length=8)}-{file_name}",
                "text/plain",
                len(content),
            )
        if on_disk:
            path = self.manager.get_local_path(doc.file_url)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        stamp = {"content_hash": hashlib.sha256(content).hexdigest() if known else "unreadable", **fields}
        frappe.db.set_value("File", doc.name, stamp, update_modified=False)
        return doc.name

    def status(self, name):
        return frappe.db.get_value("File", name, "status")

    def test_a_row_without_its_file_goes_to_the_trash_when_its_twin_holds_it(self):
        twin = self.row("race.xlsx")
        ghost = self.row("race.xlsx", on_disk=False, known=False)

        done = sweep(only=[twin, ghost])

        self.assertEqual(done, {"trashed": [ghost], "lone": []})
        self.assertEqual(self.status(ghost), STATUS_TRASHED)
        self.assertEqual(self.status(twin), STATUS_ACTIVE)
        # the twin keeps its content
        twin_url = frappe.db.get_value("File", twin, "file_url")
        self.assertEqual(self.manager.get_local_path(twin_url).read_bytes(), b"twelve bytes")

    def test_a_row_without_its_file_and_without_a_twin_is_only_named(self):
        alone = self.row("alone.xlsx", on_disk=False)
        # a row of the same name and size made long before is not a twin
        older = self.row("late.xlsx")
        late = self.row("late.xlsx", on_disk=False)
        frappe.db.set_value(
            "File",
            older,
            "creation",
            frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=-5),
            update_modified=False,
        )
        # nor one of the same name and size whose content is known to differ
        other = self.row("other.xlsx", content=b"other bytes!")
        different = self.row("other.xlsx", content=b"other bytes?", on_disk=False)

        done = sweep(only=[alone, older, late, other, different])

        self.assertEqual(done["trashed"], [])
        self.assertCountEqual(done["lone"], [alone, late, different])
        for name in (alone, older, late, other, different):
            self.assertEqual(self.status(name), STATUS_ACTIVE)
        logged = frappe.get_all(
            "Error Log",
            filters={"method": "Drive: rows without content"},
            fields=["error"],
            order_by="creation desc",
            limit=1,
        )
        self.assertIn(alone, logged[0].error)

    def test_an_attachment_of_a_document_is_never_looked_at(self):
        twin = self.row("scan.pdf")
        ghost = self.row("scan.pdf", on_disk=False, attached_to_doctype="User", attached_to_name=OWNER)

        done = sweep(only=[twin, ghost])

        self.assertEqual(done, {"trashed": [], "lone": []})
        self.assertEqual(self.status(ghost), STATUS_ACTIVE)

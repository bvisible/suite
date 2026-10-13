# //// Neoffice — added file (no upstream equivalent). A rename moves the bytes and the row together: the storage
# //// key went into file_url as a pathlib.Path, the save raised under frappe v15 after the bytes had moved, and the
# //// row kept a url with nothing behind it. And whoever the Drive lets write a row renames or trashes it, owner or
# //// not: frappe's role rule on File (« All » writes only its own Files, as on osiris) judged the save again.
from __future__ import annotations

import shutil

import frappe
from frappe.tests import IntegrationTestCase

from suite.drive.api.files import remove_or_restore
from suite.drive.utils import STATUS_ACTIVE, STATUS_TRASHED, create_drive_file, get_user_folder
from suite.drive.utils.files import FileManager
from suite.tests.utils import ensure_user


class TestRenameKeepsRowAndBytesTogether(IntegrationTestCase):
    def setUp(self):
        frappe.flags.mute_drive_activity_log = True
        self.manager = manager = FileManager()
        if manager.flat or manager.s3_enabled:
            self.skipTest("a rename moves bytes only in a tree on disk")
        self.prefix = f"rename-{frappe.generate_hash(length=6)}"
        home = get_user_folder()
        self.home = manager.get_local_path(frappe.db.get_value("File", home.name, "file_url"))
        self.folder = create_drive_file(self.prefix, home.name, "Folder", lambda f: manager.create_folder(f))

    def tearDown(self):
        frappe.flags.mute_drive_activity_log = False
        for path in self.home.glob(f"{self.prefix}*"):
            shutil.rmtree(path, ignore_errors=True)
        super().tearDown()

    def _file(self, file_name):
        manager = self.manager
        row = create_drive_file(
            file_name,
            self.folder.name,
            "Text",
            lambda f: "/" + str(manager.get_disk_path(f)),
            "text/plain",
            5,
        )
        path = manager.get_local_path(row.file_url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"hello")
        return row.name

    def test_a_renamed_file_keeps_its_bytes_under_its_url(self):
        name = self._file("before.txt")
        before = self.manager.get_local_path(frappe.db.get_value("File", name, "file_url"))

        doc = frappe.get_doc("File", name)
        doc.rename("after.txt")

        # what the save serialises (its Version row): a Path made it raise under frappe v15
        self.assertIsInstance(doc.file_url, str)
        frappe.as_json(doc.as_dict())
        row = frappe.get_doc("File", name)
        self.assertEqual(row.file_name, "after.txt")
        self.assertTrue(self.manager.get_local_path(row.file_url).is_file(), row.file_url)
        self.assertFalse(before.exists())

    def test_a_renamed_folder_takes_its_files_along(self):
        name = self._file("inside.txt")

        folder = frappe.get_doc("File", self.folder.name)
        folder.rename(f"{self.prefix} renamed")

        self.assertIsInstance(folder.file_url, str)
        folder = frappe.get_doc("File", self.folder.name)
        self.assertTrue(folder.file_url.endswith("/"), folder.file_url)
        self.assertTrue(self.manager.get_local_path(folder.file_url).is_dir())
        inside = frappe.get_doc("File", name)
        self.assertTrue(self.manager.get_local_path(inside.file_url).is_file(), inside.file_url)

    def test_whoever_may_write_a_row_renames_and_trashes_it_without_owning_it(self):
        name = self._file("shared.txt")
        writer = f"drive-writer-{frappe.generate_hash(length=6)}@example.com"
        ensure_user(writer)
        frappe.get_doc(
            {"doctype": "Drive Permission", "entity": self.folder.name, "user": writer, "read": 1, "write": 1}
        ).insert(ignore_permissions=True)

        with self.set_user(writer):
            frappe.get_doc("File", name).rename("shared-renamed.txt")
            remove_or_restore([name])
        self.assertEqual(
            frappe.db.get_value("File", name, ["file_name", "status"]), ("shared-renamed.txt", STATUS_TRASHED)
        )

        with self.set_user(writer):
            remove_or_restore([name])
        self.assertEqual(frappe.db.get_value("File", name, "status"), STATUS_ACTIVE)

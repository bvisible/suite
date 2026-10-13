# //// Neoffice — added file (no upstream equivalent). The `Projects` root, and the upload right a
# //// folder takes from the document it is attached to: a project's folder is filled by whoever may
# //// write the project (neoffice_activity/project_drive.py).
from __future__ import annotations

import shutil
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from suite.drive.api.permissions import get_user_access_for_user
from suite.drive.utils import PROJECTS_FOLDER, ROOT_FOLDER, create_drive_file, get_projects_folder
from suite.drive.utils.files import FileManager, storage_key
from suite.tests.utils import ensure_user


class TestProjectsFolder(IntegrationTestCase):
    def setUp(self):
        frappe.flags.mute_drive_activity_log = True
        suffix = frappe.generate_hash(length=6)
        self.writer = f"projects-writer-{suffix}@example.com"
        self.reader = f"projects-reader-{suffix}@example.com"
        self.stranger = f"projects-stranger-{suffix}@example.com"
        for user in (self.writer, self.reader, self.stranger):
            ensure_user(user)
        self.todo = frappe.get_doc({"doctype": "ToDo", "description": "a document with a folder"}).insert(
            ignore_permissions=True
        )
        manager = FileManager()
        self.folder = create_drive_file(
            f"projects-folder-{suffix}",
            get_projects_folder().name,
            "Folder",
            lambda file: manager.create_folder(file),
            owner="Administrator",
        )
        self.folder.db_set({"attached_to_doctype": "ToDo", "attached_to_name": self.todo.name})

    def tearDown(self):
        frappe.flags.mute_drive_activity_log = False
        if self.folder.file_url:
            shutil.rmtree(FileManager().site_folder / storage_key(self.folder.file_url), ignore_errors=True)
        super().tearDown()

    def _access(self, user):
        """The folder's access for `user`, who may write the document (writer), only read it
        (reader) or neither (stranger)."""
        rights = {self.writer: ("read", "write"), self.reader: ("read",)}

        def has_permission(doctype, ptype="read", doc=None, user=None, **kwargs):
            return ptype in rights.get(user, ())

        with patch("suite.drive.api.permissions.frappe.has_permission", side_effect=has_permission):
            return get_user_access_for_user(frappe.get_doc("File", self.folder.name), user)

    def test_the_root_stands_beside_drive_and_carries_no_grant(self):
        root = get_projects_folder()
        self.assertEqual(root.name, PROJECTS_FOLDER)
        self.assertEqual(get_projects_folder().name, root.name)
        row = frappe.db.get_value("File", root.name, ["folder", "owner", "is_folder"], as_dict=True)
        self.assertFalse(row.folder)
        self.assertNotEqual(root.name, ROOT_FOLDER)
        self.assertEqual(row.owner, "Administrator")
        self.assertTrue(row.is_folder)
        self.assertFalse(frappe.db.exists("Drive Permission", {"entity": root.name}))

    def test_whoever_may_write_the_document_may_fill_its_folder(self):
        access = self._access(self.writer)
        self.assertEqual((access["read"], access["upload"], access["write"]), (1, 1, 1))
        self.assertEqual(access["share"], 0)

    def test_a_reader_of_the_document_reads_its_folder_and_adds_nothing(self):
        access = self._access(self.reader)
        self.assertEqual((access["read"], access["upload"], access["write"]), (1, 0, 0))

    def test_the_folder_is_closed_to_whoever_cannot_read_the_document(self):
        # Under `Drive`, the root's $GENERAL row would have let this user read it.
        access = self._access(self.stranger)
        self.assertEqual((access["read"], access["upload"], access["write"]), (0, 0, 0))

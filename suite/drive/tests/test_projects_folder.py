# //// Neoffice — added file (no upstream equivalent). The `Projects` root, the upload right a folder
# //// takes from the document it is attached to, and the access it lends to all it holds: a project's
# //// folder is read by whoever reads the project and filled by whoever writes it
# //// (neoffice_activity/project_drive.py), in the Drive and over WebDAV.
from __future__ import annotations

import shutil
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from suite.drive.api.permissions import get_user_access_for_user
from suite.drive.utils import (
    PROJECTS_FOLDER,
    ROOT_FOLDER,
    create_drive_file,
    generate_upward_path,
    get_projects_folder,
)
from suite.drive.utils.files import FileManager, storage_key
from suite.drive.webdav import perms
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
        # below it, nothing attached: a folder and a file in it, as anyone adds them
        self.below = create_drive_file(
            f"below-{suffix}", self.folder.name, "Folder", lambda file: manager.create_folder(file)
        )
        self.file = create_drive_file(
            f"note-{suffix}.txt",
            self.below.name,
            "Text",
            f"{self.below.file_url}note-{suffix}.txt",
            "text/plain",
            5,
        )

    def tearDown(self):
        frappe.flags.mute_drive_activity_log = False
        if self.folder.file_url:
            shutil.rmtree(FileManager().site_folder / storage_key(self.folder.file_url), ignore_errors=True)
        super().tearDown()

    def _rights(self):
        """`user` may write the document (writer), only read it (reader) or neither (stranger)."""
        rights = {self.writer: ("read", "write"), self.reader: ("read",)}

        def has_permission(doctype, ptype="read", doc=None, user=None, **kwargs):
            return ptype in rights.get(user, ())

        return patch("suite.drive.api.permissions.frappe.has_permission", side_effect=has_permission)

    def _access(self, user, name=None):
        with self._rights():
            return get_user_access_for_user(frappe.get_doc("File", name or self.folder.name), user)

    def _bits(self, access):
        return (access["read"], access["upload"], access["write"])

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

    def test_the_root_reads_in_the_sites_language(self):
        get_projects_folder()
        label = frappe._(PROJECTS_FOLDER, lang=frappe.db.get_default("lang") or "en")
        self.assertEqual(frappe.db.get_value("File", PROJECTS_FOLDER, "file_name"), label)

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

    def test_what_lies_below_the_folder_takes_the_documents_access(self):
        for name in (self.below.name, self.file.name):
            self.assertEqual(self._bits(self._access(self.writer, name)), (1, 1, 1), name)
            self.assertEqual(self._bits(self._access(self.reader, name)), (1, 0, 0), name)
            self.assertEqual(self._bits(self._access(self.stranger, name)), (0, 0, 0), name)

    def test_a_row_nearer_than_the_document_still_decides(self):
        frappe.get_doc(
            {
                "doctype": "Drive Permission",
                "entity": self.below.name,
                "user": self.reader,
                "deny": 1,
                "read": 1,
            }
        ).insert(ignore_permissions=True)
        self.assertEqual(self._access(self.reader, self.file.name)["read"], 0)
        self.assertEqual(self._access(self.reader, self.folder.name)["read"], 1)

    def test_webdav_lists_below_the_folder_as_the_drive_does(self):
        children = [frappe._dict(frappe.get_doc("File", self.file.name).as_dict())]
        below = frappe._dict(frappe.get_doc("File", self.below.name).as_dict())
        with self._rights():
            for user, bits in (
                (self.writer, (1, 1, 1)),
                (self.reader, (1, 0, 0)),
                (self.stranger, (0, 0, 0)),
            ):
                listed = perms.resolve_children_access(
                    generate_upward_path(self.below.name, user), children, user
                )
                self.assertEqual(self._bits(listed[self.file.name]), bits, user)
                folder = perms.parent_access(generate_upward_path(self.below.name, user), below, user)
                self.assertEqual(self._bits(folder), bits, user)

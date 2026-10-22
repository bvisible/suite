# //// Neoffice — added file (no upstream equivalent): a row that leaves the Drive's tree (trash, deletion) gives up its
# //// url there (maintenance#1820, FileManager.get_trash_url). It kept its folder's path and its name, and the next file
# //// of that name in that folder got the same url: frappe's check on private files (validate_private_file_access)
# //// refused it as a row reaching another owner's bytes, « You don't have permission to access this file ». That check
# //// is meant to stay: a row aimed at another owner's bytes, in the tree or in the trash, is still refused.
from __future__ import annotations

import shutil
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from werkzeug.test import EnvironBuilder
from werkzeug.utils import secure_filename
from werkzeug.wrappers import Request

from suite.drive.api.files import (
    create_folder,
    delete_entities,
    get_upload_path,
    remove_or_restore,
    upload_file,
)
from suite.drive.patches.rows_out_of_the_tree_release_their_url import release
from suite.drive.utils import (
    STATUS_ACTIVE,
    STATUS_REMOVED,
    STATUS_TRASHED,
    create_drive_file,
    get_user_folder,
)
from suite.drive.utils.files import FileManager, storage_key
from suite.tests.utils import ensure_user

OWNER = "drive-out-of-tree-owner@example.com"
COLLEAGUE = "drive-out-of-tree-colleague@example.com"
REFUSAL = "You don't have permission to access this file"


class TestRowsOutOfTheTreeGiveUpTheirUrl(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for user in (OWNER, COLLEAGUE):
            ensure_user(user)
        with cls.set_user(OWNER):
            cls.home = get_user_folder(OWNER).name
        # an upload commits (hold_folder_names): what it relies on is committed first
        frappe.db.commit()

    def setUp(self):
        self.manager = manager = FileManager()
        if manager.flat:
            self.skipTest("only the tree layout gives a row its place by its folder and its name")
        frappe.flags.mute_drive_activity_log = True
        with self.set_user(OWNER):
            self.folder = create_drive_file(
                f"OutOfTree-{frappe.generate_hash(length=6)}",
                self.home,
                "Folder",
                lambda file: manager.create_folder(file),
            )
        # the folder is shared: the colleague may read, drop files and write in it
        frappe.get_doc(
            {
                "doctype": "Drive Permission",
                "entity": self.folder.name,
                "user": COLLEAGUE,
                "read": 1,
                "upload": 1,
                "write": 1,
            }
        ).insert(ignore_permissions=True)
        frappe.db.commit()

    def tearDown(self):
        frappe.db.rollback()
        frappe.set_user("Administrator")
        names = self.subtree(self.folder.name)
        for name in names:
            trashed = self.manager.site_folder / self.manager.get_trash_path(frappe._dict(name=name))
            if trashed.is_dir():
                shutil.rmtree(trashed)
            else:
                trashed.unlink(missing_ok=True)
        directory = self.manager.get_local_path(self.folder.file_url)
        if directory.is_dir() and self.folder.file_name in str(directory):
            shutil.rmtree(directory)
        frappe.db.delete("Drive Permission", {"entity": ("in", names)})
        frappe.db.delete("File", {"name": ("in", names)})
        frappe.db.commit()
        frappe.flags.mute_drive_activity_log = False
        super().tearDown()

    def subtree(self, name: str) -> list[str]:
        names = [name]
        for child in frappe.get_all("File", filters={"folder": name}, pluck="name"):
            names += self.subtree(child)
        return names

    def upload(self, user: str, content: bytes, file_name: str = "devis.pdf", parent: str | None = None):
        """A file dropped through the Drive's upload endpoint, by `user`, into the shared folder or `parent`."""
        builder = EnvironBuilder(
            path="/api/method/suite.drive.api.files.upload_file",
            method="POST",
            data={"file": (BytesIO(content), file_name)},
        )
        frappe.local.request = Request(builder.get_environ())
        values = {"uuid": frappe.generate_hash(length=12), "chunk_index": ""}
        try:
            with (
                self.set_user(user),
                patch("suite.drive.api.files.validate_quota"),
                patch("suite.drive.api.files.frappe.publish_realtime"),
                # these bytes are no PDF: no thumbnail is tried
                patch.object(FileManager, "can_create_thumbnail", return_value=False),
            ):
                # after set_user, which empties the form
                frappe.form_dict.update(values)
                uploaded = upload_file(total_file_size=len(content), parent=parent or self.folder.name)
            # the end of the request
            frappe.db.commit()
            return uploaded
        finally:
            for key in values:
                frappe.form_dict.pop(key, None)
            del frappe.local.request
            # a refused upload leaves its staging file behind
            get_upload_path(f"{values['uuid']}_{secure_filename(file_name)}").unlink(missing_ok=True)

    def content(self, name: str) -> bytes:
        """The bytes a row's url names."""
        with self.manager.get_file(frappe.get_doc("File", name)) as stored:
            return stored.read()

    def tree_path(self, file_name: str, folder=None) -> Path:
        folder = folder or self.folder
        return Path(storage_key(frappe.db.get_value("File", folder.name, "file_url"))) / file_name

    def make_folder(self, user: str, file_name: str):
        with self.set_user(user):
            folder = create_folder(file_name, parent=self.folder.name)
        frappe.db.commit()
        return folder

    def test_a_file_dropped_under_the_name_of_a_colleagues_trashed_file_is_taken(self):
        mine = self.upload(OWNER, b"the owner's quote")
        with self.set_user(OWNER):
            remove_or_restore([mine.name])

        theirs = self.upload(COLLEAGUE, b"the colleague's quote")

        self.assertEqual(theirs.file_name, "devis.pdf")
        self.assertEqual(Path(storage_key(theirs.file_url)), self.tree_path("devis.pdf"))
        self.assertEqual(self.content(theirs.name), b"the colleague's quote")
        # the trashed row holds its place in the trash, where its bytes are
        trashed = frappe.get_doc("File", mine.name)
        self.assertEqual(trashed.status, STATUS_TRASHED)
        self.assertEqual(trashed.file_url, self.manager.get_trash_url(trashed))
        self.assertEqual(self.content(mine.name), b"the owner's quote")

    def test_a_file_dropped_under_the_name_of_a_colleagues_deleted_file_is_taken(self):
        for through_trash in (True, False):
            with self.subTest(through_trash=through_trash):
                file_name = f"devis-{int(through_trash)}.pdf"
                mine = self.upload(OWNER, b"the owner's quote", file_name)
                with self.set_user(OWNER):
                    if through_trash:
                        remove_or_restore([mine.name])
                    delete_entities([mine.name])
                # its bytes are deleted once the deletion is committed
                frappe.db.commit()
                removed = frappe.get_doc("File", mine.name)
                self.assertEqual(removed.status, STATUS_REMOVED)
                self.assertEqual(removed.file_url, self.manager.get_trash_url(removed))
                self.assertFalse((self.manager.site_folder / self.tree_path(file_name)).exists())
                self.assertFalse((self.manager.site_folder / self.manager.get_trash_path(removed)).exists())

                theirs = self.upload(COLLEAGUE, b"the colleague's quote", file_name)

                self.assertEqual(theirs.file_name, file_name)
                self.assertEqual(Path(storage_key(theirs.file_url)), self.tree_path(file_name))
                self.assertEqual(self.content(theirs.name), b"the colleague's quote")

    def test_a_row_aimed_at_a_colleagues_private_bytes_is_still_refused(self):
        mine = self.upload(OWNER, b"the owner's private quote")

        # an Active file, by frappe's own File and by the Drive's (the other spellings of a url: test_private_file_urls)
        with self.set_user(COLLEAGUE), self.assertRaisesRegex(frappe.PermissionError, REFUSAL):
            frappe.get_doc(
                {"doctype": "File", "file_name": "copy.pdf", "file_url": mine.file_url, "is_private": 1}
            ).insert(ignore_permissions=True)
        frappe.db.rollback()
        with self.set_user(COLLEAGUE), self.assertRaisesRegex(frappe.PermissionError, REFUSAL):
            create_drive_file("copy.pdf", self.folder.name, "PDF", mine.file_url, "application/pdf", 1)
        frappe.db.rollback()

        # a trashed file: its bytes are still there, in the trash, under its url
        with self.set_user(OWNER):
            remove_or_restore([mine.name])
        frappe.db.commit()
        trash_url = frappe.db.get_value("File", mine.name, "file_url")
        self.assertEqual(self.content(mine.name), b"the owner's private quote")
        for url in (trash_url, "/" + trash_url):
            with (
                self.subTest(url=url),
                self.set_user(COLLEAGUE),
                self.assertRaisesRegex(frappe.PermissionError, REFUSAL),
            ):
                create_drive_file("copy.pdf", self.folder.name, "PDF", url, "application/pdf", 1)
            frappe.db.rollback()
        with self.set_user(COLLEAGUE), self.assertRaisesRegex(frappe.PermissionError, REFUSAL):
            frappe.get_doc(
                {"doctype": "File", "file_name": "copy.pdf", "file_url": "/" + trash_url, "is_private": 1}
            ).insert(ignore_permissions=True)

    def test_a_restore_next_to_the_newcomer_keeps_the_two_files_apart(self):
        mine = self.upload(OWNER, b"the owner's quote")
        with self.set_user(OWNER):
            remove_or_restore([mine.name])
        theirs = self.upload(COLLEAGUE, b"the colleague's quote")

        with self.set_user(OWNER):
            remove_or_restore([mine.name])

        restored = frappe.get_doc("File", mine.name)
        self.assertEqual((restored.status, restored.file_name), (STATUS_ACTIVE, "devis (1).pdf"))
        self.assertEqual(Path(storage_key(restored.file_url)), self.tree_path("devis (1).pdf"))
        self.assertEqual(self.content(mine.name), b"the owner's quote")
        self.assertEqual(self.content(theirs.name), b"the colleague's quote")
        self.assertFalse((self.manager.site_folder / self.manager.get_trash_path(restored)).exists())

    def test_a_file_moved_next_to_a_colleagues_file_of_its_name_takes_a_free_name(self):
        # the name was looked for through the permission filters, which leave out a colleague's file readable through
        # the shared folder only: the move took the colleague's name, and its bytes moved over the colleague's
        theirs = self.upload(COLLEAGUE, b"the colleague's quote")
        elsewhere = self.make_folder(OWNER, "Ailleurs")
        mine = self.upload(OWNER, b"the owner's quote", parent=elsewhere.name)

        with self.set_user(OWNER):
            frappe.get_doc("File", mine.name).move(self.folder.name)

        moved = frappe.get_doc("File", mine.name)
        self.assertEqual(moved.file_name, "devis (1).pdf")
        self.assertEqual(self.content(mine.name), b"the owner's quote")
        self.assertEqual(self.content(theirs.name), b"the colleague's quote")

    def test_a_restore_without_a_newcomer_goes_back_to_its_place(self):
        mine = self.upload(OWNER, b"the plan", "plan.pdf")
        with self.set_user(OWNER):
            remove_or_restore([mine.name])
            remove_or_restore([mine.name])

        restored = frappe.get_doc("File", mine.name)
        self.assertEqual((restored.status, restored.file_name), (STATUS_ACTIVE, "plan.pdf"))
        self.assertEqual(Path(storage_key(restored.file_url)), self.tree_path("plan.pdf"))
        self.assertEqual(self.content(mine.name), b"the plan")

    def test_the_files_of_a_trashed_folder_follow_it_and_come_back_apart_from_the_newcomers(self):
        projects = self.make_folder(OWNER, "Projets")
        mine = self.upload(OWNER, b"the owner's plan", "plan.pdf", parent=projects.name)
        with self.set_user(OWNER):
            remove_or_restore([projects.name])

        trashed = frappe.get_doc("File", projects.name)
        self.assertEqual(trashed.file_url, self.manager.get_trash_url(trashed))
        inside = frappe.get_doc("File", mine.name)
        self.assertEqual(
            Path(storage_key(inside.file_url)), self.manager.get_trash_path(trashed) / "plan.pdf"
        )
        self.assertEqual(self.content(mine.name), b"the owner's plan")

        # the colleague makes the folder again and drops the same name in it
        again = self.make_folder(COLLEAGUE, "Projets")
        theirs = self.upload(COLLEAGUE, b"the colleague's plan", "plan.pdf", parent=again.name)
        self.assertEqual(Path(storage_key(theirs.file_url)), self.tree_path("plan.pdf", again))

        with self.set_user(OWNER):
            remove_or_restore([projects.name])

        restored = frappe.get_doc("File", projects.name)
        self.assertEqual((restored.status, restored.file_name), (STATUS_ACTIVE, "Projets (1)"))
        inside = frappe.get_doc("File", mine.name)
        self.assertEqual(Path(storage_key(inside.file_url)), self.tree_path("plan.pdf", restored))
        self.assertEqual(self.content(mine.name), b"the owner's plan")
        self.assertEqual(self.content(theirs.name), b"the colleague's plan")

    def test_emptying_a_trashed_folder_leaves_the_file_that_took_its_place(self):
        # the same owner, whom frappe's check never stopped: deleting the old folder for good deleted its files at
        # their old urls, which the new folder's files had taken
        archive = self.make_folder(OWNER, "Archive")
        old = self.upload(OWNER, b"old", "a.pdf", parent=archive.name)
        with self.set_user(OWNER):
            remove_or_restore([archive.name])
        again = self.make_folder(OWNER, "Archive")
        new = self.upload(OWNER, b"new", "a.pdf", parent=again.name)

        with self.set_user(OWNER):
            delete_entities([archive.name])
        frappe.db.commit()

        self.assertEqual(frappe.db.get_value("File", old.name, "status"), STATUS_REMOVED)
        self.assertEqual(self.content(new.name), b"new")
        self.assertFalse(
            (self.manager.site_folder / self.manager.get_trash_path(frappe._dict(name=archive.name))).exists()
        )

    def test_the_patch_releases_the_urls_of_the_rows_that_left_the_tree_before(self):
        # rows trashed or deleted before the fix: they hold their place in the tree
        loose = self.upload(OWNER, b"the owner's quote")
        projects = self.make_folder(OWNER, "Projets")
        inside = self.upload(OWNER, b"the owner's plan", "plan.pdf", parent=projects.name)
        gone = self.upload(OWNER, b"gone", "gone.pdf")
        legacy = {
            name: frappe.db.get_value("File", name, "file_url")
            for name in (loose.name, projects.name, inside.name, gone.name)
        }
        with self.set_user(OWNER):
            remove_or_restore([loose.name, projects.name])
            delete_entities([gone.name])
        frappe.db.commit()
        for name, url in legacy.items():
            frappe.db.set_value("File", name, "file_url", url, update_modified=False)
        frappe.db.commit()

        # before: the colleague's file of the same name is refused
        with self.assertRaisesRegex(frappe.PermissionError, REFUSAL):
            self.upload(COLLEAGUE, b"the colleague's quote")
        frappe.db.rollback()

        modified = frappe.db.get_value("File", gone.name, "modified")
        counts = release(only=list(legacy))

        self.assertEqual(counts, {"trashed": 2, "removed": 1, "followed": 1})
        for name in (loose.name, projects.name, gone.name):
            row = frappe.get_doc("File", name)
            self.assertEqual(row.file_url, self.manager.get_trash_url(row), name)
        self.assertEqual(
            Path(storage_key(frappe.db.get_value("File", inside.name, "file_url"))),
            self.manager.get_trash_path(frappe._dict(name=projects.name)) / "plan.pdf",
        )
        self.assertEqual(self.content(loose.name), b"the owner's quote")
        self.assertEqual(self.content(inside.name), b"the owner's plan")
        # the purge of a deleted row is timed by `modified`: left as it was
        self.assertEqual(frappe.db.get_value("File", gone.name, "modified"), modified)
        # once is enough
        self.assertEqual(release(only=list(legacy)), {"trashed": 0, "removed": 0, "followed": 0})
        frappe.db.commit()

        theirs = self.upload(COLLEAGUE, b"the colleague's quote")
        self.assertEqual(theirs.file_name, "devis.pdf")
        with self.set_user(OWNER):
            remove_or_restore([projects.name])
        self.assertEqual(self.content(inside.name), b"the owner's plan")

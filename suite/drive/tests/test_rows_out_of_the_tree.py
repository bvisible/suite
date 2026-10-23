# //// Neoffice — added file (no upstream equivalent): a row that leaves the Drive's tree (trash, deletion) gives up its
# //// url there (maintenance#1820, FileManager.get_trash_url). It kept its folder's path and its name, and the next file
# //// of that name in that folder got the same url: frappe's check on private files (the fork's)
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
    create_link,
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
from suite.drive.utils.files import FileManager, repoint_descendants, storage_key
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
        self.planted = []
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
        for path in self.planted:
            path.unlink(missing_ok=True)
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
        # one row a batch: every page and every write of the patch is gone through
        counts = release(only=list(legacy), batch=1)

        self.assertEqual(counts, {"trashed": 2, "removed": 1, "followed": 1, "failed": 0})
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
        self.assertEqual(release(only=list(legacy)), {"trashed": 0, "removed": 0, "followed": 0, "failed": 0})
        frappe.db.commit()

        theirs = self.upload(COLLEAGUE, b"the colleague's quote")
        self.assertEqual(theirs.file_name, "devis.pdf")
        with self.set_user(OWNER):
            remove_or_restore([projects.name])
        self.assertEqual(self.content(inside.name), b"the owner's plan")

    def test_a_name_handed_out_is_free_even_when_numbers_were_skipped(self):
        # upstream numbered « title (n) » by how many names looked alike: with « x.pdf » and « x (2).pdf » in the
        # folder, the next « x.pdf » got « x (2).pdf », taken, and a move or a restore went over its bytes
        first = self.upload(COLLEAGUE, b"first", "x.pdf")
        second = self.upload(COLLEAGUE, b"second", "x (2).pdf")
        elsewhere = self.make_folder(OWNER, "Ailleurs-x")
        mine = self.upload(OWNER, b"mine", "x.pdf", parent=elsewhere.name)

        with self.set_user(OWNER):
            frappe.get_doc("File", mine.name).move(self.folder.name)
        frappe.db.commit()

        self.assertEqual(frappe.db.get_value("File", mine.name, "file_name"), "x (3).pdf")
        for name, content in ((first.name, b"first"), (second.name, b"second"), (mine.name, b"mine")):
            self.assertEqual(self.content(name), content)

    def test_a_folder_moved_next_to_a_folder_of_its_name_is_renamed_and_nothing_mixes(self):
        # upstream compared folders by a type that matched no row: the moved folder went inside the other one on the
        # disk while the rows kept the urls of the other one's files
        theirs = self.make_folder(COLLEAGUE, "Docs")
        their_file = self.upload(COLLEAGUE, b"their doc", "a.pdf", parent=theirs.name)
        holder = self.make_folder(OWNER, "Holder")
        with self.set_user(OWNER):
            mine = create_folder("Docs", parent=holder.name)
        frappe.db.commit()
        my_file = self.upload(OWNER, b"my doc", "a.pdf", parent=mine.name)

        with self.set_user(OWNER):
            frappe.get_doc("File", mine.name).move(self.folder.name)
        frappe.db.commit()

        self.assertEqual(frappe.db.get_value("File", mine.name, "file_name"), "Docs (1)")
        self.assertEqual(self.content(my_file.name), b"my doc")
        self.assertEqual(self.content(their_file.name), b"their doc")

    def test_a_move_never_lands_on_bytes_already_there(self):
        mine = self.upload(OWNER, b"mine", "here.pdf")
        # bytes that no Active row names, at the place the move would take
        orphan = self.manager.site_folder / self.tree_path("there.pdf")
        orphan.write_bytes(b"not mine")
        try:
            with (
                self.set_user(OWNER),
                self.assertRaisesRegex(frappe.ValidationError, "A file is already there"),
            ):
                self.manager.move(frappe.get_doc("File", mine.name), str(self.tree_path("there.pdf")))
            self.assertEqual(orphan.read_bytes(), b"not mine")
            self.assertEqual(self.content(mine.name), b"mine")
        finally:
            orphan.unlink(missing_ok=True)

    def test_a_restore_onto_bytes_already_there_takes_a_free_place(self):
        # an adopted framework upload keeps frappe's url (/private/files/<name>) while trashed; a framework upload of that
        # name, made meanwhile, wrote its bytes there: upstream's restore moved the trashed bytes over them
        file_name = f"{self.folder.file_name}-adopted.pdf"
        kept_url = f"/private/files/{file_name}"
        kept = self.manager.site_folder / storage_key(kept_url)
        self.planted.append(kept)
        with self.set_user(OWNER):
            adopted = create_drive_file(file_name, self.folder.name, "PDF", kept_url, "application/pdf", 7)
        kept.write_bytes(b"adopted")
        frappe.db.commit()
        with self.set_user(OWNER):
            remove_or_restore([adopted.name])
        frappe.db.commit()
        self.assertEqual(frappe.db.get_value("File", adopted.name, "file_url"), kept_url)
        self.assertFalse(kept.exists())
        kept.write_bytes(b"the newcomer's")

        with self.set_user(OWNER):
            remove_or_restore([adopted.name])
        frappe.db.commit()

        restored = frappe.get_doc("File", adopted.name)
        self.assertEqual((restored.status, restored.file_name), (STATUS_ACTIVE, file_name))
        self.assertEqual(Path(storage_key(restored.file_url)), self.tree_path(file_name))
        self.assertEqual(self.content(adopted.name), b"adopted")
        self.assertEqual(kept.read_bytes(), b"the newcomer's")

    def test_a_place_pointed_at_in_advance_does_not_receive_a_restored_file(self):
        # once the trashed row gave up its url, a colleague points a row of their own at that empty place; upstream's
        # order (bytes first, row after) put the owner's bytes under the colleague's row when the restore was refused
        mine = self.upload(OWNER, b"the owner's contract", "contrat.pdf")
        place = Path(storage_key(mine.file_url))
        theirs = self.upload(COLLEAGUE, b"the colleague's note", "note.txt")
        with self.set_user(OWNER):
            remove_or_restore([mine.name])
        frappe.db.commit()
        with self.set_user(COLLEAGUE):
            frappe.client.set_value("File", theirs.name, "file_url", "/" + place.as_posix())
        frappe.db.commit()

        with self.set_user(OWNER):
            remove_or_restore([mine.name])
        frappe.db.commit()

        restored = frappe.get_doc("File", mine.name)
        self.assertEqual((restored.status, restored.file_name), (STATUS_ACTIVE, "contrat (1).pdf"))
        self.assertEqual(self.content(mine.name), b"the owner's contract")
        self.assertFalse((self.manager.site_folder / place).exists())
        with self.assertRaises(frappe.DoesNotExistError):
            self.content(theirs.name)

    def test_a_move_onto_a_place_another_row_names_is_refused_before_the_bytes_move(self):
        mine = self.upload(OWNER, b"the owner's", "here.pdf")
        theirs = self.upload(COLLEAGUE, b"the colleague's note", "note.txt")
        target = self.tree_path("there.pdf")
        with self.set_user(COLLEAGUE):
            frappe.client.set_value("File", theirs.name, "file_url", "/" + target.as_posix())
        frappe.db.commit()

        with self.set_user(OWNER), self.assertRaisesRegex(frappe.ValidationError, "A file is already there"):
            frappe.get_doc("File", mine.name).rename("there.pdf")
        frappe.db.rollback()

        self.assertEqual(self.content(mine.name), b"the owner's")
        self.assertFalse((self.manager.site_folder / target).exists())

    def test_a_file_restored_while_its_folder_is_in_the_trash_is_refused_before_anything_moves(self):
        projects = self.make_folder(OWNER, "Projets")
        inside = self.upload(OWNER, b"the plan", "plan.pdf", parent=projects.name)
        with self.set_user(OWNER):
            remove_or_restore([inside.name])
            remove_or_restore([projects.name])
        frappe.db.commit()

        with self.set_user(OWNER), self.assertRaisesRegex(frappe.ValidationError, "Restore its folder"):
            remove_or_restore([inside.name])
        frappe.db.rollback()
        trashed = frappe.get_doc("File", inside.name)
        self.assertEqual(trashed.status, STATUS_TRASHED)
        self.assertEqual(self.content(inside.name), b"the plan")

        # both at once, the file first in the list: the folder is restored first
        with self.set_user(OWNER):
            remove_or_restore([inside.name, projects.name])
        frappe.db.commit()
        self.assertEqual(frappe.db.get_value("File", projects.name, "status"), STATUS_ACTIVE)
        self.assertEqual(
            Path(storage_key(frappe.db.get_value("File", inside.name, "file_url"))),
            self.tree_path("plan.pdf", projects),
        )
        self.assertEqual(self.content(inside.name), b"the plan")

    def test_a_file_renamed_inside_a_trashed_folder_comes_back_with_its_bytes(self):
        projects = self.make_folder(OWNER, "Projets")
        inside = self.upload(OWNER, b"the plan", "ancien.pdf", parent=projects.name)
        with self.set_user(OWNER):
            remove_or_restore([projects.name])
        frappe.db.commit()

        with self.set_user(OWNER):
            frappe.get_doc("File", inside.name).rename("nouveau.pdf")
        frappe.db.commit()
        renamed = frappe.get_doc("File", inside.name)
        self.assertEqual(Path(storage_key(renamed.file_url)).name, "nouveau.pdf")
        self.assertEqual(self.content(inside.name), b"the plan")

        # then trashed itself, the folder restored, and the file restored
        with self.set_user(OWNER):
            remove_or_restore([inside.name])
            remove_or_restore([projects.name])
            remove_or_restore([inside.name])
        frappe.db.commit()
        self.assertEqual(
            Path(storage_key(frappe.db.get_value("File", inside.name, "file_url"))),
            self.tree_path("nouveau.pdf", projects),
        )
        self.assertEqual(self.content(inside.name), b"the plan")

    def test_nothing_is_dropped_into_a_trashed_folder(self):
        projects = self.make_folder(OWNER, "Projets")
        with self.set_user(OWNER):
            sub = create_folder("Sub", parent=projects.name)
            remove_or_restore([projects.name])
        frappe.db.commit()

        for parent in (projects.name, sub.name):
            with (
                self.subTest(parent=parent),
                self.assertRaisesRegex(frappe.ValidationError, "This folder is in the trash"),
            ):
                self.upload(COLLEAGUE, b"late", "late.pdf", parent=parent)
            frappe.db.rollback()

    def test_a_trashed_file_is_not_moved_and_a_rename_keeps_its_bytes_in_the_trash(self):
        mine = self.upload(OWNER, b"mine", "old-name.pdf")
        elsewhere = self.make_folder(OWNER, "Elsewhere")
        with self.set_user(OWNER):
            remove_or_restore([mine.name])
        frappe.db.commit()

        with self.set_user(OWNER), self.assertRaisesRegex(frappe.ValidationError, "Restore this file"):
            frappe.get_doc("File", mine.name).move(elsewhere.name)
        frappe.db.rollback()

        with self.set_user(OWNER):
            frappe.get_doc("File", mine.name).rename("new-name.pdf")
        frappe.db.commit()
        trashed = frappe.get_doc("File", mine.name)
        self.assertEqual(trashed.file_url, self.manager.get_trash_url(trashed))
        self.assertEqual(self.content(mine.name), b"mine")

        with self.set_user(OWNER):
            remove_or_restore([mine.name])
        frappe.db.commit()
        self.assertEqual(
            Path(storage_key(frappe.db.get_value("File", mine.name, "file_url"))),
            self.tree_path("new-name.pdf"),
        )
        self.assertEqual(self.content(mine.name), b"mine")

    def test_nothing_is_moved_into_a_trashed_folder(self):
        projects = self.make_folder(OWNER, "Projets")
        loose = self.upload(OWNER, b"loose", "loose.pdf")
        with self.set_user(OWNER):
            remove_or_restore([projects.name])
        frappe.db.commit()

        with (
            self.set_user(OWNER),
            self.assertRaisesRegex(frappe.ValidationError, "This folder is in the trash"),
        ):
            frappe.get_doc("File", loose.name).move(projects.name)
        frappe.db.rollback()
        self.assertEqual(self.content(loose.name), b"loose")
        self.assertEqual(
            Path(storage_key(frappe.db.get_value("File", loose.name, "file_url"))),
            self.tree_path("loose.pdf"),
        )

    def test_a_trash_tried_again_after_a_rollback_keeps_the_folders_files(self):
        # the first attempt moved the directory to the trash, then its transaction was rolled back: the row is Active on
        # its old url with nothing there. Upstream deleted the directory in the trash first, and the files were gone.
        projects = self.make_folder(OWNER, "Projets")
        inside = self.upload(OWNER, b"the plan", "plan.pdf", parent=projects.name)
        folder = frappe.get_doc("File", projects.name)
        self.manager.move_to_trash(folder)
        self.assertFalse(self.manager.get_local_path(folder.file_url).exists())

        with self.set_user(OWNER):
            remove_or_restore([projects.name])
        frappe.db.commit()

        self.assertEqual(frappe.db.get_value("File", projects.name, "status"), STATUS_TRASHED)
        self.assertEqual(self.content(inside.name), b"the plan")
        with self.set_user(OWNER):
            remove_or_restore([projects.name])
        frappe.db.commit()
        self.assertEqual(self.content(inside.name), b"the plan")

    def test_the_files_of_a_folder_follow_it_without_their_own_save(self):
        projects = self.make_folder(OWNER, "Projets")
        sub = None
        with self.set_user(OWNER):
            sub = create_folder("Sub", parent=projects.name)
        frappe.db.commit()
        deep = self.upload(OWNER, b"deep", "deep.pdf", parent=sub.name)
        modified = frappe.db.get_value("File", deep.name, "modified")
        old = frappe.db.get_value("File", projects.name, "file_url")

        moved = repoint_descendants(projects.name, old, "private/files/somewhere-else/")

        self.assertEqual(moved, 2)
        self.assertEqual(
            Path(storage_key(frappe.db.get_value("File", deep.name, "file_url"))),
            Path("private/files/somewhere-else/Sub/deep.pdf"),
        )
        self.assertTrue(frappe.db.get_value("File", sub.name, "file_url").endswith("/Sub/"))
        self.assertEqual(frappe.db.get_value("File", deep.name, "modified"), modified)
        frappe.db.rollback()

    def test_a_restore_holds_every_owners_storage_before_checking_it(self):
        # a deposit landing between the check of the storage and the restores would make a row refused half-way, after
        # the bytes of the ones before had moved; the deposit takes the same lock
        import suite.drive.api.files as files_api

        mine = self.upload(OWNER, b"mine", "a.pdf")
        theirs = self.upload(COLLEAGUE, b"theirs", "b.pdf")
        with self.set_user(OWNER):
            remove_or_restore([mine.name, theirs.name])
        frappe.db.commit()

        calls = []
        lock, quota = files_api.acquire_owner_storage_lock, files_api.validate_quota

        def locking(owner):
            calls.append(("lock", owner))
            return lock(owner)

        def checking(owner=None, incoming_size=0):
            calls.append(("quota", owner))
            return quota(owner, incoming_size)

        with (
            self.set_user(OWNER),
            patch.object(files_api, "acquire_owner_storage_lock", side_effect=locking),
            patch.object(files_api, "validate_quota", side_effect=checking),
        ):
            remove_or_restore([theirs.name, mine.name])
        frappe.db.commit()

        first_check = next(i for i, call in enumerate(calls) if call[0] == "quota")
        self.assertEqual([owner for kind, owner in calls[:first_check]], sorted([OWNER, COLLEAGUE]))
        self.assertEqual(frappe.db.get_value("File", mine.name, "status"), STATUS_ACTIVE)
        self.assertEqual(self.content(theirs.name), b"theirs")

    def test_a_restore_refused_for_the_storage_moves_nothing(self):
        import suite.drive.api.files as files_api

        first = self.upload(OWNER, b"first", "first.pdf")
        second = self.upload(OWNER, b"second", "second.pdf")
        with self.set_user(OWNER):
            remove_or_restore([first.name, second.name])
        frappe.db.commit()

        with (
            self.set_user(OWNER),
            patch.object(files_api, "validate_quota", side_effect=ValueError("You're out of storage!")),
            self.assertRaises(ValueError),
        ):
            remove_or_restore([first.name, second.name])
        frappe.db.rollback()

        for row, content in ((first, b"first"), (second, b"second")):
            trashed = frappe.get_doc("File", row.name)
            self.assertEqual(trashed.status, STATUS_TRASHED)
            self.assertEqual(trashed.file_url, self.manager.get_trash_url(trashed))
            self.assertEqual(self.content(row.name), content)

    def test_a_deleted_file_in_the_selection_is_refused_before_anything_moves(self):
        gone = self.upload(OWNER, b"gone", "gone.pdf")
        kept = self.upload(OWNER, b"kept", "kept.pdf")
        with self.set_user(OWNER):
            remove_or_restore([gone.name, kept.name])
            delete_entities([gone.name])
        frappe.db.commit()

        with (
            self.set_user(OWNER),
            self.assertRaisesRegex(frappe.DoesNotExistError, "This file has been deleted"),
        ):
            remove_or_restore([kept.name, gone.name])
        frappe.db.rollback()

        self.assertEqual(frappe.db.get_value("File", kept.name, "status"), STATUS_TRASHED)
        self.assertEqual(self.content(kept.name), b"kept")
        self.assertEqual(frappe.db.get_value("File", gone.name, "status"), STATUS_REMOVED)

    def test_a_name_that_differs_by_case_is_another_place_but_not_next_to_a_colleagues_file(self):
        # the column compares without case or accents, the disk does not
        mine = self.upload(OWNER, b"the small one", "rapport.pdf")
        with self.set_user(OWNER):
            remove_or_restore([mine.name])
        frappe.db.commit()
        big = self.upload(OWNER, b"the big one", "Rapport.pdf")

        with self.set_user(OWNER):
            remove_or_restore([mine.name])
        frappe.db.commit()

        self.assertEqual(frappe.db.get_value("File", mine.name, "file_name"), "rapport.pdf")
        self.assertEqual(self.content(mine.name), b"the small one")
        self.assertEqual(self.content(big.name), b"the big one")

        # next to a colleague's « Bilan.pdf », a « bilan.pdf » would be refused by frappe's check once its bytes had
        # moved (it compares the same way as the column): it takes a free name instead
        other = self.upload(OWNER, b"mine", "bilan.pdf")
        with self.set_user(OWNER):
            remove_or_restore([other.name])
        frappe.db.commit()
        theirs = self.upload(COLLEAGUE, b"theirs", "Bilan.pdf")
        with self.set_user(OWNER):
            remove_or_restore([other.name])
        frappe.db.commit()
        self.assertEqual(frappe.db.get_value("File", other.name, "file_name"), "bilan (1).pdf")
        self.assertEqual(self.content(other.name), b"mine")
        self.assertEqual(self.content(theirs.name), b"theirs")

    def test_the_place_lookup_sees_what_lies_below_and_keeps_a_folders_own_files(self):
        projects = self.make_folder(OWNER, "Projets")
        inside = self.upload(OWNER, b"inside", "plan.pdf", parent=projects.name)
        place = storage_key(frappe.db.get_value("File", projects.name, "file_url")).rstrip("/")

        self.assertFalse(self.manager.named_by_another_row(place, projects.name))
        self.assertTrue(self.manager.named_by_another_row(place, None))

        # the LIKE wildcards of a name are taken literally: « a_b » is not « aXb », whose file is a colleague's
        axb = self.make_folder(COLLEAGUE, "aXb")
        self.upload(COLLEAGUE, b"theirs", "x.pdf", parent=axb.name)
        sibling = Path(storage_key(self.folder.file_url)) / "a_b"
        with self.set_user(OWNER):
            self.assertFalse(self.manager.named_by_another_row(sibling, None))

        # a colleague's row pointed under the place is another row, whatever the folder it is in
        theirs = self.upload(COLLEAGUE, b"theirs", "note.txt")
        with self.set_user(COLLEAGUE):
            frappe.client.set_value("File", theirs.name, "file_url", f"/{place}/elsewhere.pdf")
        frappe.db.commit()
        self.assertTrue(self.manager.named_by_another_row(place, projects.name))
        self.assertEqual(self.content(inside.name), b"inside")

    def commit_elsewhere(self, file_name: str, content: bytes, folder=None) -> str:
        """An Active file of `folder` (the shared folder), with its bytes, made and committed by another request."""
        import hashlib

        from suite.drive.tests.test_folder_names import another_connection

        folder = folder or self.folder
        name = frappe.generate_hash(length=10)
        place = self.tree_path(file_name, folder)
        (self.manager.site_folder / place).write_bytes(content)
        now = frappe.utils.now()
        with another_connection() as other:
            other.sql("SET SESSION innodb_lock_wait_timeout = 5")
            other.sql(
                """INSERT INTO `tabFile` (`name`, `creation`, `modified`, `owner`, `modified_by`, `file_name`, `folder`,
                `file_url`, `is_private`, `is_folder`, `file_size`, `file_type`, `mime_type`, `status`, `content_hash`,
                `file_modified`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, 0, %s, 'PDF', 'application/pdf', %s, %s, %s)""",
                (
                    name,
                    now,
                    now,
                    COLLEAGUE,
                    COLLEAGUE,
                    file_name,
                    folder.name,
                    "/" + place.as_posix(),
                    len(content),
                    STATUS_ACTIVE,
                    hashlib.sha256(content).hexdigest(),
                    now,
                ),
            )
            other.commit()
        return name

    def test_two_moves_of_one_name_into_one_folder_get_two_names(self):
        # a move reads the names of the folder it goes to while it holds them, past its transaction's snapshot: the other
        # request had committed « dup.pdf » after this one began, and both aimed at the same place on the disk
        elsewhere = self.make_folder(OWNER, "Ailleurs-dup")
        mine = self.upload(OWNER, b"mine", "dup.pdf", parent=elsewhere.name)
        # this request's snapshot, taken before the other request commits
        frappe.db.sql("SELECT COUNT(*) FROM `tabFile` WHERE `folder` = %s", self.folder.name)
        theirs = self.commit_elsewhere("dup.pdf", b"theirs")

        with self.set_user(OWNER):
            frappe.get_doc("File", mine.name).move(self.folder.name)
        frappe.db.commit()

        self.assertEqual(frappe.db.get_value("File", mine.name, "file_name"), "dup (1).pdf")
        self.assertEqual(self.content(mine.name), b"mine")
        self.assertEqual(self.content(theirs), b"theirs")

    def test_two_renames_to_one_name_in_one_folder_are_not_both_taken(self):
        mine = self.upload(OWNER, b"mine", "free.pdf")
        frappe.db.sql("SELECT COUNT(*) FROM `tabFile` WHERE `folder` = %s", self.folder.name)
        theirs = self.commit_elsewhere("taken.pdf", b"theirs")

        with self.set_user(OWNER), self.assertRaises(frappe.ValidationError):
            frappe.get_doc("File", mine.name).rename("taken.pdf")
        frappe.db.rollback()

        self.assertEqual(self.content(mine.name), b"mine")
        self.assertEqual(self.content(theirs), b"theirs")

    def test_an_upload_never_replaces_bytes_already_at_its_place(self):
        orphan = self.manager.site_folder / self.tree_path("orphan.pdf")
        orphan.write_bytes(b"bytes no row names")

        mine = self.upload(OWNER, b"mine", "orphan.pdf")

        self.assertEqual(mine.file_name, "orphan (1).pdf")
        self.assertEqual(self.content(mine.name), b"mine")
        self.assertEqual(orphan.read_bytes(), b"bytes no row names")
        # and the storage itself refuses to place bytes over others
        staged = self.manager.site_folder / self.tree_path("staged.tmp")
        staged.write_bytes(b"staged")
        self.planted.append(staged)
        with self.assertRaisesRegex(frappe.ValidationError, "A file is already there"):
            self.manager.upload_file(staged, frappe._dict(name=mine.name, file_url=mine.file_url), False)
        self.assertEqual(self.content(mine.name), b"mine")

    def test_a_link_is_an_address_on_the_web_only(self):
        place = Path(storage_key(self.folder.file_url)) / "devis.pdf"
        for link in (place.as_posix(), "/" + place.as_posix(), "javascript:alert(1)", "https:///nohost"):
            with self.subTest(link=link), self.set_user(COLLEAGUE):
                with self.assertRaisesRegex(frappe.ValidationError, "http or https"):
                    create_link("devis.pdf", link, parent=self.folder.name)
            frappe.db.rollback()
        with self.set_user(COLLEAGUE):
            link = create_link("site", "https://example.com/page", parent=self.folder.name)
        self.assertEqual(link.file_url, "https://example.com/page")
        # and the name a colleague's file would take stays free
        self.assertFalse(self.manager.named_by_another_row(place, None))

    def test_folders_that_loop_into_each_other_change_nothing(self):
        first = self.make_folder(OWNER, "Premier")
        with self.set_user(OWNER):
            second = create_folder("Second", parent=first.name)
        frappe.db.commit()
        inside = self.upload(OWNER, b"inside", "plan.pdf", parent=second.name)
        url = frappe.db.get_value("File", inside.name, "file_url")
        # a corrupt `folder`: the first folder inside the second
        frappe.db.set_value("File", first.name, "folder", second.name, update_modified=False)

        with self.assertRaisesRegex(frappe.ValidationError, "loop"):
            repoint_descendants(first.name, first.file_url, "private/files/elsewhere/")
        self.assertEqual(frappe.db.get_value("File", inside.name, "file_url"), url)
        frappe.db.rollback()

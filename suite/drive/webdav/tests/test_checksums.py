# //// Neoffice — added file (no upstream equivalent): the catch-up of the SHA-256 of the Drive's files (maintenance#1598).
from __future__ import annotations

import hashlib
import os
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from suite.drive.utils import create_drive_file, get_user_folder
from suite.drive.utils.files import FileManager, storage_key
from suite.drive.webdav import checksums
from suite.drive.webdav.tests.utils import ensure_user_with_password, write_file_fixture

OWNER = "webdav-checksums-owner@example.com"
PASSWORD = "webdav-checksums-pw"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class TestChecksumBackfill(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_user_with_password(OWNER, PASSWORD)
        with cls.set_user(OWNER):
            cls.home = get_user_folder(OWNER).name

    def setUp(self):
        manager = FileManager()
        with self.set_user(OWNER):
            self.folder = create_drive_file(
                f"CS-{frappe.generate_hash(length=6)}",
                self.home,
                "Folder",
                lambda f: manager.create_folder(f),
            )

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def _file(self, name: str, data: bytes, content_hash):
        with self.set_user(OWNER):
            row = write_file_fixture(self.folder.name, name, data)
        frappe.db.set_value("File", row.name, "content_hash", content_hash, update_modified=False)
        return row

    def _hash(self, row):
        return frappe.db.get_value("File", row.name, "content_hash")

    def test_a_file_with_no_sum_or_an_md5_gets_its_sha256(self):
        bare = self._file("bare.txt", b"no sum yet", None)
        md5 = self._file("md5.txt", b"framework upload", hashlib.md5(b"framework upload").hexdigest())
        done = checksums.backfill(names=[bare.name, md5.name])
        self.assertEqual(done["hashed"], 2)
        self.assertEqual(self._hash(bare), sha(b"no sum yet"))
        self.assertEqual(self._hash(md5), sha(b"framework upload"))

    def test_a_file_that_already_has_one_is_left_alone(self):
        stamped = self._file("stamped.txt", b"the bytes", sha(b"the bytes"))
        before = frappe.db.get_value("File", stamped.name, "modified")
        done = checksums.backfill(names=[stamped.name])
        self.assertEqual(done["hashed"], 0)
        self.assertEqual(self._hash(stamped), sha(b"the bytes"))
        self.assertEqual(frappe.db.get_value("File", stamped.name, "modified"), before)

    def test_only_the_column_is_written(self):
        row = self._file("column.txt", b"only the column", None)
        before = frappe.db.get_value(
            "File", row.name, ["modified", "file_size", "file_modified"], as_dict=True
        )
        checksums.backfill(names=[row.name])
        after = frappe.db.get_value(
            "File", row.name, ["modified", "file_size", "file_modified"], as_dict=True
        )
        self.assertEqual(before, after)

    def test_folders_trashed_files_and_links_are_not_read(self):
        trashed = self._file("trashed.txt", b"in the bin", None)
        frappe.db.set_value("File", trashed.name, "status", "Trashed", update_modified=False)
        link = self._file("link.txt", b"a link", None)
        frappe.db.set_value("File", link.name, "file_type", "Link", update_modified=False)
        done = checksums.backfill(names=[self.folder.name, trashed.name, link.name])
        self.assertEqual(done["hashed"], 0)
        for name in (trashed.name, link.name):
            self.assertFalse(frappe.db.get_value("File", name, "content_hash"))

    def test_a_file_whose_bytes_are_gone_is_marked_once(self):
        row = self._file("gone.txt", b"vanished", None)
        os.remove(FileManager().site_folder / storage_key(frappe.db.get_value("File", row.name, "file_url")))
        first = checksums.backfill(names=[row.name])
        self.assertEqual(first["unreadable"], 1)
        self.assertEqual(self._hash(row), checksums.UNREADABLE)
        # it is not asked for again
        self.assertEqual(checksums.backfill(names=[row.name]), {**first, "unreadable": 0})

    def test_a_file_saved_while_it_was_read_is_not_overwritten(self):
        row = self._file("busy.txt", b"first version", None)
        real = checksums.sha256_of_path

        def saved_meanwhile(path, deadline=None):
            value = real(path, deadline)
            # an editor saved: the row moved and stamped its own sum
            frappe.db.set_value(
                "File",
                row.name,
                {"content_hash": sha(b"second version"), "file_size": 14},
                update_modified=True,
            )
            return value

        with patch.object(checksums, "sha256_of_path", saved_meanwhile):
            done = checksums.backfill(names=[row.name])
        self.assertEqual(done["changed_meanwhile"], 1)
        self.assertEqual(self._hash(row), sha(b"second version"))

    def test_it_can_be_switched_off(self):
        row = self._file("off.txt", b"left alone", None)
        with patch.dict(frappe.local.conf, {"drive_checksum_backfill": 0}):
            self.assertEqual(checksums.backfill(names=[row.name]), {"skipped": "switched off"})
        self.assertFalse(self._hash(row))

    def test_a_run_stops_at_its_time_budget_and_the_next_goes_on(self):
        rows = [self._file(f"slow-{i}.txt", f"bytes {i}".encode(), None) for i in range(3)]
        names = [row.name for row in rows]
        done = checksums.backfill(names=names, budget=-1)
        self.assertTrue(done["out_of_time"])
        self.assertEqual(done["hashed"], 0)
        again = checksums.backfill(names=names)
        self.assertEqual(again["hashed"], 3)

    def test_the_hourly_job_is_scheduled(self):
        import suite.hooks as hooks

        self.assertIn("suite.drive.webdav.checksums.backfill", hooks.scheduler_events["hourly"])

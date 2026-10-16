# //// Neoffice — added file (no upstream equivalent): the disk the Drive writes to, as its storage bar shows it
# //// (suite/drive/api/storage.py, drive_disk; maintenance#1598).
from __future__ import annotations

import shutil
from collections import namedtuple
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from suite.drive.api.storage import drive_disk, storage_bar_data

Usage = namedtuple("Usage", "total used free")


class TestTheDiskTheDriveWritesTo(IntegrationTestCase):
    def test_the_bar_says_the_volume_of_the_site_s_private_files(self):
        seen = []

        def disk_usage(path):
            seen.append(str(path))
            return Usage(500 * 10**9, 120 * 10**9, 380 * 10**9)

        with (
            patch("suite.drive.api.storage.shutil.disk_usage", side_effect=disk_usage),
            patch("suite.drive.api.storage.frappe.db.get_single_value", return_value=0),
        ):
            data = storage_bar_data()

        self.assertEqual(data["disk"], {"total": 500 * 10**9, "used": 120 * 10**9, "free": 380 * 10**9})
        self.assertEqual(seen, [frappe.get_site_path("private", "files")])
        # what the bar had before is still there: the person's use and the quota
        self.assertIn("total_size", data)
        self.assertIn("limit", data)

    def test_the_real_volume_is_read(self):
        with patch("suite.drive.api.storage.frappe.db.get_single_value", return_value=0):
            disk = drive_disk()
        real = shutil.disk_usage(frappe.get_site_path("private", "files"))
        self.assertEqual(disk["total"], real.total)
        self.assertGreater(disk["total"], 0)
        self.assertLessEqual(disk["used"], disk["total"])

    def test_files_kept_on_s3_have_no_disk_to_say(self):
        with patch("suite.drive.api.storage.frappe.db.get_single_value", return_value=1):
            self.assertIsNone(drive_disk())

    def test_a_volume_that_cannot_be_read_says_nothing(self):
        with (
            patch("suite.drive.api.storage.frappe.db.get_single_value", return_value=0),
            patch("suite.drive.api.storage.shutil.disk_usage", side_effect=OSError("gone")),
        ):
            self.assertIsNone(drive_disk())

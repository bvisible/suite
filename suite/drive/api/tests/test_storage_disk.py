# //// Neoffice — added file (no upstream equivalent): the disk the Drive writes to, as its storage bar shows it
# //// (suite/drive/api/storage.py, drive_disk; maintenance#1598).
from __future__ import annotations

import shutil
from collections import namedtuple
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from suite.drive.api.storage import drive_disk, storage_bar_data, storage_breakdown
from suite.drive.utils import create_drive_file, get_user_folder
from suite.tests.utils import ensure_user

Usage = namedtuple("Usage", "total used free")
OWNER = "drive-disk-owner@example.com"


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


class TestTheStatisticsOfTheDrive(IntegrationTestCase):
    def test_they_say_the_disk_and_offer_no_file_a_computer_wrote(self):
        ensure_user(OWNER)
        frappe.flags.mute_drive_activity_log = True
        try:
            with self.set_user(OWNER):
                home = get_user_folder(OWNER)
                for name in ("statistics.bin", "._statistics.bin", ".DS_Store"):
                    create_drive_file(name, home.name, "Text", f"{home.file_url}{name}", "text/plain", 4096)
                single = frappe.db.get_single_value

                def on_a_disk(doctype, field, *args, **kwargs):
                    # files on the site's disk (not on S3), whatever the site running the test keeps them on
                    if (doctype, field) == ("Drive Disk Settings", "enabled"):
                        return 0
                    return single(doctype, field, *args, **kwargs)

                with (
                    patch("suite.drive.api.storage.shutil.disk_usage", return_value=Usage(500, 120, 380)),
                    patch("suite.drive.api.storage.get_quota", return_value=0),
                    patch("suite.drive.api.storage.frappe.db.get_single_value", side_effect=on_a_disk),
                ):
                    data = storage_breakdown()
        finally:
            frappe.flags.mute_drive_activity_log = False

        self.assertEqual(data["disk"], {"total": 500, "used": 120, "free": 380})
        names = {entity.file_name for entity in data["entities"]}
        self.assertIn("statistics.bin", names)
        self.assertNotIn("._statistics.bin", names)
        self.assertNotIn(".DS_Store", names)

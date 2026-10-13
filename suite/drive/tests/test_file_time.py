# //// Neoffice — added file (no upstream equivalent). A file's own time (the browser's epoch) is kept in the
# //// zone of the site: read in the server's zone, a file uploaded a minute ago read « 2 hours ago ».
from __future__ import annotations

import time

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime

from suite.drive.utils import create_drive_file, get_user_folder


class TestFileTimeInTheSitesZone(IntegrationTestCase):
    def setUp(self):
        frappe.flags.mute_drive_activity_log = True

    def tearDown(self):
        frappe.flags.mute_drive_activity_log = False
        super().tearDown()

    def test_a_files_own_time_is_read_in_the_sites_zone(self):
        name = f"time-{frappe.generate_hash(length=6)}.txt"
        row = create_drive_file(name, get_user_folder().name, "Text", "", "text/plain", 1, time.time())
        stored = frappe.db.get_value("File", row.name, "file_modified")
        self.assertLess(abs((stored - now_datetime()).total_seconds()), 120, stored)

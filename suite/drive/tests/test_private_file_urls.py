# //// Neoffice — added file (no upstream equivalent): frappe's check on private files (validate_private_file_access,
# //// frappe fork, #1738) sees a url the way the Drive reads it, and a url in one of the Drive's own folders, whose bytes
# //// no row names, is refused (maintenance#1821). Before, a row of one's own set to a colleague's file without the
# //// leading slash, to a colleague's file in the trash or to a colleague's thumbnail passed the check, and the Drive
# //// served the colleague's bytes.
from __future__ import annotations

import shutil
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from suite.drive.api.files import ARCHIVE_DIR, remove_or_restore, upload_file
from suite.drive.utils import create_drive_file, get_user_folder
from suite.drive.utils.files import FileManager, get_s3_url, storage_key
from suite.drive.webdav.put import _PENDING_SWAP_PREFIX
from suite.tests.utils import ensure_user

OWNER = "drive-private-urls-owner@example.com"
OTHER = "drive-private-urls-other@example.com"
REFUSAL = "You don't have permission to access this file"


class TestThePrivateFileCheckReadsUrlsAsTheDriveDoes(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for user in (OWNER, OTHER):
            ensure_user(user)
        with cls.set_user(OWNER):
            cls.owner_home = get_user_folder(OWNER).name
        with cls.set_user(OTHER):
            cls.other_home = get_user_folder(OTHER).name
        frappe.db.commit()

    def setUp(self):
        self.manager = manager = FileManager()
        if manager.s3_enabled:
            self.skipTest("the Drive's bytes are on the site's disk here")
        frappe.flags.mute_drive_activity_log = True
        self.folders, self.planted = [], []
        for user, home in ((OWNER, self.owner_home), (OTHER, self.other_home)):
            with self.set_user(user):
                self.folders.append(
                    create_drive_file(
                        f"PrivateUrls-{frappe.generate_hash(length=6)}",
                        home,
                        "Folder",
                        lambda file: manager.create_folder(file),
                    )
                )
        frappe.db.commit()
        self.secret = self.upload(OWNER, b"the owner's secret", "secret.pdf", self.folders[0].name)
        self.mine = self.upload(OTHER, b"the other's note", "note.txt", self.folders[1].name)

    def tearDown(self):
        frappe.db.rollback()
        frappe.set_user("Administrator")
        names = []
        for folder in self.folders:
            names += self.subtree(folder.name)
            directory = self.manager.get_local_path(folder.file_url)
            if directory.is_dir() and folder.file_name in str(directory):
                shutil.rmtree(directory)
        for name in names:
            trashed = self.manager.site_folder / self.manager.get_trash_path(frappe._dict(name=name))
            shutil.rmtree(trashed) if trashed.is_dir() else trashed.unlink(missing_ok=True)
        for path in self.planted:
            path.unlink(missing_ok=True)
        frappe.db.delete("File", {"name": ("in", names)})
        frappe.db.commit()
        frappe.flags.mute_drive_activity_log = False
        super().tearDown()

    def subtree(self, name: str) -> list[str]:
        names = [name]
        for child in frappe.get_all("File", filters={"folder": name}, pluck="name"):
            names += self.subtree(child)
        return names

    def upload(self, user: str, content: bytes, file_name: str, parent: str):
        builder = EnvironBuilder(
            path="/api/method/x", method="POST", data={"file": (BytesIO(content), file_name)}
        )
        frappe.local.request = Request(builder.get_environ())
        try:
            with (
                self.set_user(user),
                patch("suite.drive.api.files.validate_quota"),
                patch("suite.drive.api.files.frappe.publish_realtime"),
                patch.object(FileManager, "can_create_thumbnail", return_value=False),
            ):
                frappe.form_dict.update({"uuid": frappe.generate_hash(length=12), "chunk_index": ""})
                uploaded = upload_file(total_file_size=len(content), parent=parent)
            frappe.db.commit()
            return uploaded
        finally:
            del frappe.local.request

    def plant(self, key: Path, content: bytes) -> Path:
        """Bytes the Drive keeps under `key` with no row naming them."""
        path = self.manager.site_folder / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        self.planted.append(path)
        return path

    def point_my_row_at(self, url: str):
        """The other user sets the url of a row of their own, through the desk's API."""
        with self.set_user(OTHER):
            frappe.client.set_value("File", self.mine.name, "file_url", url)

    def served(self) -> bytes:
        with self.manager.get_file(frappe.get_doc("File", self.mine.name)) as stored:
            return stored.read()

    def assert_refused(self, url: str):
        with self.subTest(url=url):
            with self.assertRaisesRegex(frappe.PermissionError, REFUSAL):
                self.point_my_row_at(url)
            frappe.db.rollback()
            self.assertEqual(self.served(), b"the other's note")

    def test_a_colleagues_file_is_refused_in_every_spelling_the_drive_reads(self):
        key = storage_key(self.secret.file_url)
        folder, name = key.rsplit("/", 1)
        for url in (
            "/" + key,  # frappe refused this one already
            key,
            "//" + key,
            "./" + key,
            f"{folder}/./{name}",
            f"{folder}//{name}",
            "files/../../" + key,
            get_s3_url(key),
        ):
            self.assert_refused(url)

    def test_ones_own_file_is_still_taken_in_another_spelling(self):
        # what proves the refusals above come from the check, not from the API
        key = storage_key(self.mine.file_url)
        self.point_my_row_at(key)
        self.assertEqual(frappe.db.get_value("File", self.mine.name, "file_url"), key)
        self.assertEqual(self.served(), b"the other's note")

    def test_a_colleagues_file_in_the_trash_is_refused(self):
        with self.set_user(OWNER):
            remove_or_restore([self.secret.name])
        frappe.db.commit()
        key = str(self.manager.get_trash_path(self.secret))
        for url in (key, "/" + key):
            self.assert_refused(url)

    def test_bytes_no_row_names_in_the_drives_own_folders_are_refused(self):
        root = Path(storage_key(self.manager.get_root_storage_key()))
        planted = [
            self.manager.get_thumbnail_path(self.secret.name),
            root / ".uploads" / f"{frappe.generate_hash(length=12)}_secret.pdf",
            root / _PENDING_SWAP_PREFIX / f"{self.secret.name}.{frappe.generate_hash(length=12)}.putpart",
            Path(ARCHIVE_DIR) / f"{frappe.generate_hash(length=16)}.zip",
            # in the trash, the bytes of a row that went another way
            root / ".trash" / frappe.generate_hash(length=10),
        ]
        for key in planted:
            self.plant(key, b"the owner's secret")
            for url in (str(key), "/" + str(key)):
                self.assert_refused(url)

    def test_a_new_row_aimed_at_a_colleagues_thumbnail_is_refused(self):
        key = self.manager.get_thumbnail_path(self.secret.name)
        self.plant(key, b"the owner's thumbnail")
        with self.set_user(OTHER), self.assertRaisesRegex(frappe.PermissionError, REFUSAL):
            frappe.get_doc(
                {"doctype": "File", "file_name": "copy.webp", "file_url": "/" + str(key), "is_private": 1}
            ).insert(ignore_permissions=True)
        frappe.db.rollback()
        with self.set_user(OTHER), self.assertRaisesRegex(frappe.PermissionError, REFUSAL):
            create_drive_file("copy.webp", self.folders[1].name, "Image", str(key), "image/webp", 1)

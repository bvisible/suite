# //// Neoffice — added file (no upstream equivalent): the names of a folder are given out one request at a time
# //// (suite/drive/utils, hold_folder_names; maintenance#1598). Each test plays the request that came second: the
# //// first one commits its entry from another connection while this test's transaction is open, after its snapshot
# //// was taken, as a request finishes while another one runs. A plain read cannot see that entry, a locking read
# //// does. Before, the second request took the same name, and the two rows shared one blob (or one directory):
# //// moving either one left the other without content.
from __future__ import annotations

import hashlib
import shutil
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from suite.drive.api.files import create_folder, upload_file
from suite.drive.utils import STATUS_ACTIVE, create_drive_file, get_user_folder
from suite.drive.utils.files import FileManager, storage_key
from suite.tests.utils import ensure_user

OWNER = "drive-names-owner@example.com"


@contextmanager
def another_connection():
    """A second connection to the site's database: what it commits is another request's work."""
    from frappe.database import get_db

    conf = frappe.local.conf
    other = get_db(
        socket=conf.db_socket,
        host=conf.db_host,
        port=conf.db_port,
        user=conf.db_user or conf.db_name,
        password=conf.db_password,
        cur_db_name=conf.db_name,
    )
    other.connect()
    try:
        yield other
    finally:
        other.close()


class TestFolderNamesAreGivenOutOneAtATime(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_user(OWNER)
        with cls.set_user(OWNER):
            cls.home = get_user_folder(OWNER).name

    def setUp(self):
        frappe.flags.mute_drive_activity_log = True
        self.manager = FileManager()
        self.elsewhere = []
        with self.set_user(OWNER):
            self.folder = create_drive_file(
                f"Names-{frappe.generate_hash(length=6)}",
                self.home,
                "Folder",
                lambda file: self.manager.create_folder(file),
            )
        frappe.db.commit()
        # the snapshot of this transaction: what is committed from now on is invisible to its plain reads
        frappe.db.sql("SELECT COUNT(*) FROM `tabFile` WHERE `folder` = %s", self.folder.name)

    def tearDown(self):
        # this transaction holds row locks on what it read FOR UPDATE: released before the other connection cleans up
        frappe.db.rollback()
        with another_connection() as other:
            names = [name for name, _ in self.elsewhere] + [self.folder.name]
            # and what the test made below the folder and a commit kept (ensure_path commits)
            names += [
                row[0]
                for row in other.sql("SELECT `name` FROM `tabFile` WHERE `folder` IN %s", [tuple(names)])
            ]
            other.sql("DELETE FROM `tabFile` WHERE `name` IN %s", [tuple(names)])
            other.commit()
        directory = self.manager.get_local_path(self.folder.file_url)
        if directory.is_dir() and self.folder.file_name in str(directory):
            shutil.rmtree(directory)
        frappe.flags.mute_drive_activity_log = False
        frappe.set_user("Administrator")
        super().tearDown()

    def commit_elsewhere(self, file_name: str, data: bytes | None = b"first", is_folder: bool = False) -> str:
        """An entry of the test folder, made and committed by another request (its row, and its blob or directory)."""
        name = frappe.generate_hash(length=10)
        if is_folder:
            relative = self.manager.create_folder(
                frappe._dict(file_name=file_name, parent_path=Path(storage_key(self.folder.file_url or "")))
            )
            url, path = str(relative), None
        else:
            relative = self.manager.get_disk_path(
                frappe._dict(file_name=file_name, parent_path=Path(storage_key(self.folder.file_url or "")))
            )
            path = self.manager.site_folder / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            url = "/" + str(relative)
        now = frappe.utils.now()
        with another_connection() as other:
            # another request does not wait long here: a wait would be a lock this test's request keeps
            other.sql("SET SESSION innodb_lock_wait_timeout = 5")
            other.sql(
                """INSERT INTO `tabFile` (`name`, `creation`, `modified`, `owner`, `modified_by`, `file_name`,
                `folder`, `file_url`, `is_private`, `is_folder`, `file_size`, `file_type`, `mime_type`, `status`,
                `content_hash`, `file_modified`)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    name,
                    now,
                    now,
                    OWNER,
                    OWNER,
                    file_name,
                    self.folder.name,
                    url,
                    int(is_folder),
                    0 if is_folder else len(data),
                    "Folder" if is_folder else "Text",
                    None if is_folder else "text/plain",
                    STATUS_ACTIVE,
                    None if is_folder else hashlib.sha256(data).hexdigest(),
                    now,
                ),
            )
            other.commit()
        self.elsewhere.append((name, path))
        return name

    def active(self, file_name: str) -> list[str]:
        return [
            row[0]
            for row in frappe.db.sql(
                "SELECT `name` FROM `tabFile` WHERE `folder` = %s AND `file_name` = %s AND `status` = %s FOR UPDATE",
                (self.folder.name, file_name, STATUS_ACTIVE),
            )
        ]

    @contextmanager
    def upload_request(self, content: bytes, filename: str, **form):
        builder = EnvironBuilder(
            path="/api/method/suite.drive.api.files.upload_file",
            method="POST",
            data={"file": (BytesIO(content), filename)},
        )
        frappe.local.request = Request(builder.get_environ())
        values = {"uuid": frappe.generate_hash(length=12), "chunk_index": "", **form}
        frappe.form_dict.update(values)
        try:
            with (
                patch("suite.drive.api.files.validate_quota"),
                patch("suite.drive.api.files.frappe.publish_realtime"),
            ):
                yield
        finally:
            for key in values:
                frappe.form_dict.pop(key, None)
            del frappe.local.request

    def test_an_upload_of_a_name_just_taken_elsewhere_gets_its_own_name_and_blob(self):
        first = self.commit_elsewhere("race.txt", b"first")

        with self.set_user(OWNER), self.upload_request(b"second", "race.txt"):
            second = upload_file(total_file_size=6, parent=self.folder.name)

        self.assertEqual(second.file_name, "race (1).txt")
        self.assertEqual(self.active("race.txt"), [first])
        with self.manager.get_file(second) as stored:
            self.assertEqual(stored.read(), b"second")
        # the first file kept its own content
        self.assertEqual(self.elsewhere[0][1].read_bytes(), b"first")

    def test_the_files_of_a_new_folder_uploaded_at_once_land_in_one_folder(self):
        made = self.commit_elsewhere("Photos", is_folder=True)

        with self.set_user(OWNER), self.upload_request(b"second", "b.txt"):
            uploaded = upload_file(total_file_size=6, parent=self.folder.name, fullpath="Photos/b.txt")

        self.assertEqual(uploaded.folder, made)
        self.assertEqual(self.active("Photos"), [made])
        # in that folder's directory on the disk too
        self.assertTrue(uploaded.file_url.endswith("/Photos/b.txt"), uploaded.file_url)
        with self.manager.get_file(uploaded) as stored:
            self.assertEqual(stored.read(), b"second")

    def test_an_upload_keeps_no_lock_on_the_other_names_of_its_folder(self):
        # Once it holds the folder's names and has committed, an upload reads them plainly. A locking read kept the range
        # of names it looked at locked until the request's end, and another request writing in that folder waited on it:
        # two uploads into one new folder at once waited on each other until a timeout.
        with self.set_user(OWNER), self.upload_request(b"mine", "a.txt"):
            upload_file(total_file_size=4, parent=self.folder.name)

        # this request is still open: another one writes a name of the same folder at once
        other = self.commit_elsewhere("a (2).txt", b"other")

        self.assertEqual(self.active("a (2).txt"), [other])

    def test_a_folder_made_twice_at_once_is_refused_the_second_time(self):
        made = self.commit_elsewhere("Plans", is_folder=True)

        with self.set_user(OWNER), self.assertRaises(frappe.ValidationError):
            create_folder("Plans", parent=self.folder.name)

        self.assertEqual(self.active("Plans"), [made])

    def test_a_put_of_a_file_just_committed_elsewhere_overwrites_it(self):
        from suite.drive.webdav import put
        from suite.drive.webdav.tests.utils import make_ctx

        first = self.commit_elsewhere("race.dav.txt", b"first")

        response = put.handle(
            make_ctx(
                "PUT",
                f"/dav/Home/{self.folder.file_name}/race.dav.txt",
                OWNER,
                data=b"second body",
                content_type="application/octet-stream",
            )
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.active("race.dav.txt"), [first])
        self.assertEqual(
            frappe.db.get_value("File", first, "content_hash"), hashlib.sha256(b"second body").hexdigest()
        )

    def test_a_mkcol_of_a_folder_just_committed_elsewhere_is_refused(self):
        from suite.drive.webdav import structure
        from suite.drive.webdav.errors import MethodNotAllowed
        from suite.drive.webdav.tests.utils import make_ctx

        made = self.commit_elsewhere("Archive", is_folder=True)

        with self.assertRaises(MethodNotAllowed):
            structure.handle_mkcol(make_ctx("MKCOL", f"/dav/Home/{self.folder.file_name}/Archive", OWNER))

        self.assertEqual(self.active("Archive"), [made])

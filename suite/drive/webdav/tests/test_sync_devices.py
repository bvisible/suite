# //// Neoffice — added file (no upstream equivalent): the computers paired to synchronise a folder, and what a
# //// synchronising client reads (the owncloud-namespace properties).
"""A paired computer's token opens the Drive's WebDAV for its user and nothing else; revoking it stops that computer.

Expectations come from the contract in the vault's note 06 (« Synchro du Drive avec rclone »), not from the code:
the token is shown once and only its SHA-256 is kept; Bearer is accepted by /dav; a revoked, unknown, malformed or
disabled-account token is the same refusal; one person never sees or stops another's computers (a System Manager
can stop any); a stable identifier, a size and, when it is known, a SHA-256 are readable as `oc:` properties.
"""

from __future__ import annotations

import hashlib
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from lxml import etree

from suite.drive.api import sync
from suite.drive.doctype.drive_sync_device.drive_sync_device import TOKEN_PREFIX, hash_token
from suite.drive.utils import create_drive_file, get_user_folder
from suite.drive.utils.files import FileManager
from suite.drive.webdav import propfind, structure
from suite.drive.webdav.properties import OC_NS
from suite.drive.webdav.tests.utils import (
    dispatch,
    enable_user_webdav,
    ensure_user_with_password,
    make_ctx,
    write_file_fixture,
)
from suite.drive.webdav.xmlutil import dav
from suite.tests.utils import ensure_user

OWNER = "webdav-device-owner@example.com"
OTHER = "webdav-device-other@example.com"
MANAGER = "webdav-device-manager@example.com"
PASSWORD = "webdav-device-pw-9000"
PROPFIND_OC = (
    b'<?xml version="1.0"?><D:propfind xmlns:D="DAV:" xmlns:oc="http://owncloud.org/ns">'
    b"<D:prop><oc:fileid/><oc:size/><oc:checksums/><D:getetag/></D:prop></D:propfind>"
)


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Depth": "0"}


class TestSyncDevices(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for user in (OWNER, OTHER):
            ensure_user_with_password(user, PASSWORD)
        ensure_user(MANAGER)
        frappe.get_doc("User", MANAGER).add_roles("System Manager")
        frappe.db.commit()

    def setUp(self):
        frappe.db.set_single_value("Drive Disk Settings", "webdav_enabled", 1)
        frappe.clear_document_cache("Drive Disk Settings", "Drive Disk Settings")
        frappe.db.delete("Drive Sync Device", {"user": ["in", [OWNER, OTHER]]})
        frappe.db.commit()

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.delete("Drive Sync Device", {"user": ["in", [OWNER, OTHER]]})
        frappe.db.set_single_value("Drive Disk Settings", "webdav_enabled", 0)
        frappe.clear_document_cache("Drive Disk Settings", "Drive Disk Settings")
        frappe.db.commit()
        super().tearDown()

    def _pair(self, user: str = OWNER, name: str = "MacBook de test") -> dict:
        frappe.set_user(user)
        paired = sync.register_device(name, "macOS 15 arm64", "Neodesk 0.5.9")
        frappe.db.commit()
        frappe.set_user("Administrator")
        return paired

    # ── pairing ─────────────────────────────────────────────────────────────

    def test_the_token_is_given_once_and_only_its_hash_is_kept(self):
        paired = self._pair()
        self.assertTrue(paired["token"].startswith(TOKEN_PREFIX))
        self.assertGreaterEqual(len(paired["token"]), 40)
        self.assertTrue(paired["dav_url"].endswith("/dav/"))

        stored = frappe.db.get_value("Drive Sync Device", paired["id"], "*", as_dict=True)
        self.assertEqual(stored.token_hash, hashlib.sha256(paired["token"].encode()).hexdigest())
        self.assertEqual(stored.token_hint, paired["token"][-4:])
        self.assertEqual(stored.user, OWNER)
        self.assertEqual(stored.device_name, "MacBook de test")
        self.assertNotIn(paired["token"], " ".join(str(value) for value in stored.values()))

        # the listing never says it again
        frappe.set_user(OWNER)
        listed = sync.list_devices()
        self.assertEqual([row["id"] for row in listed], [paired["id"]])
        self.assertNotIn(paired["token"], str(listed))

    def test_pairing_asks_for_a_name_and_a_site_that_has_the_feature(self):
        frappe.set_user(OWNER)
        with self.assertRaises(frappe.ValidationError):
            sync.register_device("   ")
        frappe.set_user("Administrator")
        frappe.db.set_single_value("Drive Disk Settings", "webdav_enabled", 0)
        frappe.clear_document_cache("Drive Disk Settings", "Drive Disk Settings")
        frappe.set_user(OWNER)
        with self.assertRaises(frappe.PermissionError):
            sync.register_device("Un Mac")
        frappe.set_user("Guest")
        with self.assertRaises(frappe.PermissionError):
            sync.register_device("Un Mac")

    def test_pairing_turns_the_accounts_own_switch_on(self):
        enable_user_webdav(OWNER)
        frappe.db.set_value("Drive Settings", OWNER, "webdav_enabled", 0, update_modified=False)
        frappe.db.commit()
        paired = self._pair()
        self.assertTrue(paired["id"])
        self.assertEqual(frappe.db.get_value("Drive Settings", OWNER, "webdav_enabled"), 1)

    def test_the_number_of_computers_is_bounded(self):
        with patch.object(sync, "MAX_DEVICES_PER_USER", 2):
            self._pair(name="un")
            self._pair(name="deux")
            frappe.set_user(OWNER)
            with self.assertRaises(frappe.ValidationError):
                sync.register_device("trois")

    # ── the token at the door of /dav ───────────────────────────────────────

    def test_a_paired_computer_reads_its_owners_drive(self):
        paired = self._pair()
        response = dispatch("PROPFIND", "/dav/Home", headers=bearer(paired["token"]))
        self.assertEqual(response.status_code, 207)
        frappe.set_user("Administrator")

    def test_a_token_is_its_owner_and_nobody_else(self):
        mine = self._pair(OWNER)
        theirs = self._pair(OTHER, "Le PC de l'autre")
        dispatch("PROPFIND", "/dav/Home", headers=bearer(mine["token"]))
        self.assertEqual(frappe.session.user, OWNER)
        frappe.set_user("Administrator")
        dispatch("PROPFIND", "/dav/Home", headers=bearer(theirs["token"]))
        self.assertEqual(frappe.session.user, OTHER)
        frappe.set_user("Administrator")

    def test_an_unknown_malformed_or_empty_token_is_one_refusal(self):
        for token in ("", "nope", TOKEN_PREFIX + "x" * 40, "A" * 400):
            response = dispatch("PROPFIND", "/dav/Home", headers=bearer(token))
            self.assertEqual(response.status_code, 401, token[:12])
            self.assertIn("Basic", response.headers["WWW-Authenticate"])

    def test_a_revoked_token_is_refused_at_its_next_request_and_the_others_are_not(self):
        first = self._pair(name="un")
        second = self._pair(name="deux")
        self.assertEqual(dispatch("PROPFIND", "/dav/Home", headers=bearer(first["token"])).status_code, 207)
        frappe.set_user(OWNER)
        sync.revoke_device(first["id"])
        frappe.db.commit()
        self.assertEqual(dispatch("PROPFIND", "/dav/Home", headers=bearer(first["token"])).status_code, 401)
        self.assertEqual(dispatch("PROPFIND", "/dav/Home", headers=bearer(second["token"])).status_code, 207)
        self.assertTrue(frappe.db.get_value("Drive Sync Device", first["id"], "revoked"))
        self.assertTrue(frappe.db.get_value("Drive Sync Device", first["id"], "revoked_at"))

    def test_the_token_of_a_disabled_account_is_refused(self):
        paired = self._pair()
        frappe.db.set_value("User", OWNER, "enabled", 0)
        frappe.db.commit()
        try:
            self.assertEqual(
                dispatch("PROPFIND", "/dav/Home", headers=bearer(paired["token"])).status_code, 401
            )
        finally:
            frappe.db.set_value("User", OWNER, "enabled", 1)
            frappe.db.commit()

    def test_the_site_switch_still_closes_the_door(self):
        paired = self._pair()
        frappe.db.set_single_value("Drive Disk Settings", "webdav_enabled", 0)
        frappe.clear_document_cache("Drive Disk Settings", "Drive Disk Settings")
        from werkzeug.exceptions import NotFound

        with self.assertRaises(NotFound):
            dispatch("PROPFIND", "/dav/Home", headers=bearer(paired["token"]))

    def test_a_computer_is_noted_as_seen_without_a_write_per_request(self):
        paired = self._pair()
        frappe.cache.delete_value(f"drive_sync_device_seen:{paired['id']}")
        dispatch("PROPFIND", "/dav/Home", headers=bearer(paired["token"]))
        first = frappe.db.get_value("Drive Sync Device", paired["id"], "last_seen")
        self.assertTrue(first)
        with patch("frappe.db.set_value") as write:
            dispatch("PROPFIND", "/dav/Home", headers=bearer(paired["token"]))
            for call in write.call_args_list:
                self.assertNotEqual(call.args[0], "Drive Sync Device")

    # ── who may stop which computer ─────────────────────────────────────────

    def test_a_person_stops_their_own_computer_and_never_another_persons(self):
        mine = self._pair(OWNER)
        theirs = self._pair(OTHER, "Le PC de l'autre")
        frappe.set_user(OWNER)
        with self.assertRaises(frappe.DoesNotExistError):
            sync.revoke_device(theirs["id"])
        with self.assertRaises(frappe.DoesNotExistError):
            sync.revoke_device("does-not-exist")
        self.assertEqual(sync.revoke_device(mine["id"])["revoked"], True)
        self.assertFalse(frappe.db.get_value("Drive Sync Device", theirs["id"], "revoked"))
        self.assertEqual([row["id"] for row in sync.list_devices()], [mine["id"]])

    def test_a_system_manager_stops_a_lost_computer(self):
        theirs = self._pair(OTHER)
        frappe.set_user(MANAGER)
        self.assertEqual(sync.revoke_device(theirs["id"])["revoked"], True)
        frappe.set_user("Administrator")
        self.assertEqual(dispatch("PROPFIND", "/dav/Home", headers=bearer(theirs["token"])).status_code, 401)

    def test_the_hash_is_what_the_door_looks_up(self):
        self.assertEqual(hash_token("abc"), hashlib.sha256(b"abc").hexdigest())


class TestOwncloudProperties(IntegrationTestCase):
    """What rclone's `nextcloud` vendor and the engines of that family read to tell a rename from a new file.

    The handlers are called directly (as test_propfind and test_movecopy do), nothing is committed, and every test
    works in a folder of its own: the dispatcher commits whatever it answers, which would leave the fixtures behind.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_user_with_password(OWNER, PASSWORD)
        with cls.set_user(OWNER):
            cls.home = get_user_folder(OWNER).name

    def setUp(self):
        self.folder_name = f"OC-{frappe.generate_hash(length=6)}"
        self.path = f"/dav/Home/{self.folder_name}"
        manager = FileManager()
        with self.set_user(OWNER):
            self.folder = create_drive_file(
                self.folder_name, self.home, "Folder", lambda f: manager.create_folder(f)
            )

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def _props(self, path: str) -> etree._Element:
        ctx = make_ctx(
            "PROPFIND",
            path,
            OWNER,
            headers={"Depth": "0", "Content-Type": "application/xml"},
            data=PROPFIND_OC,
        )
        response = propfind.handle(ctx)
        self.assertEqual(response.status_code, 207)
        return etree.fromstring(response.get_data()).find(
            f"{dav('response')}/{dav('propstat')}/{dav('prop')}"
        )

    def _text(self, prop: etree._Element, name: str) -> str | None:
        element = prop.find(f"{{{OC_NS}}}{name}")
        return None if element is None else "".join(element.itertext()).strip()

    def _move(self, source: str, destination: str) -> None:
        structure.handle_move(make_ctx("MOVE", source, OWNER, headers={"Destination": destination}))

    def test_a_file_has_a_stable_identifier_a_size_and_its_sha256(self):
        body = b"synchronised bytes"
        with self.set_user(OWNER):
            row = write_file_fixture(self.folder.name, "props.txt", body)
        digest = hashlib.sha256(body).hexdigest()
        frappe.db.set_value("File", row.name, "content_hash", digest, update_modified=False)

        prop = self._props(f"{self.path}/props.txt")
        self.assertEqual(self._text(prop, "fileid"), row.name)
        self.assertEqual(self._text(prop, "size"), str(len(body)))
        self.assertEqual(self._text(prop, "checksums"), f"SHA256:{digest}")

    def test_a_hash_that_is_not_a_sha256_is_not_told_as_one(self):
        with self.set_user(OWNER):
            row = write_file_fixture(self.folder.name, "md5.txt", b"bytes of a web upload")
        frappe.db.set_value(
            "File",
            row.name,
            "content_hash",
            hashlib.md5(b"bytes of a web upload").hexdigest(),
            update_modified=False,
        )
        prop = self._props(f"{self.path}/md5.txt")
        self.assertEqual(self._text(prop, "fileid"), row.name)
        # asked for, and not there: the property is in the 404 propstat, not in this one
        self.assertIsNone(prop.find(f"{{{OC_NS}}}checksums"))

    def test_a_folder_has_an_identifier_and_no_checksum(self):
        prop = self._props(self.path)
        self.assertEqual(self._text(prop, "fileid"), self.folder.name)
        self.assertIsNone(prop.find(f"{{{OC_NS}}}checksums"))

    def test_the_identifier_survives_a_rename_and_a_move(self):
        manager = FileManager()
        with self.set_user(OWNER):
            row = write_file_fixture(self.folder.name, "before.txt", b"x")
            create_drive_file("sub", self.folder.name, "Folder", lambda f: manager.create_folder(f))
        before = self._text(self._props(f"{self.path}/before.txt"), "fileid")
        self.assertEqual(before, row.name)

        self._move(f"{self.path}/before.txt", f"{self.path}/after.txt")
        self.assertEqual(self._text(self._props(f"{self.path}/after.txt"), "fileid"), before)

        self._move(f"{self.path}/after.txt", f"{self.path}/sub/moved.txt")
        self.assertEqual(self._text(self._props(f"{self.path}/sub/moved.txt"), "fileid"), before)

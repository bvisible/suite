# //// Neoffice — added file (no upstream equivalent): the four advisories that frappe/drive published on 10.11.2026,
# //// read against the Drive of the Suite (GHSA-73gm-29h2-x4jf, GHSA-xqwr-x9c5-vvf8, GHSA-hvv9-wq9j-hccx,
# //// GHSA-rw29-8w4g-95jw). The e-mail codes (rw29) were already timed and counted here (test_account_access). Each test
# //// below is the probe of what was still open: it fails on the code before its fix.
"""What the Drive's advisories of 10.11.2026 still left open in the Suite, each played as its attacker would."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import frappe
from frappe.tests import IntegrationTestCase

from suite.drive.api import product
from suite.drive.api.files import create_folder, create_link
from suite.drive.utils import get_user_folder
from suite.drive.utils.files import FileManager
from suite.drive.webdav import put
from suite.drive.webdav.errors import Conflict
from suite.drive.wopi import craft, editor, endpoints
from suite.tests.utils import ensure_user

OWNER = "drive-advisories-owner@example.com"
# the rate limit of the editor's entry point reads the request; this calls the function
EDITOR_CONFIG = getattr(craft.get_craft_editor_config, "__wrapped__", craft.get_craft_editor_config)


def make_invitation(email: str) -> str:  # role-check: ok scenery an admin prepares
    frappe.set_user("Administrator")
    doc = frappe.new_doc("Drive User Invitation")
    doc.email = email
    doc.status = "Pending"
    with patch.object(type(doc), "invite_via_email"):
        doc.insert(ignore_permissions=True)
    return doc.name


class TestTheInvitationLinkCarriesItsProof(IntegrationTestCase):
    """GHSA-xqwr-x9c5-vvf8: for an address with no account, the key alone signed whoever held it up."""

    def setUp(self):
        frappe.local.request = None
        frappe.local.login_manager = MagicMock()
        frappe.local.response = frappe._dict()

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def test_the_key_alone_signs_nobody_up(self):
        # imported here: on the code before the fix, the other probes of this module still run
        from suite.drive.doctype.drive_user_invitation.drive_user_invitation import get_invite_token

        email = f"drive-advisory-{frappe.generate_hash(length=6)}@example.test"
        name = make_invitation(email)
        frappe.set_user("Guest")
        for token in (None, "", "0" * 64, get_invite_token(name + "x")):
            with self.subTest(token=token), self.assertRaises(frappe.PermissionError):
                product.accept_invite(key=name, token=token)
        self.assertFalse(frappe.db.exists("Account Request", {"email": email}))

        product.accept_invite(key=name, token=get_invite_token(name))
        query = parse_qs(urlparse(frappe.local.response["location"]).query)
        self.assertEqual(query["e"], [email])
        self.assertTrue(frappe.db.exists("Account Request", {"email": email}))

    def test_the_emailed_link_carries_the_token(self):
        from suite.drive.doctype.drive_user_invitation.drive_user_invitation import get_invite_token

        email = f"drive-advisory-{frappe.generate_hash(length=6)}@example.test"
        name = make_invitation(email)
        invitation = frappe.get_doc("Drive User Invitation", name)
        with patch(
            "suite.drive.doctype.drive_user_invitation.drive_user_invitation.suite_email.send"
        ) as send:
            invitation.invite_via_email()
        link = send.call_args.args[2]["link"]
        query = parse_qs(urlparse(link).query)
        self.assertEqual(query["key"], [name])
        self.assertEqual(query["token"], [get_invite_token(name)])


class TestTheDriveAloneWritesItsPlaces(IntegrationTestCase):
    """GHSA-hvv9-wq9j-hccx (a row's place in the tree) and GHSA-73gm-29h2-x4jf (writes outside the files folders)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_user(OWNER)
        with cls.set_user(OWNER):
            cls.home = get_user_folder(OWNER).name
        # the owner's folder outlives each test's rollback
        frappe.db.commit()

    def setUp(self):
        frappe.flags.mute_drive_activity_log = True
        self.site = Path(frappe.get_site_path()).resolve()
        self.suffix = frappe.generate_hash(length=8)
        self.made = []

    def tearDown(self):
        frappe.flags.mute_drive_activity_log = False
        frappe.set_user("Administrator")
        frappe.db.rollback()
        # what a Drive flow committed on its own
        for name in self.made:
            frappe.db.delete("File", {"name": name})
        frappe.db.commit()
        super().tearDown()

    def tree_on_the_disk(self) -> FileManager:
        manager = FileManager()
        if manager.flat or manager.s3_enabled:
            self.skipTest("the Drive keeps its files in a tree on this site's disk only there")
        return manager

    def folder_without_address(self) -> str:
        """A folder of the owner's that has no address, as frappe's own create_new_folder makes one."""
        row = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": f"advisory-{self.suffix}",
                "is_folder": 1,
                "is_private": 1,
                "folder": self.home,
                "owner": OWNER,
            }
        )
        row.db_insert()
        self.made.append(row.name)
        return row.name

    def test_a_document_api_does_not_move_a_row_in_the_tree(self):
        self.tree_on_the_disk()
        with self.set_user(OWNER):
            a = create_folder(f"A-{self.suffix}", self.home).name
            b = create_folder(f"B-{self.suffix}", self.home).name
            self.made += [a, b]
            for field, value in (("folder", b), ("is_folder", 0)):
                with self.subTest(field=field), self.assertRaises(frappe.PermissionError):
                    frappe.client.set_value("File", a, field, value)
            self.assertEqual(frappe.db.get_value("File", a, "folder"), self.home)
            # and the Drive's own move still does it
            frappe.get_doc("File", a).move(b)
            self.assertEqual(frappe.db.get_value("File", a, "folder"), b)

    def test_a_link_never_opens_in_an_editor(self):
        with self.set_user(OWNER):
            link = create_link(
                f"advisory-{self.suffix}.docx", "https://example.com/advisory/x.bin", self.home
            )
            self.made.append(link.name)
            self.assertFalse(EDITOR_CONFIG(link.name)["available"])
            with self.assertRaises(frappe.DoesNotExistError):
                endpoints.get_wopi_file(link.name)

    def test_a_new_document_never_lands_in_the_sites_folder(self):
        self.tree_on_the_disk()
        folder = self.folder_without_address()
        title = f"advisory-{self.suffix}"
        with self.set_user(OWNER), self.assertRaises(frappe.ValidationError):
            editor.create_office_file("docx", title, parent=folder)
        self.assertFalse((self.site / f"{title}.docx").exists())

    def test_a_webdav_put_never_sets_aside_what_lies_in_the_sites_folder(self):
        manager = self.tree_on_the_disk()
        folder = self.folder_without_address()
        # a file of the site's own folder, standing for its site_config.json
        sentinel = self.site / f"advisory-sentinel-{self.suffix}.txt"
        sentinel.write_bytes(b"keep")
        self.addCleanup(lambda: sentinel.unlink(missing_ok=True))
        with self.assertRaises(Conflict):
            put._clear_the_place(manager, folder, sentinel.name)
        self.assertEqual(sentinel.read_bytes(), b"keep")

    def test_the_drive_folder_is_a_name_inside_the_files_folder(self):
        settings = frappe.get_single("Drive Disk Settings")
        for field in ("root_folder", "thumbnail_prefix"):
            for value in ("../outside", "/etc", "a/../b", "a//b", ".", "a\\b"):
                with self.subTest(field=field, value=value), self.assertRaises(frappe.ValidationError):
                    settings.set(field, value)
                    settings.validate()
            settings.set(field, "Drive/Files")
            settings.validate()

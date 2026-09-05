# //// Neoffice — added file (no upstream equivalent). The WOPI/Collabora port is
# //// ours and so are the defects fixed on 2026-09-04; each test below pins one of
# //// them, so a later merge that drops a guard fails here instead of in production.
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from suite.drive.utils import create_drive_file, get_user_folder
from suite.drive.utils.files import FileManager, storage_key
from suite.drive.wopi import discovery, endpoints
from suite.drive.wopi.editor import create_office_file
from suite.drive.wopi.token import generate_wopi_token, get_wopi_secret, validate_wopi_token
from suite.tests.utils import ensure_user

OWNER = "wopi-owner@example.com"
INTRUDER = "wopi-intruder@example.com"


def _office_file(owner: str, folder: str, folder_url: str):
    """A .docx File record owned by `owner`, with real bytes behind it."""
    name = f"{frappe.generate_hash(8)}.docx"
    file = create_drive_file(
        name,
        folder,
        "Document",
        f"{folder_url}{name}",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        4,
        owner=owner,
    )
    path = FileManager().site_folder / storage_key(file.file_url)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(b"DOCX")
    return file, path


class TestCreateOfficeFilePermission(IntegrationTestCase):
    """create_office_file() inserts with ignore_permissions=True, so the guard on
    `parent` is the only thing between a signed-in user and anybody else's folder."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_user(OWNER)
        ensure_user(INTRUDER)
        with cls.set_user(OWNER):
            cls.home = get_user_folder(OWNER)

    def setUp(self):
        frappe.flags.mute_drive_activity_log = True
        with self.set_user(OWNER):
            manager = FileManager()
            self.folder = create_drive_file(
                frappe.generate_hash(8),
                self.home.name,
                "Folder",
                lambda file: manager.create_folder(file),
                owner=OWNER,
            )

    def tearDown(self):
        frappe.flags.mute_drive_activity_log = False
        super().tearDown()

    def _drop(self, file_id: str) -> None:
        """create_office_file() commits, so the happy path is undone by hand."""
        file_url = frappe.db.get_value("File", file_id, "file_url")
        frappe.delete_doc("File", file_id, force=True, ignore_permissions=True, delete_permanently=True)
        frappe.db.commit()
        if file_url:
            path = FileManager().site_folder / storage_key(file_url)
            if os.path.exists(path):
                os.remove(path)

    def test_another_user_cannot_create_in_my_folder(self):
        with self.set_user(INTRUDER):
            with self.assertRaises(frappe.PermissionError):
                create_office_file("docx", "intruder", parent=self.folder.name)

        self.assertEqual(
            frappe.get_all("File", filters={"folder": self.folder.name}, pluck="name"),
            [],
            "the refusal must happen before anything is inserted",
        )

    def test_a_file_that_is_not_a_folder_cannot_be_a_parent(self):
        with self.set_user(OWNER):
            document, path = _office_file(OWNER, self.folder.name, self.folder.file_url)
            self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
            with self.assertRaises(frappe.ValidationError):
                create_office_file("docx", "wrong parent", parent=document.name)

    def test_a_parent_that_does_not_exist_is_refused(self):
        with self.set_user(OWNER):
            with self.assertRaises(frappe.DoesNotExistError):
                create_office_file("docx", "nowhere", parent="does-not-exist")

    def test_owner_can_still_create_in_their_own_folder(self):
        """The positive control: the guard refuses the intruder, not everybody."""
        with self.set_user(OWNER):
            result = create_office_file("docx", "mine", parent=self.folder.name)
        self.addCleanup(self._drop, result["file_id"])

        self.assertEqual(result["file_name"], "mine.docx")
        self.assertEqual(frappe.db.get_value("File", result["file_id"], "folder"), self.folder.name)


class TestWopiSigningSecret(IntegrationTestCase):
    """A secret invented per request cannot verify the token it signed."""

    def test_the_secret_is_the_same_from_one_call_to_the_next(self):
        self.assertEqual(get_wopi_secret(), get_wopi_secret())

    def test_a_token_signed_now_validates_now(self):
        token = generate_wopi_token("some-file-id", user=OWNER, can_write=True)
        payload = validate_wopi_token(token["access_token"])

        self.assertEqual(payload["file_id"], "some-file-id")
        self.assertEqual(payload["user_id"], OWNER)
        self.assertTrue(payload["can_write"])

    def test_a_missing_secret_is_reported_not_invented(self):
        """Before the fix this returned a fresh random value on every call."""
        with patch(
            "suite.drive.wopi.token.get_wopi_settings",
            return_value={"enabled": True, "jwt_secret": None, "jwt_expiry_hours": 4},
        ):
            with self.assertRaises(frappe.ValidationError):
                get_wopi_secret()


class TestWopiTokenExpiry(IntegrationTestCase):
    """`access_token_ttl` is what Collabora believes; `exp` is what we enforce."""

    def _force_timezone(self, name: str) -> None:
        previous = os.environ.get("TZ")

        def restore():
            if previous is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = previous
            time.tzset()

        self.addCleanup(restore)
        os.environ["TZ"] = name
        time.tzset()

    def test_the_ttl_and_the_signed_expiry_agree_off_utc(self):
        """datetime.utcnow() is naive, so .timestamp() read it as LOCAL time and the
        ttl handed to Collabora was off by the server's UTC offset. Forcing a
        non-UTC zone is the only way to see it: the fleet's servers run on UTC."""
        self._force_timezone("Europe/Zurich")

        token = generate_wopi_token("some-file-id", user=OWNER)
        payload = validate_wopi_token(token["access_token"])

        self.assertEqual(token["access_token_ttl"] // 1000, payload["exp"])

    def test_the_expiry_is_the_configured_number_of_hours_away(self):
        with patch(
            "suite.drive.wopi.token.get_wopi_settings",
            return_value={"enabled": True, "jwt_secret": get_wopi_secret(), "jwt_expiry_hours": 3},
        ):
            token = generate_wopi_token("some-file-id", user=OWNER)

        payload = validate_wopi_token(token["access_token"])
        expected = datetime.now(timezone.utc) + timedelta(hours=3)
        self.assertAlmostEqual(payload["exp"], int(expected.timestamp()), delta=5)


class TestWopiEndpointsRecheckPermission(IntegrationTestCase):
    """A WOPI token freezes `can_write` for hours. Revocation has to bite before it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_user(OWNER)
        ensure_user(INTRUDER)
        with cls.set_user(OWNER):
            cls.home = get_user_folder(OWNER)

    def setUp(self):
        frappe.flags.mute_drive_activity_log = True
        with self.set_user(OWNER):
            manager = FileManager()
            self.folder = create_drive_file(
                frappe.generate_hash(8),
                self.home.name,
                "Folder",
                lambda file: manager.create_folder(file),
                owner=OWNER,
            )
            self.file, path = _office_file(OWNER, self.folder.name, self.folder.file_url)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))

    def tearDown(self):
        frappe.flags.mute_drive_activity_log = False
        super().tearDown()

    def _request(self, token: str, method: str = "GET", data: bytes = b""):
        """Collabora calls in with no session: the token is the whole identity."""
        builder = EnvironBuilder(
            path=f"/wopi/files/{self.file.name}",
            method=method,
            headers={"X-WOPI-Access-Token": token},
            data=data,
        )
        frappe.local.request = Request(builder.get_environ())

    def _grant(self, user: str, **rights) -> None:
        frappe.get_doc(
            {"doctype": "Drive Permission", "entity": self.file.name, "user": user, **rights}
        ).insert(ignore_permissions=True)

    def test_get_file_refuses_a_token_whose_user_lost_read(self):
        token = generate_wopi_token(self.file.name, user=INTRUDER, can_write=False)
        self._request(token["access_token"])

        with self.assertRaises(frappe.PermissionError):
            endpoints.get_file(self.file.name)

    def test_put_file_refuses_a_token_whose_user_lost_write(self):
        """The token still says can_write; the share behind it is gone."""
        self._grant(INTRUDER, read=1)
        token = generate_wopi_token(self.file.name, user=INTRUDER, can_write=True)
        self._request(token["access_token"], method="POST", data=b"NEW BYTES")

        with self.assertRaises(frappe.PermissionError):
            endpoints.put_file(self.file.name)

        path = FileManager().site_folder / storage_key(self.file.file_url)
        with open(path, "rb") as fh:
            self.assertEqual(fh.read(), b"DOCX", "the refusal must precede the write")

    def test_check_file_info_downgrades_a_stale_write_token(self):
        self._grant(INTRUDER, read=1)
        token = generate_wopi_token(self.file.name, user=INTRUDER, can_write=True)
        self._request(token["access_token"])

        endpoints.check_file_info(self.file.name)

        self.assertFalse(frappe.response["UserCanWrite"])
        self.assertEqual(frappe.response["BaseFileName"], self.file.file_name)

    def test_the_owner_still_reads_and_writes(self):
        """The positive control: re-checking must not break the normal session."""
        token = generate_wopi_token(self.file.name, user=OWNER, can_write=True)

        self._request(token["access_token"])
        endpoints.get_file(self.file.name)
        self.assertEqual(frappe.response.filecontent, b"DOCX")

        self._request(token["access_token"], method="POST", data=b"NEW BYTES")
        endpoints.put_file(self.file.name)

        path = FileManager().site_folder / storage_key(self.file.file_url)
        with open(path, "rb") as fh:
            self.assertEqual(fh.read(), b"NEW BYTES")


class TestCollaboraStatusIsReadOnly(IntegrationTestCase):
    """Starting a 400 MB daemon is not something a status check does, and not
    something an anonymous visitor gets to trigger."""

    def test_the_status_endpoint_no_longer_answers_guests(self):
        self.assertIn(discovery.check_collabora_status, frappe.whitelisted)
        self.assertNotIn(discovery.check_collabora_status, frappe.guest_methods)

    def test_the_status_check_never_starts_the_daemon(self):
        with (
            patch("suite.drive.wopi.discovery.is_wopi_enabled", return_value=True),
            patch("suite.drive.wopi.discovery._can_connect_socket", return_value=False),
            patch("suite.drive.wopi.discovery._record_activity") as record_activity,
            patch("suite.drive.wopi.discovery.ensure_collabora_running") as ensure_running,
        ):
            status = discovery.collabora_status(start_if_down=False)

        ensure_running.assert_not_called()
        record_activity.assert_not_called()
        self.assertEqual(status["status"], "error")

    def test_a_running_daemon_is_still_read_by_a_status_check(self):
        """The cache is a Redis key: empty after every flush and every deploy. A
        read-only caller must still be able to READ a daemon that is already up."""
        xml = b'<discovery><net-zone><app name="x"><action name="edit" ext="docx"/></app></net-zone></discovery>'
        response = type("R", (), {"content": xml, "raise_for_status": lambda self: None})()

        with (
            patch("suite.drive.wopi.discovery.is_wopi_enabled", return_value=True),
            patch("suite.drive.wopi.discovery._can_connect_socket", return_value=True),
            patch.object(frappe.cache(), "get_value", return_value=None),
            patch("suite.drive.wopi.discovery.requests.get", return_value=response) as fetch,
            patch("suite.drive.wopi.discovery.ensure_collabora_running") as ensure_running,
        ):
            self.assertIsNotNone(discovery.get_discovery_xml(start_if_down=False))

        fetch.assert_called_once()
        ensure_running.assert_not_called()

    def test_the_editor_open_path_may_still_start_the_daemon(self):
        with (
            patch("suite.drive.wopi.discovery.is_wopi_enabled", return_value=True),
            patch("suite.drive.wopi.discovery._can_connect_socket", return_value=False),
            patch(
                "suite.drive.wopi.discovery.ensure_collabora_running", return_value=False
            ) as ensure_running,
        ):
            self.assertIsNone(discovery.get_discovery_xml(start_if_down=True))

        ensure_running.assert_called_once()

    def test_a_cached_hit_does_not_keep_a_daemon_alive_for_a_status_check(self):
        with (
            patch("suite.drive.wopi.discovery.is_wopi_enabled", return_value=True),
            patch("suite.drive.wopi.discovery._can_connect_socket", return_value=True),
            patch("suite.drive.wopi.discovery._record_activity") as record_activity,
            patch.object(frappe.cache(), "get_value", return_value=b"<discovery></discovery>"),
        ):
            self.assertIsNotNone(discovery.get_discovery_xml(start_if_down=False))
            record_activity.assert_not_called()

            self.assertIsNotNone(discovery.get_discovery_xml(start_if_down=True))
            record_activity.assert_called_once()

# //// Neoffice — added file (no upstream equivalent): the boundaries of the Drive and its files that the audit of
# //// 06.11.2026 found open (neoffice-maintenance#2296). Each test plays the person who acts in real life (a desk
# //// colleague, a portal customer, a visitor) next to the legitimate use the fix keeps working.
from __future__ import annotations

import io
import os
import tarfile
import tempfile
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.tests.roles import as_role
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from suite.drive.api.files import _collect_download_files, create_folder, ensure_path, upload_file
from suite.drive.api.permissions import user_has_permission
from suite.drive.utils import (
    GENERAL_USER,
    ROOT_FOLDER,
    create_drive_file,
    get_principals,
    get_root_folder,
    get_user_folder,
    get_valid_breadcrumbs,
)
from suite.drive.utils.files import FileManager, storage_key
from suite.utils.file import extract_compressed_file

OWNER = "sb-drive-owner@yopmail.com"
COLLEAGUE = "sb-drive-colleague@yopmail.com"
CUSTOMER = "sb-drive-customer@yopmail.com"


def _grant(entity: str, user: str, **rights) -> None:
    frappe.get_doc({"doctype": "Drive Permission", "entity": entity, "user": user, **rights}).insert(
        ignore_permissions=True
    )


def _blob(name: str, folder: str, content: bytes = b"bytes") -> frappe._dict:
    """A file with bytes behind it, in `folder`, owned by the session user."""
    folder_url = frappe.db.get_value("File", folder, "file_url")
    file = create_drive_file(name, folder, "Text", f"{folder_url}{name}", "text/plain", len(content))
    path = FileManager().site_folder / storage_key(file.file_url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return file


class DriveCase(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.flags.mute_drive_activity_log = True
        # the people: two desk colleagues and a portal customer (a Website User)
        for email, persona in (
            (OWNER, "sales_user"),
            (COLLEAGUE, "sales_user"),
            (CUSTOMER, "portal_customer"),
        ):
            with as_role(persona, email=email):
                pass
            # as every account of the site, they hold Suite User too (suite/utils/user.py, assign_suite_role)
            user = frappe.get_doc("User", email)
            user.append("roles", {"role": "Suite User"})
            user.save(ignore_permissions=True)
            with as_role(email):
                get_user_folder(email)
        get_root_folder()

    def setUp(self):
        frappe.flags.mute_drive_activity_log = True
        self.manager = FileManager()

    def folder(self, name: str | None = None, parent: str | None = None):
        parent = parent or get_user_folder().name
        return create_folder(name or f"sb-{frappe.generate_hash(length=8)}", parent)

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
            with patch("suite.drive.api.files.frappe.publish_realtime"):
                yield
        finally:
            for key in values:
                frappe.form_dict.pop(key, None)
            del frappe.local.request


class TestNamesStayInsideTheDrive(DriveCase):
    """#3: a folder named ".." climbed out of the Drive, and an upload below it wrote anywhere."""

    def test_a_folder_called_dot_dot_is_refused_and_a_real_one_is_made(self):
        with as_role(OWNER):
            home = get_user_folder().name
            for name in ("..", ".", ""):
                with self.assertRaises(frappe.ValidationError):
                    create_folder(name, home)
            made = self.folder(f"Devis {frappe.generate_hash(length=6)}", home)
        self.assertTrue((self.manager.site_folder / storage_key(made.file_url)).is_dir())
        self.assertFalse(frappe.db.exists("File", {"folder": home, "file_name": ".."}))

    def test_an_upload_whose_path_climbs_is_refused_and_writes_nothing(self):
        planted = Path(frappe.get_app_path("suite")) / "sb_planted.py"
        with as_role(CUSTOMER):
            home = get_user_folder().name
            with self.upload_request(b"print('x')", "sb_planted.py"):
                with self.assertRaises(frappe.ValidationError):
                    upload_file(
                        total_file_size=10,
                        parent=home,
                        fullpath="../../../../../../apps/suite/suite/sb_planted.py",
                    )
        self.assertFalse(planted.exists())
        self.assertFalse(frappe.db.exists("File", {"folder": home, "file_name": ".."}))

    def test_an_upload_into_its_own_subfolders_still_lands(self):
        with as_role(OWNER):
            home = get_user_folder().name
            top = f"Projets {frappe.generate_hash(length=6)}"
            with self.upload_request(b"hello", "note.txt"):
                file = upload_file(total_file_size=5, parent=home, fullpath=f"{top}/2026/note.txt")
        path = self.manager.site_folder / storage_key(file.file_url)
        self.assertEqual(path.read_bytes(), b"hello")
        self.assertIn(f"{top}/2026/note.txt", str(path))

    def test_a_dot_dot_row_cannot_be_saved_nor_a_climbing_key_be_made(self):
        with as_role(OWNER):
            home = get_user_folder().name
            with self.assertRaises(frappe.ValidationError):
                ensure_path("../escape/file.txt", home)
            with self.assertRaises(frappe.ValidationError):
                create_drive_file("..", home, "Folder", lambda file: "private/files/x/")
        with self.assertRaises(frappe.ValidationError):
            self.manager.place_in_tree("private/files/Users/x/../../../../apps/suite/x.py")
        with self.assertRaises(frappe.ValidationError):
            self.manager.place_in_tree("apps/suite/x.py")


class TestArchiveImportKeepsItsMembersInside(DriveCase):
    """#18: a link member of a .tgz, followed by a member below it, wrote outside the import directory."""

    def _tgz(self, build) -> str:
        handle, path = tempfile.mkstemp(suffix=".tgz", dir=frappe.get_site_path("private", "files"))
        os.close(handle)
        with tarfile.open(path, "w:gz") as archive:
            build(archive)
        self.addCleanup(os.remove, path)
        return path

    def test_a_link_member_is_refused_and_plain_members_extract(self):
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: [p.unlink() for p in outside.iterdir()] and None)

        def evil(archive):
            link = tarfile.TarInfo("lnk")
            link.type = tarfile.SYMTYPE
            link.linkname = str(outside)
            archive.addfile(link)
            payload = tarfile.TarInfo("lnk/sb_planted.txt")
            payload.size = 3
            archive.addfile(payload, io.BytesIO(b"bad"))

        def plain(archive):
            folder = tarfile.TarInfo("mails")
            folder.type = tarfile.DIRTYPE
            archive.addfile(folder)
            mail = tarfile.TarInfo("mails/1.eml")
            mail.size = 5
            archive.addfile(mail, io.BytesIO(b"hello"))

        with as_role(OWNER):
            destination = tempfile.mkdtemp()
            with self.assertRaises(frappe.ValidationError):
                extract_compressed_file(self._tgz(evil), destination)
            self.assertFalse((outside / "sb_planted.txt").exists())

            destination = tempfile.mkdtemp()
            extract_compressed_file(self._tgz(plain), destination)
            self.assertEqual((Path(destination) / "mails" / "1.eml").read_bytes(), b"hello")


class TestOwnerIsNotTheCallersToChange(DriveCase):
    """#4: `owner` set through the document API took over a File, a Sheet, a Writer Template or a Presentation."""

    def test_a_reader_cannot_make_himself_the_owner_of_a_file(self):
        with as_role(OWNER):
            file = _blob(f"sb-{frappe.generate_hash(length=6)}.txt", get_user_folder().name)
        _grant(file.name, COLLEAGUE, read=1)
        with as_role(COLLEAGUE):
            doc = frappe.get_doc("File", file.name)
            doc.update({"owner": COLLEAGUE})
            with self.assertRaises(frappe.PermissionError):
                doc.save()
            self.assertFalse(user_has_permission(file.name, "write"))
        self.assertEqual(frappe.db.get_value("File", file.name, "owner"), OWNER)
        # the owner still saves the file as before
        with as_role(OWNER):
            doc = frappe.get_doc("File", file.name)
            doc.file_modified = frappe.utils.now()
            doc.save()

    def test_a_sheet_and_a_template_stay_their_owners(self):
        with as_role(OWNER):
            sheet = frappe.get_doc({"doctype": "Sheet", "title": "sb owner"}).insert()
            template = frappe.get_doc(
                {
                    "doctype": "Writer Template",
                    "title": f"sb owner {frappe.generate_hash(length=6)}",
                    "content": "x",
                }
            ).insert()
        for doc in (sheet, template):
            with as_role(COLLEAGUE):
                theirs = frappe.get_doc(doc.doctype, doc.name)
                theirs.update({"owner": COLLEAGUE})
                with self.assertRaises(frappe.PermissionError):
                    theirs.save()
            self.assertEqual(frappe.db.get_value(doc.doctype, doc.name, "owner"), OWNER)
        with as_role(OWNER):
            mine = frappe.get_doc("Sheet", sheet.name)
            mine.title = "sb owner renamed"
            mine.save()


class TestTheSharedTreeIsTheCompanys(DriveCase):
    """#5: a portal customer read the company's shared Drive through the `$GENERAL` read row of its root."""

    def test_a_portal_customer_does_not_read_the_shared_tree_and_a_colleague_does(self):
        self.assertNotIn(GENERAL_USER, get_principals(CUSTOMER))
        self.assertIn(GENERAL_USER, get_principals(COLLEAGUE))
        self.assertFalse(user_has_permission(ROOT_FOLDER, "read", CUSTOMER))
        self.assertTrue(user_has_permission(ROOT_FOLDER, "read", COLLEAGUE))
        # what is shared with the customer by name stays theirs
        with as_role(OWNER):
            file = _blob(f"sb-{frappe.generate_hash(length=6)}.txt", get_user_folder().name)
        _grant(file.name, CUSTOMER, read=1)
        self.assertTrue(user_has_permission(file.name, "read", CUSTOMER))
        with as_role(CUSTOMER):
            from suite.drive.api.list import files as list_files

            with self.assertRaises(frappe.PermissionError):
                list_files(entity_name=ROOT_FOLDER)


class TestAFileIsMadePublicByWhoMayShareIt(DriveCase):
    """#28: a collaborator with `write` only made a file public with a made-up attachment reference."""

    def test_write_without_share_cannot_expose_and_the_owner_can(self):
        with as_role(OWNER):
            file = _blob(f"sb-{frappe.generate_hash(length=6)}.txt", get_user_folder().name)
        _grant(file.name, COLLEAGUE, read=1, write=1)
        with as_role(COLLEAGUE):
            # a document of their own, which they may write: frappe's reference check alone lets it through
            todo = frappe.get_doc({"doctype": "ToDo", "description": "sb exposure"}).insert()
            doc = frappe.get_doc("File", file.name)
            doc.update({"is_private": 0, "attached_to_doctype": "ToDo", "attached_to_name": todo.name})
            # the stock File rows let role All write any File, and the Drive's hook decides (write: yes); a site whose
            # Custom DocPerm keeps All to its own Files (osiris) refuses earlier, which is not what is tested here
            with patch("frappe.model.document.Document.check_permission"):
                with self.assertRaises(frappe.PermissionError):
                    doc.save()
        self.assertEqual(frappe.db.get_value("File", file.name, "is_private"), 1)
        self.assertFalse(user_has_permission(file.name, "read", "Guest"))
        # the owner holds `share`: they still attach their file to their own document
        with as_role(OWNER):
            todo = frappe.get_doc({"doctype": "ToDo", "description": "sb exposure owner"}).insert()
            doc = frappe.get_doc("File", file.name)
            doc.update({"attached_to_doctype": "ToDo", "attached_to_name": todo.name})
            doc.save()
        self.assertEqual(frappe.db.get_value("File", file.name, "attached_to_name"), todo.name)


class TestTheFolderDownloadTakesEachFileOnce(DriveCase):
    """#32: one readable file named twenty thousand times made a zip of twenty thousand copies."""

    def test_a_file_named_many_times_goes_in_once(self):
        with as_role(OWNER):
            folder = self.folder()
            file = _blob("one.txt", folder.name)
            files = list(_collect_download_files([file.name] * 50 + [folder.name]))
        self.assertEqual([entity.name for _arcname, entity in files], [file.name])


class TestBreadcrumbsStopWhereReadingStops(DriveCase):
    """#47: a holder of `write` on a shared subfolder got the names of the owner's private folders above it."""

    def test_a_colleague_sees_the_shared_folder_down_and_the_owner_his_home(self):
        with as_role(OWNER):
            tag = frappe.generate_hash(length=6)
            private = self.folder(f"sb-private-{tag}")
            shared = self.folder(f"sb-shared-{tag}", private.name)
            leaf = _blob("leaf.txt", shared.name)
        _grant(shared.name, COLLEAGUE, read=1, write=1)
        with as_role(COLLEAGUE):
            from suite.drive.api.permissions import get_user_access

            crumbs = get_valid_breadcrumbs(leaf.name, get_user_access(leaf.name))
        names = [crumb["file_name"] for crumb in crumbs]
        self.assertEqual(names, [f"sb-shared-{tag}", "leaf.txt"])
        with as_role(OWNER):
            crumbs = get_valid_breadcrumbs(leaf.name, get_user_access(leaf.name))
        self.assertEqual(
            [crumb["file_name"] for crumb in crumbs],
            ["Home", f"sb-private-{tag}", f"sb-shared-{tag}", "leaf.txt"],
        )


class TestALinkOpensOneDocumentAndListsNone(DriveCase):
    """#21: the list query of Writer Document counted the "anyone with the link" principal: a visitor listed them all."""

    def test_a_visitor_lists_no_link_shared_document_but_opens_one(self):
        from suite.writer.api.docs import create_document

        with as_role(OWNER):
            entity = create_document(f"sb link {frappe.generate_hash(length=6)}")
        entity_name = entity.get("name") if isinstance(entity, dict) else entity.name
        docname = frappe.db.get_value("File", entity_name, "content_docname")
        _grant(entity_name, "", read=1)
        with as_role("Guest"):
            self.assertNotIn(docname, frappe.get_list("Writer Document", pluck="name", limit_page_length=0))
            self.assertTrue(frappe.has_permission("Writer Document", "read", doc=docname))
        with as_role(OWNER):
            self.assertIn(docname, frappe.get_list("Writer Document", pluck="name", limit_page_length=0))


class TestAnUploadIsWeighedFromItsFirstChunk(DriveCase):
    """#33: the chunks of an upload grew a staging file with no quota and no limit until the last one came."""

    def test_an_undeclared_or_overflowing_chunk_is_refused_and_a_real_one_lands(self):
        with as_role(CUSTOMER):
            home = get_user_folder().name
            first = {"chunk_index": "0", "total_chunk_count": "2", "chunk_byte_offset": "0"}
            with self.upload_request(b"x" * 10, "big.bin", **first):
                with self.assertRaises(frappe.ValidationError):
                    upload_file(total_file_size=0, parent=home)
            with self.upload_request(b"x" * 10, "big.bin", **first):
                with self.assertRaises(frappe.ValidationError):
                    upload_file(total_file_size=4, parent=home)
            with patch("suite.drive.api.files.validate_quota", side_effect=frappe.ValidationError("full")):
                with self.upload_request(b"x" * 10, "big.bin", **first):
                    with self.assertRaises(frappe.ValidationError):
                        upload_file(total_file_size=20, parent=home)
            session = frappe.generate_hash(length=12)
            name = f"two-{frappe.generate_hash(length=6)}.bin"
            with self.upload_request(b"a" * 5, name, uuid=session, **first):
                self.assertIsNone(upload_file(total_file_size=10, parent=home))
            second = {"chunk_index": "1", "total_chunk_count": "2", "chunk_byte_offset": "5"}
            with self.upload_request(b"b" * 5, name, uuid=session, **second):
                file = upload_file(total_file_size=10, parent=home)
        self.assertEqual((self.manager.site_folder / storage_key(file.file_url)).read_bytes(), b"aaaaabbbbb")


class TestMailUploadStaysWithinTheLargestFile(DriveCase):
    """#29: a chunk sent at a huge offset made a sparse file that the endpoint read whole into memory."""

    def test_a_chunk_past_the_largest_file_is_refused_before_anything_is_read(self):
        from suite.mail.api.mail import upload_file as mail_upload_file

        builder = EnvironBuilder(
            path="/api/method/suite.mail.api.mail.upload_file",
            method="POST",
            data={"file": (BytesIO(b"x"), "sp.bin")},
        )
        values = {
            "chunk_index": "0",
            "total_chunk_count": "1",
            "chunk_byte_offset": str(200 * 1024 * 1024),
            "total_file_size": "0",
            "is_private": 1,
        }
        with as_role(OWNER):
            frappe.local.request = Request(builder.get_environ())
            frappe.form_dict.update(values)
            try:
                with patch("pathlib.Path.read_bytes", side_effect=AssertionError("the sparse file was read")):
                    with self.assertRaises(frappe.ValidationError):
                        mail_upload_file()
            finally:
                for key in values:
                    frappe.form_dict.pop(key, None)
                del frappe.local.request
        self.assertFalse(Path(frappe.get_site_path("private", "files", ".temp-sp.bin")).exists())


class TestSmallBoundaries(DriveCase):
    """#35, #39, #44, #46, #30: an avatar's size, the webp conversion, a disabled editor, the WOPI secret, the S3 endpoint."""

    def test_an_avatar_is_drawn_at_most_at_the_largest_size(self):
        from suite.mail.api import mail

        with (
            patch.object(mail.pydenticon, "Generator") as generator,
            patch.object(mail, "get_config", return_value=0),
        ):
            generator.return_value.generate.return_value = b"png"
            with as_role(CUSTOMER):
                mail.get_avatar(f"sb-{frappe.generate_hash(length=8)}@example.invalid", size=30000)
        args = generator.return_value.generate.call_args.args
        self.assertEqual(args[1:3], (mail.AVATAR_MAX_SIZE, mail.AVATAR_MAX_SIZE))

    def test_the_webp_conversion_asks_for_write_first(self):
        from suite.slides.doctype.presentation.presentation import get_webp_doc

        with as_role(OWNER):
            presentation = frappe.get_doc({"doctype": "Presentation", "title": "sb webp"}).insert()
        with as_role(COLLEAGUE):
            with self.assertRaises(frappe.PermissionError):
                get_webp_doc(presentation.name, {"file_url": "/private/files/sb-nothing.png"})

    def test_a_disabled_account_holds_no_editor_token(self):
        from suite.drive.wopi.endpoints import check_token_permission

        with as_role(OWNER):
            file = _blob(f"sb-{frappe.generate_hash(length=6)}.txt", get_user_folder().name)
        self.assertTrue(check_token_permission(frappe.get_doc("File", file.name), {"user_id": OWNER}, "read"))
        frappe.db.set_value("User", OWNER, "enabled", 0)
        try:
            self.assertFalse(
                check_token_permission(frappe.get_doc("File", file.name), {"user_id": OWNER}, "read")
            )
        finally:
            frappe.db.set_value("User", OWNER, "enabled", 1)

    def test_a_reminted_wopi_secret_is_stored_encrypted(self):
        from suite.drive.wopi.token import _persist_jwt_secret

        settings = frappe.get_single("WOPI Settings")
        try:
            previous = settings.get_password("jwt_secret", raise_exception=False)
        except Exception:
            previous = None
        secret = frappe.generate_hash(length=32)
        try:
            self.assertTrue(_persist_jwt_secret(settings, secret))
            self.assertNotEqual(frappe.db.get_single_value("WOPI Settings", "jwt_secret"), secret)
            self.assertEqual(frappe.get_single("WOPI Settings").get_password("jwt_secret"), secret)
        finally:
            if previous:
                _persist_jwt_secret(frappe.get_single("WOPI Settings"), previous)

    def test_a_suite_admin_cannot_point_the_storage_at_an_internal_host(self):
        admin = "sb-drive-suite-admin@yopmail.com"
        with as_role("sales_user", email=admin):
            pass
        user = frappe.get_doc("User", admin)
        user.append("roles", {"role": "Suite Admin"})
        user.save(ignore_permissions=True)
        with as_role(admin):
            settings = frappe.get_single("Drive Disk Settings")
            for url in ("http://169.254.169.254/latest", "http://127.0.0.1:9000", "file:///etc/passwd"):
                settings.endpoint_url = url
                with self.assertRaises(frappe.ValidationError):
                    settings._validate_endpoint_url()
            settings.endpoint_url = "http://169.254.169.254/latest"
            with self.assertRaises(frappe.ValidationError):
                settings.save()
            settings = frappe.get_single("Drive Disk Settings")
            settings.endpoint_url = "https://s3.pub1.infomaniak.cloud"
            settings._validate_endpoint_url()


class TestTheDirectoryIsTheCompanys(DriveCase):
    """#7: Drive's user picker gave every account, portal customers included, the whole user directory."""

    def test_a_portal_customer_lists_nobody_and_a_colleague_lists_the_colleagues(self):
        from suite.drive.api.product import get_user_groups, get_users

        with as_role(CUSTOMER):
            self.assertEqual(get_users(), [])
            self.assertEqual(get_user_groups(), [])
        with as_role(COLLEAGUE):
            names = {user.name for user in get_users()}
            self.assertIsInstance(get_user_groups(), list)
        self.assertIn(OWNER, names)


class TestFavouritesRecentsAndNotificationsAreTheirPersons(DriveCase):
    """#20: another user's favourite, recent or notification was read, rewritten or removed by its name, and a
    notification could be created in anyone's inbox in anyone's name."""

    def test_the_rows_answer_their_person_only(self):
        from suite.drive.api.permissions import (
            drive_entity_log_has_permission,
            drive_favourite_has_permission,
            drive_notification_has_permission,
        )

        with as_role(OWNER):
            file = _blob(f"sb-{frappe.generate_hash(length=6)}.txt", get_user_folder().name)
            favourite = frappe.get_doc(
                {"doctype": "Drive Favourite", "entity": file.name, "user": OWNER}
            ).insert()
            recent = frappe.get_doc(
                {
                    "doctype": "Drive Entity Log",
                    "entity_name": file.name,
                    "user": OWNER,
                    "last_interaction": frappe.utils.now(),
                }
            ).insert()
        _grant(file.name, COLLEAGUE, read=1)
        with as_role(OWNER):
            notification = frappe.get_doc(
                {
                    "doctype": "Drive Notification",
                    "from_user": OWNER,
                    "to_user": COLLEAGUE,
                    "type": "Share",
                    "notif_doctype": "File",
                    "notif_doctype_name": file.name,
                }
            ).insert()
        for check, row in (
            (drive_favourite_has_permission, favourite),
            (drive_entity_log_has_permission, recent),
        ):
            for ptype in ("read", "write", "delete"):
                self.assertTrue(check(frappe.get_doc(row.doctype, row.name), ptype, OWNER))
                self.assertFalse(check(frappe.get_doc(row.doctype, row.name), ptype, COLLEAGUE))
            # a row handed to oneself by a save is still the other person's
            taken = frappe.get_doc(row.doctype, row.name)
            taken.user = COLLEAGUE
            self.assertFalse(check(taken, "write", COLLEAGUE))
        stored = frappe.get_doc("Drive Notification", notification.name)
        self.assertTrue(drive_notification_has_permission(stored, "read", COLLEAGUE))
        self.assertTrue(drive_notification_has_permission(stored, "delete", COLLEAGUE))
        self.assertTrue(drive_notification_has_permission(stored, "read", OWNER))
        self.assertFalse(drive_notification_has_permission(stored, "delete", OWNER))
        self.assertFalse(drive_notification_has_permission(stored, "read", CUSTOMER))
        forged = frappe.get_doc(
            {
                "doctype": "Drive Notification",
                "from_user": OWNER,
                "to_user": COLLEAGUE,
                "type": "Share",
                "message": "sb forged",
                "notif_doctype": "File",
                "notif_doctype_name": file.name,
            }
        )
        # in another person's name, or about a file the recipient cannot read, nobody creates one
        self.assertFalse(drive_notification_has_permission(forged, "create", CUSTOMER))
        forged.from_user = CUSTOMER
        forged.to_user = COLLEAGUE
        self.assertFalse(drive_notification_has_permission(forged, "create", CUSTOMER))
        forged.from_user, forged.to_user = OWNER, COLLEAGUE
        self.assertTrue(drive_notification_has_permission(forged, "create", OWNER))
        # and through the document API, where the hooks answer
        with as_role(COLLEAGUE):
            self.assertFalse(frappe.has_permission("Drive Favourite", "read", doc=favourite.name))
            self.assertFalse(frappe.has_permission("Drive Entity Log", "delete", doc=recent.name))
            with self.assertRaises(frappe.PermissionError):
                frappe.delete_doc("Drive Favourite", favourite.name)
        with as_role(OWNER):
            self.assertTrue(frappe.has_permission("Drive Favourite", "read", doc=favourite.name))
        with as_role(CUSTOMER):
            forged = frappe.get_doc(
                {
                    "doctype": "Drive Notification",
                    "from_user": OWNER,
                    "to_user": COLLEAGUE,
                    "type": "Share",
                    "message": "sb forged",
                    "notif_doctype": "File",
                    "notif_doctype_name": file.name,
                }
            )
            with self.assertRaises(frappe.PermissionError):
                forged.insert()


class TestAnEditorSaveCountsAgainstTheOwnersStorage(DriveCase):
    """#31: a save of the Office editors wrote up to the largest file size with no quota check."""

    def test_a_save_past_the_quota_is_refused_and_one_within_lands(self):
        from suite.drive.wopi import endpoints
        from suite.drive.wopi.token import generate_wopi_token

        with as_role(OWNER):
            file = _blob(f"sb-{frappe.generate_hash(length=6)}.docx", get_user_folder().name, b"DOCX")
        _grant(file.name, COLLEAGUE, read=1, write=1)
        path = self.manager.site_folder / storage_key(file.file_url)
        token = generate_wopi_token(file.name, user=COLLEAGUE, can_write=True)["access_token"]

        def save(data: bytes):
            builder = EnvironBuilder(
                path=f"/wopi/files/{file.name}",
                method="POST",
                headers={"X-WOPI-Access-Token": token},
                data=data,
            )
            frappe.local.request = Request(builder.get_environ())
            try:
                endpoints.put_file(file.name)
            finally:
                del frappe.local.request

        # the owner has room for what they hold and a few bytes more, not for a large save by a collaborator
        used = frappe.db.sql(
            "SELECT COALESCE(SUM(file_size), 0) FROM `tabFile` WHERE owner = %s AND is_folder = 0 AND status = 'Active'",
            OWNER,
        )[0][0]
        with patch("suite.drive.api.storage.get_quota", return_value=int(used) + 100):
            with self.assertRaises(ValueError):
                save(b"x" * 1000)
            self.assertEqual(path.read_bytes(), b"DOCX")
            save(b"DOCX2")
        self.assertEqual(path.read_bytes(), b"DOCX2")

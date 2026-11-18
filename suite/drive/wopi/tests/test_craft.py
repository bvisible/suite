# //// Neoffice — added file (no upstream equivalent). The Craft editors open the Drive's Office documents:
# //// which editor takes which file, what the page is told to open it, and what a copy may be.
from __future__ import annotations

import hashlib
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from suite.drive.api.files import create_folder
from suite.drive.utils import apply_file_size_delta, get_user_folder
from suite.drive.utils.files import FileManager, storage_key
from suite.drive.wopi import craft
from suite.drive.wopi.token import validate_wopi_token

CONFIG = getattr(craft.get_craft_editor_config, "__wrapped__", craft.get_craft_editor_config)
SAVE_COPY = getattr(craft.save_copy, "__wrapped__", craft.save_copy)

# Accounts of these tests only: a desk one and a portal one, made here and removed after.
STAFF = "drive-nora-staff@example.com"
PORTAL = "drive-nora-portal@example.com"
WITH_NORA = ["frappe", "suite", "nora"]
WITHOUT_NORA = ["frappe", "suite"]


def _user(email: str, user_type: str) -> str:
    if not frappe.db.exists("User", email):
        with patch("suite.mail.events._should_provision_mail", return_value=False):
            frappe.get_doc(
                {
                    "doctype": "User",
                    "email": email,
                    "first_name": "Drive Nora",
                    "send_welcome_email": 0,
                    "user_type": user_type,
                    "roles": [{"role": "Blogger"}] if user_type == "System User" else [],
                }
            ).insert(ignore_permissions=True)
    frappe.db.set_value("User", email, {"user_type": user_type, "enabled": 1})
    return email


def _remove_user(email: str) -> None:
    frappe.set_user("Administrator")
    if frappe.db.exists("User", email):
        frappe.delete_doc("User", email, force=True, ignore_permissions=True, delete_permanently=True)


class TestWhichEditorTakesWhichFile(IntegrationTestCase):
    def test_the_office_types_open_in_their_own_editor(self):
        self.assertEqual(craft.editor_for("quote.docx"), "word")
        self.assertEqual(craft.editor_for("budget.xlsx"), "sheet")
        self.assertEqual(craft.editor_for("deck.pptx"), "deck")

    def test_the_extension_is_read_in_lower_case_and_after_the_last_dot(self):
        self.assertEqual(craft.editor_for("QUOTE.DOCX"), "word")
        self.assertEqual(craft.editor_for("report.final.docx"), "word")

    def test_a_type_no_editor_writes_back_has_no_editor_to_edit_it_in_place(self):
        for name in ("old.doc", "old.xls", "old.ppt", "text.odt", "notes", "notes."):
            self.assertIsNone(craft.editor_for(name), name)

    def test_the_types_the_editors_import_are_imported_by_the_editor_of_their_kind(self):
        """What the bridges of the builds take (EDITORS): GridCraft the workbooks and the data files, WordCraft the
        documents; DeckCraft and PdfCraft nothing but their own types."""
        for name in ("old.xls", "BOOK.XLSB", "tableau.ods", "export.csv", "export.tsv"):
            self.assertEqual(craft.importer_for(name), "sheet", name)
        for name in ("old.doc", "texte.odt", "letter.RTF"):
            self.assertEqual(craft.importer_for(name), "word", name)
        for name in ("old.ppt", "slides.odp", "quote.docx", "scan.pdf", "notes.txt", "notes", "notes."):
            self.assertIsNone(craft.importer_for(name), name)
        # asking for another editor does not make it import a type it does not take
        self.assertIsNone(craft.importer_for("old.xls", "word"))

    def test_an_import_is_saved_under_its_own_name_in_the_editor_s_type(self):
        self.assertEqual(craft.native_name("Budget 2026.xls", "sheet"), "Budget 2026.xlsx")
        self.assertEqual(craft.native_name("export.v2.csv", "sheet"), "export.v2.xlsx")
        self.assertEqual(craft.native_name("Lettre.odt", "word"), "Lettre.docx")
        # room left for the ` (n)` a taken name gets, in a File name of 140 characters
        long = craft.native_name("a" * 300 + ".csv", "sheet")
        self.assertEqual(len(long), 130)
        self.assertTrue(long.endswith(".xlsx"))
        self.assertEqual(craft.fit_name("b" * 200 + ".docx"), "b" * 125 + ".docx")
        self.assertEqual(craft.fit_name("short.docx"), "short.docx")

    def test_a_pdf_opens_in_the_pdf_editor_by_default_as_the_other_types_do(self):
        self.assertEqual(craft.editor_for("scan.pdf"), "pdf")
        self.assertEqual(craft.editor_for("SCAN.PDF"), "pdf")
        # Asking for it names the same editor (an older page asked).
        self.assertEqual(craft.editor_for("scan.pdf", "pdf"), "pdf")
        # Asking for an editor does not make it take a type it cannot write.
        self.assertIsNone(craft.editor_for("quote.docx", "pdf"))
        self.assertIsNone(craft.editor_for("quote.docx", "nonexistent"))


class TestWhatThePageIsToldToOpen(IntegrationTestCase):
    def ask(
        self,
        *,
        exists=True,
        readable=True,
        writable=True,
        file_name="quote.docx",
        version="0.6.1",
        requested=None,
        imports=0,
        uploadable=True,
    ):
        # _not_in_disk: a file whose bytes the Drive stores (craft.get_craft_editor_config, GHSA-73gm)
        document = SimpleNamespace(
            file_name=file_name, is_folder=0, folder="a-folder", _not_in_disk=lambda: False
        )

        def permission(doc, ptype, user=None):
            return {"read": readable, "upload": uploadable}.get(ptype, writable)

        with (
            patch.object(craft.frappe.db, "exists", return_value=exists),
            patch.object(craft.frappe, "get_doc", return_value=document),
            patch("suite.drive.api.permissions.user_has_permission", side_effect=permission),
            patch.object(craft, "installed_version", return_value=version),
            patch.object(
                craft, "generate_wopi_token", return_value={"access_token": "token", "access_token_ttl": 42}
            ) as mint,
        ):
            return CONFIG("a-file-id", requested, imports), mint

    def test_a_readable_document_gets_its_editor_and_a_token(self):
        answer, mint = self.ask()
        self.assertTrue(answer["available"], answer)
        self.assertEqual(answer["editor"], "word")
        self.assertEqual(answer["base_url"], "/assets/suite/craft/wordcraft/")
        self.assertEqual(answer["version"], "0.6.1")
        self.assertEqual(answer["wopi_src"], "/wopi/files/a-file-id")
        self.assertEqual((answer["access_token"], answer["access_token_ttl"]), ("token", 42))
        self.assertTrue(answer["can_write"])
        mint.assert_called_once_with("a-file-id", can_write=True)

    def test_the_editor_is_told_the_locale_of_the_person_and_the_country(self):
        """`fr-CH`: the editor shows `CHF 5'478.45` (GridCraft's number_locale), as Excel does with Swiss settings."""

        def locale(lang, country, code):
            with (
                patch.object(craft.frappe.local, "lang", lang, create=True),
                patch.object(craft.frappe.db, "get_single_value", return_value=country),
                patch.object(craft.frappe.db, "get_value", return_value=code),
            ):
                return craft.editor_locale()

        self.assertEqual(locale("fr", "Switzerland", "ch"), "fr-CH")
        self.assertEqual(locale("de", "Switzerland", "ch"), "de-CH")
        self.assertEqual(
            locale("pt-BR", "Switzerland", "ch"), "pt-CH", "the country's numbers, the person's language"
        )
        self.assertEqual(locale("fr", None, None), "", "no country: the editor takes the browser's")
        self.assertEqual(locale("fr", "Nowhere", ""), "")
        answer, _mint = self.ask()
        self.assertIn("locale", answer)

    def test_a_reader_gets_a_token_that_cannot_write(self):
        answer, mint = self.ask(writable=False)
        self.assertTrue(answer["available"], answer)
        self.assertFalse(answer["can_write"])
        mint.assert_called_once_with("a-file-id", can_write=False)

    def test_a_missing_file_and_an_unreadable_one_answer_the_same_and_mint_nothing(self):
        for kwargs in ({"exists": False}, {"readable": False}):
            answer, mint = self.ask(**kwargs)
            self.assertEqual(answer, {"available": False, "reason": "File not found"}, kwargs)
            mint.assert_not_called()

    def test_a_site_without_the_build_names_the_editor_it_lacks(self):
        # The page tells the person the editor is unavailable and offers the file: it never sends it elsewhere.
        answer, mint = self.ask(version=None)
        self.assertFalse(answer["available"])
        self.assertEqual(answer["editor"], "word")
        self.assertIn("not installed", answer["reason"])
        mint.assert_not_called()

    def test_a_type_without_an_editor_names_none(self):
        # The page goes on to upstream's viewer, which asks the person before anything leaves the site.
        for kwargs in ({"file_name": "old.ppt"}, {"file_name": "old.ppt", "imports": 1}):
            answer, mint = self.ask(**kwargs)
            self.assertFalse(answer["available"], kwargs)
            self.assertNotIn("editor", answer)
            self.assertEqual(answer["reason"], "File type not supported")
            mint.assert_not_called()

    def test_an_import_opens_in_the_editor_of_its_kind_with_a_token_that_never_writes(self):
        answer, mint = self.ask(file_name="Budget.xls", imports=1)
        self.assertTrue(answer["available"], answer)
        self.assertEqual(answer["editor"], "sheet")
        self.assertEqual(answer["base_url"], "/assets/suite/craft/gridcraft/")
        self.assertIs(answer["imported"], True)
        self.assertEqual(answer["save_as"], "Budget.xlsx")
        # the person may add the new file to the folder; the original is never written, whatever their rights on it
        self.assertTrue(answer["can_write"])
        mint.assert_called_once_with("a-file-id", can_write=False)
        answer, _mint = self.ask(file_name="lettre.odt", imports=1)
        self.assertEqual((answer["editor"], answer["save_as"]), ("word", "lettre.docx"))

    def test_can_write_of_an_import_is_the_right_to_add_a_file_to_its_folder(self):
        answer, mint = self.ask(file_name="export.csv", imports=1, writable=True, uploadable=False)
        self.assertTrue(answer["available"], answer)
        self.assertFalse(answer["can_write"])
        answer, _mint = self.ask(file_name="export.csv", imports=1, writable=False, uploadable=True)
        self.assertTrue(answer["can_write"])

    def test_a_caller_that_does_not_ask_for_imports_is_told_the_type_is_not_supported(self):
        # Neodesk's window writes a document in place: it is never handed an import it would save over the original.
        answer, mint = self.ask(file_name="Budget.xls")
        self.assertEqual(answer, {"available": False, "reason": "File type not supported"})
        mint.assert_not_called()

    def test_an_import_whose_editor_this_site_lacks_is_not_supported_rather_than_not_installed(self):
        # The page then shows the type as it did before the editors imported it (a .csv as text, a .doc in the viewer).
        answer, mint = self.ask(file_name="Budget.xls", imports=1, version=None)
        self.assertEqual(answer, {"available": False, "reason": "File type not supported"})
        mint.assert_not_called()

    def test_an_unreadable_import_answers_as_a_missing_file(self):
        answer, mint = self.ask(file_name="Budget.xls", imports=1, readable=False)
        self.assertEqual(answer, {"available": False, "reason": "File not found"})
        mint.assert_not_called()

    def test_a_document_an_editor_writes_back_is_not_an_import_when_imports_are_asked_for(self):
        answer, mint = self.ask(file_name="quote.docx", imports=1, writable=True)
        self.assertNotIn("imported", answer)
        self.assertNotIn("save_as", answer)
        mint.assert_called_once_with("a-file-id", can_write=True)


class TestNoraIsForStaff(IntegrationTestCase):
    """The editor's Nora pane is offered on the rule Nora's own endpoints apply: staff (a System User), on a site
    that has Nora. A portal account (Website User) is refused by every nora method, so it is never offered the pane."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _user(STAFF, "System User")
        _user(PORTAL, "Website User")
        cls.addClassCleanup(_remove_user, PORTAL)
        cls.addClassCleanup(_remove_user, STAFF)

    def setUp(self):
        self.addCleanup(frappe.set_user, "Administrator")

    def offered(self, user, apps=WITH_NORA):
        frappe.set_user(user)
        with patch.object(craft.frappe, "get_installed_apps", return_value=list(apps)):
            return craft.nora_for_the_person()

    def test_staff_get_the_pane_where_the_site_has_nora(self):
        self.assertTrue(self.offered(STAFF))
        self.assertTrue(self.offered("Administrator"))

    def test_a_portal_account_never_gets_it(self):
        self.assertEqual(frappe.db.get_value("User", PORTAL, "user_type"), "Website User")
        self.assertFalse(self.offered(PORTAL))

    def test_a_visitor_never_gets_it(self):
        self.assertFalse(self.offered("Guest"))

    def test_nobody_gets_it_on_a_site_without_nora(self):
        for user in (STAFF, "Administrator", PORTAL, "Guest"):
            self.assertFalse(self.offered(user, apps=WITHOUT_NORA), user)

    def test_staff_who_become_portal_accounts_lose_it(self):
        frappe.db.set_value("User", STAFF, "user_type", "Website User")
        try:
            self.assertFalse(self.offered(STAFF))
        finally:
            frappe.db.set_value("User", STAFF, "user_type", "System User")

    def config(self, user):
        """What the page of `user` is told, through the endpoint (the file and the build stood in)."""
        frappe.set_user(user)
        with (
            patch.object(craft.frappe.db, "exists", return_value=True),
            patch.object(
                craft.frappe,
                "get_doc",
                return_value=SimpleNamespace(file_name="quote.docx", is_folder=0, _not_in_disk=lambda: False),
            ),
            patch("suite.drive.api.permissions.user_has_permission", return_value=True),
            patch.object(craft, "installed_version", return_value="0.7.0"),
            patch.object(
                craft, "generate_wopi_token", return_value={"access_token": "t", "access_token_ttl": 1}
            ),
            patch.object(craft.frappe, "get_installed_apps", return_value=WITH_NORA),
        ):
            return CONFIG("a-file-id")

    def test_the_page_of_staff_is_told_to_offer_nora_and_a_portal_account_s_is_not(self):
        staff, portal = self.config(STAFF), self.config(PORTAL)
        self.assertTrue(staff["available"] and portal["available"], (staff, portal))
        self.assertIs(staff["nora"], True)
        self.assertIs(portal["nora"], False)


class TestWhatTheSiteHas(IntegrationTestCase):
    def test_only_the_installed_editors_are_listed_with_their_version(self):
        versions = {"word": "0.6.1+abc", "pdf": "0.7.1+def"}
        with patch.object(craft, "installed_version", side_effect=lambda editor: versions.get(editor)):
            self.assertEqual(craft.get_installed_editors(), versions)

    def test_a_site_with_none_lists_none(self):
        with patch.object(craft, "installed_version", return_value=None):
            self.assertEqual(craft.get_installed_editors(), {})
            self.assertEqual(craft.opened_extensions(), {})

    def test_what_opens_where_lists_the_installed_editors_types_and_imports(self):
        """What NeoMail offers to open in the Drive: every extension of an installed editor, imports included."""
        versions = {"sheet": "0.19.1", "pdf": "0.21.1"}
        with patch.object(craft, "installed_version", side_effect=lambda editor: versions.get(editor)):
            opened = craft.opened_extensions()
        self.assertEqual(
            opened,
            {
                "xlsx": "sheet",
                "xls": "sheet",
                "xlsb": "sheet",
                "ods": "sheet",
                "csv": "sheet",
                "tsv": "sheet",
                "pdf": "pdf",
            },
        )
        # the editors this site has no build of open nothing
        self.assertNotIn("docx", opened)
        self.assertNotIn("doc", opened)


class TestACopy(IntegrationTestCase):
    def test_a_name_is_cleaned_before_it_is_stored(self):
        self.assertEqual(craft.clean_file_name("../../etc/quote.docx"), "quote.docx")
        self.assertEqual(craft.clean_file_name("a\\b\\quote.docx"), "quote.docx")
        self.assertEqual(craft.clean_file_name("quote\x00\x1f.docx"), "quote.docx")
        self.assertEqual(craft.clean_file_name("  quote.docx  "), "quote.docx")
        self.assertEqual(craft.clean_file_name(""), "")

    def test_a_long_name_keeps_its_extension(self):
        cleaned = craft.clean_file_name("a" * 300 + ".docx")
        self.assertEqual(len(cleaned), 140)
        self.assertTrue(cleaned.endswith(".docx"))

    def copy(self, source_name, new_name, body=b"x"):
        source = SimpleNamespace(file_name=source_name, folder="a-folder", is_folder=0)
        request = SimpleNamespace(get_data=lambda: body)
        with (
            patch.object(craft.frappe.db, "exists", return_value=True),
            patch.object(craft.frappe.db, "get_value", return_value=source),
            patch("suite.drive.api.permissions.user_has_permission", return_value=True),
            patch.object(craft.frappe, "request", request, create=True),
        ):
            return SAVE_COPY("a-file-id", new_name)

    def test_a_copy_keeps_the_type_of_the_document(self):
        for new_name in ("copy.xlsx", "copy.exe", "copy", ""):
            with self.assertRaises(frappe.ValidationError, msg=new_name):
                self.copy("quote.docx", new_name)

    def test_an_empty_copy_is_refused(self):
        with self.assertRaises(frappe.ValidationError):
            self.copy("quote.docx", "copy.docx", body=b"")

    def test_a_copy_needs_the_right_to_upload_in_the_folder(self):
        def permission(doc, ptype, user=None):
            return ptype == "read"

        source = SimpleNamespace(file_name="quote.docx", folder="a-folder", is_folder=0)
        with (
            patch.object(craft.frappe.db, "exists", return_value=True),
            patch.object(craft.frappe.db, "get_value", return_value=source),
            patch("suite.drive.api.permissions.user_has_permission", side_effect=permission),
        ):
            with self.assertRaises(frappe.PermissionError):
                SAVE_COPY("a-file-id", "copy.docx")


# The accounts of the import tests: the owner of a folder and a desk colleague. Made here, kept from one run to the next
# with their own Drive folder, as test_drive_boundaries keeps its own; every file a test makes is removed after it.
OWNER = "drive-import-owner@example.com"
COLLEAGUE = "drive-import-colleague@example.com"
# How an .xlsx begins (a ZIP archive), then anything: the server checks the package, the editor wrote it.
XLSX_BODY = b"PK\x03\x04 the workbook the editor saved"
ORIGINAL_BYTES = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1 an Excel 97-2003 workbook"
SAVE_IMPORT = getattr(craft.save_import, "__wrapped__", craft.save_import)


def _drive_user(email: str) -> str:
    """A desk account with the role every account of the site holds (Suite User) and its own Drive folder."""
    _user(email, "System User")
    user = frappe.get_doc("User", email)
    if "Suite User" not in {row.role for row in user.roles}:
        user.append("roles", {"role": "Suite User"})
        with patch("suite.mail.events._should_provision_mail", return_value=False):
            user.save(ignore_permissions=True)
    frappe.set_user(email)
    try:
        get_user_folder(email)
    finally:
        frappe.set_user("Administrator")
    return email


def _grant(entity: str, user: str, **rights) -> None:
    """The owner shares `entity` with `user` (scenery). Without the share's notification job, which a commit would let
    into the queue (drive_permission.after_insert)."""
    with patch.object(frappe, "enqueue"):
        frappe.get_doc({"doctype": "Drive Permission", "entity": entity, "user": user, **rights}).insert(
            ignore_permissions=True
        )


class TestAnImportIsSavedAsANewFile(IntegrationTestCase):
    """An imported document (.xls, .csv, .doc…) is saved as a new file of the editor's type next to it: the original is
    never written, the name is the original's own in the new type and free in the folder, and only someone who reads
    the original and may add a file to its folder makes one."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for email in (OWNER, COLLEAGUE):
            _drive_user(email)
        frappe.db.commit()

    def setUp(self):
        frappe.flags.mute_drive_activity_log = True
        self.addCleanup(setattr, frappe.flags, "mute_drive_activity_log", False)
        self.manager = FileManager()
        if self.manager.flat or self.manager.s3_enabled:
            self.skipTest("the Drive keeps its files in a tree on this site's disk only there")
        self.suffix = frappe.generate_hash(length=8)
        self.made = []
        self.addCleanup(self.remove_made)
        with self.set_user(OWNER):
            home = get_user_folder(OWNER).name
            self.folder = create_folder(f"drive-import-{self.suffix}", home).name
            self.made.append(self.folder)
            self.original = self.store(
                f"Budget {self.suffix}.xls", ORIGINAL_BYTES, "application/vnd.ms-excel"
            )
        self.before = frappe.db.get_value(
            "File", self.original, ["file_size", "content_hash", "modified", "file_modified"], as_dict=True
        )

    def store(self, name, content, mime_type):
        """A file of the session's person in the test folder, stored as the Drive stores a new one."""
        with patch.object(craft.frappe, "publish_realtime"):
            name = craft.store_new_file(name, self.folder, mime_type, content).name
        self.made.append(name)
        return name

    def remove_made(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        # files first, their folder last; the sizes they added to the folders above them taken off again
        for name in reversed(self.made):
            row = frappe.db.get_value(
                "File", name, ["file_url", "is_folder", "folder", "file_size"], as_dict=True
            )
            if row and not row.is_folder and row.file_size:
                apply_file_size_delta(row.folder, -row.file_size)
            if row and row.file_url:
                place = self.manager.site_folder / storage_key(row.file_url)
                if row.is_folder and place.is_dir():
                    place.rmdir()
                elif place.is_file():
                    place.unlink()
            frappe.db.delete("Drive Permission", {"entity": name})
            frappe.db.delete("File", {"name": name})
        frappe.db.commit()

    def save(self, user, body=XLSX_BODY, file_id=None):
        """`user` saves `body` as the editor hands it over, for the original or `file_id`."""
        request = SimpleNamespace(get_data=lambda: body)
        with (
            self.set_user(user),
            patch.object(craft.frappe, "request", request, create=True),
            patch.object(craft.frappe, "publish_realtime"),
        ):
            answer = SAVE_IMPORT(file_id or self.original)
        self.made.append(answer["file_id"])
        return answer

    def bytes_of(self, name):
        return FileManager().get_file(frappe.get_doc("File", name)).read()

    def names_in_folder(self):
        return set(frappe.get_all("File", filters={"folder": self.folder}, pluck="file_name"))

    def assert_the_original_is_untouched(self):
        self.assertEqual(self.bytes_of(self.original), ORIGINAL_BYTES)
        after = frappe.db.get_value(
            "File", self.original, ["file_size", "content_hash", "modified", "file_modified"], as_dict=True
        )
        self.assertEqual(after, self.before)

    def test_the_owner_s_save_is_a_new_private_xlsx_of_theirs_next_to_the_original(self):
        folder_size = frappe.db.get_value("File", self.folder, "file_size")
        answer = self.save(OWNER)
        self.assertEqual(answer["file_name"], f"Budget {self.suffix}.xlsx")
        row = frappe.db.get_value(
            "File",
            answer["file_id"],
            ["folder", "owner", "is_private", "mime_type", "file_size", "content_hash"],
            as_dict=True,
        )
        self.assertEqual(row.folder, self.folder)
        self.assertEqual(row.owner, OWNER)
        self.assertEqual(row.is_private, 1)
        self.assertEqual(row.mime_type, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.assertEqual(row.file_size, len(XLSX_BODY))
        self.assertEqual(row.content_hash, hashlib.sha256(XLSX_BODY).hexdigest())
        self.assertEqual(self.bytes_of(answer["file_id"]), XLSX_BODY)
        # the folder holds it, as it holds an upload
        self.assertEqual(frappe.db.get_value("File", self.folder, "file_size"), folder_size + len(XLSX_BODY))
        self.assert_the_original_is_untouched()

    def test_a_taken_name_gets_the_first_free_one_and_the_first_file_stays(self):
        first = self.save(OWNER)
        second = self.save(OWNER, body=XLSX_BODY + b" and later")
        self.assertEqual(first["file_name"], f"Budget {self.suffix}.xlsx")
        self.assertEqual(second["file_name"], f"Budget {self.suffix} (1).xlsx")
        self.assertEqual(self.bytes_of(first["file_id"]), XLSX_BODY)
        self.assertEqual(self.bytes_of(second["file_id"]), XLSX_BODY + b" and later")
        self.assert_the_original_is_untouched()

    def test_bytes_no_row_names_are_never_written_over(self):
        """A place on the disk that holds bytes without a row (an upload whose request failed) is left as it is."""
        folder_url = frappe.db.get_value("File", self.folder, "file_url")
        stray = self.manager.site_folder / storage_key(folder_url) / f"Budget {self.suffix}.xlsx"
        stray.write_bytes(b"bytes nobody names")
        self.addCleanup(lambda: stray.unlink(missing_ok=True))
        answer = self.save(OWNER)
        self.assertEqual(answer["file_name"], f"Budget {self.suffix} (1).xlsx")
        self.assertEqual(stray.read_bytes(), b"bytes nobody names")
        self.assertEqual(self.bytes_of(answer["file_id"]), XLSX_BODY)

    def test_a_folder_in_the_trash_takes_no_new_file(self):
        frappe.db.set_value("File", self.folder, "status", "Trashed", update_modified=False)
        frappe.db.commit()
        self.addCleanup(frappe.db.commit)
        self.addCleanup(frappe.db.set_value, "File", self.folder, "status", "Active", update_modified=False)
        with self.assertRaises(frappe.ValidationError):
            self.save(OWNER)
        self.assertEqual(self.names_in_folder(), {f"Budget {self.suffix}.xls"})

    def test_a_copy_of_a_native_document_is_stored_by_the_same_rules(self):
        """Save As of an .xlsx (save_copy): a new file of its type next to it, named as asked or the first free name."""
        with self.set_user(OWNER):
            sheet = self.store(f"Sheet {self.suffix}.xlsx", XLSX_BODY, craft.MIME_TYPES["xlsx"])
        request = SimpleNamespace(get_data=lambda: XLSX_BODY + b" saved as")
        with (
            self.set_user(OWNER),
            patch.object(craft.frappe, "request", request, create=True),
            patch.object(craft.frappe, "publish_realtime"),
        ):
            answer = SAVE_COPY(sheet, f"Sheet {self.suffix}.xlsx")
        self.made.append(answer["file_id"])
        self.assertEqual(answer["file_name"], f"Sheet {self.suffix} (1).xlsx")
        self.assertEqual(self.bytes_of(answer["file_id"]), XLSX_BODY + b" saved as")
        self.assertEqual(self.bytes_of(sheet), XLSX_BODY)
        self.assertEqual(frappe.db.get_value("File", answer["file_id"], "owner"), OWNER)

    def test_a_colleague_who_may_read_the_original_but_not_add_to_its_folder_is_refused(self):
        _grant(self.original, COLLEAGUE, read=1)
        with self.assertRaises(frappe.PermissionError):
            self.save(COLLEAGUE)
        self.assertEqual(self.names_in_folder(), {f"Budget {self.suffix}.xls"})
        self.assert_the_original_is_untouched()

    def test_a_colleague_who_may_add_to_the_folder_saves_a_file_of_their_own(self):
        _grant(self.folder, COLLEAGUE, read=1, upload=1)
        answer = self.save(COLLEAGUE)
        self.assertEqual(frappe.db.get_value("File", answer["file_id"], "owner"), COLLEAGUE)
        self.assert_the_original_is_untouched()

    def test_someone_who_cannot_read_the_original_is_told_it_does_not_exist(self):
        with self.assertRaises(frappe.DoesNotExistError):
            self.save(COLLEAGUE)
        self.assertEqual(self.names_in_folder(), {f"Budget {self.suffix}.xls"})

    def test_what_is_not_an_office_package_is_refused_and_nothing_is_stored(self):
        for body in (b"col1;col2\n1;2\n", b"{\\rtf1 a letter}", b""):
            with self.subTest(body=body), self.assertRaises(frappe.ValidationError):
                self.save(OWNER, body=body)
        self.assertEqual(self.names_in_folder(), {f"Budget {self.suffix}.xls"})
        self.assert_the_original_is_untouched()

    def test_a_type_no_editor_imports_is_refused(self):
        with self.set_user(OWNER):
            native = self.store(f"Quote {self.suffix}.docx", XLSX_BODY, craft.MIME_TYPES["docx"])
            text = self.store(f"Notes {self.suffix}.txt", b"notes", "text/plain")
        for name in (native, text):
            with self.subTest(name=name), self.assertRaises(frappe.ValidationError):
                self.save(OWNER, file_id=name)
        self.assertEqual(
            self.names_in_folder(),
            {f"Budget {self.suffix}.xls", f"Quote {self.suffix}.docx", f"Notes {self.suffix}.txt"},
        )

    def test_the_save_counts_against_the_person_s_quota(self):
        full = {"limit": 100, "total_size": 100 - len(XLSX_BODY) + 1}
        with (
            patch("suite.drive.api.storage.get_storage_usage", return_value=full),
            self.assertRaises(ValueError),
        ):
            self.save(OWNER)
        self.assertEqual(self.names_in_folder(), {f"Budget {self.suffix}.xls"})

    def test_the_editor_s_token_for_an_import_reads_and_never_writes(self):
        with (
            self.set_user(OWNER),
            patch.object(craft, "installed_version", return_value="0.19.1"),
        ):
            answer = CONFIG(self.original, "", 1)
        self.assertTrue(answer["available"], answer)
        self.assertEqual((answer["imported"], answer["save_as"]), (True, f"Budget {self.suffix}.xlsx"))
        self.assertTrue(answer["can_write"])
        self.assertFalse(validate_wopi_token(answer["access_token"])["can_write"])

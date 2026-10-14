# //// Neoffice — added file (no upstream equivalent). The Craft editors open the Drive's Office documents with
# //// no Collabora: which editor takes which file, what the page is told to open it, and what a copy may be.
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from suite.drive.wopi import craft

CONFIG = getattr(craft.get_craft_editor_config, "__wrapped__", craft.get_craft_editor_config)
SAVE_COPY = getattr(craft.save_copy, "__wrapped__", craft.save_copy)


class TestWhichEditorTakesWhichFile(IntegrationTestCase):
    def test_the_office_types_open_in_their_own_editor(self):
        self.assertEqual(craft.editor_for("quote.docx"), "word")
        self.assertEqual(craft.editor_for("budget.xlsx"), "sheet")
        self.assertEqual(craft.editor_for("deck.pptx"), "deck")

    def test_the_extension_is_read_in_lower_case_and_after_the_last_dot(self):
        self.assertEqual(craft.editor_for("QUOTE.DOCX"), "word")
        self.assertEqual(craft.editor_for("report.final.docx"), "word")

    def test_a_type_no_editor_writes_back_stays_with_collabora(self):
        for name in ("old.doc", "old.xls", "old.ppt", "text.odt", "notes", "notes."):
            self.assertIsNone(craft.editor_for(name), name)

    def test_a_pdf_opens_in_the_pdf_editor_only_when_asked(self):
        self.assertIsNone(craft.editor_for("scan.pdf"))
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
    ):
        document = SimpleNamespace(file_name=file_name, is_folder=0)

        def permission(doc, ptype, user=None):
            return readable if ptype == "read" else writable

        with (
            patch.object(craft.frappe.db, "exists", return_value=exists),
            patch.object(craft.frappe, "get_doc", return_value=document),
            patch("suite.drive.api.permissions.user_has_permission", side_effect=permission),
            patch.object(craft, "installed_version", return_value=version),
            patch.object(
                craft, "generate_wopi_token", return_value={"access_token": "token", "access_token_ttl": 42}
            ) as mint,
        ):
            return CONFIG("a-file-id", requested), mint

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

    def test_a_site_without_the_build_falls_back(self):
        answer, mint = self.ask(version=None)
        self.assertFalse(answer["available"])
        self.assertIn("not installed", answer["reason"])
        mint.assert_not_called()

    def test_a_type_without_an_editor_falls_back(self):
        answer, mint = self.ask(file_name="old.doc")
        self.assertFalse(answer["available"])
        self.assertEqual(answer["reason"], "File type not supported")
        mint.assert_not_called()


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

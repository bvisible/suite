# //// Neoffice — added file (no upstream equivalent). A File that frappe writes (an attachment,
# //// a print, an upload made outside Drive) keeps frappe's storage rules under Drive's File
# //// override: is_private moves it, and a rollback removes what the transaction wrote.
from __future__ import annotations

import os
from io import BytesIO

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import get_files_path
from PIL import Image


class TestFrameworkFilesUnderDrive(IntegrationTestCase):
    def setUp(self):
        frappe.flags.mute_drive_activity_log = True

    def tearDown(self):
        frappe.flags.mute_drive_activity_log = False
        super().tearDown()

    def _file(self, is_private, **values):
        name = f"framework-file-{frappe.generate_hash(length=6)}.txt"
        return frappe.get_doc(
            {
                "doctype": "File",
                "file_name": name,
                "content": name.encode(),
                "is_private": is_private,
                **values,
            }
        ).insert(ignore_permissions=True)

    def test_marking_a_file_private_moves_it_out_of_the_public_folder(self):
        doc = self._file(is_private=0)
        public_path = doc.get_full_path()
        doc.is_private = 1
        doc.save(ignore_permissions=True)
        self.assertTrue(doc.file_url.startswith("/private/files/"), doc.file_url)
        self.assertTrue(os.path.isfile(doc.get_full_path()))
        self.assertFalse(os.path.exists(public_path))

    def test_making_an_attachment_public_moves_it_to_the_public_folder(self):
        todo = frappe.get_doc({"doctype": "ToDo", "description": "framework file"}).insert(
            ignore_permissions=True
        )
        doc = self._file(is_private=1, attached_to_doctype="ToDo", attached_to_name=todo.name)
        private_path = doc.get_full_path()
        doc.is_private = 0
        doc.save(ignore_permissions=True)
        self.assertTrue(doc.file_url.startswith("/files/"), doc.file_url)
        self.assertTrue(os.path.isfile(doc.get_full_path()))
        self.assertFalse(os.path.exists(private_path))

    def test_a_rolled_back_file_leaves_nothing_on_disk(self):
        path = self._file(is_private=1).get_full_path()
        self.assertTrue(os.path.isfile(path))
        frappe.db.rollback()
        self.assertFalse(os.path.exists(path))

    def test_a_public_image_converted_to_webp_keeps_its_new_url(self):
        # The wiki's webp conversion: a public upload's blob is replaced by a
        # sibling .webp, then file_url and file_name are pointed at it and saved.
        png = BytesIO()
        Image.new("RGB", (4, 4), "red").save(png, "PNG")
        doc = self._file(
            is_private=0,
            file_name=f"framework-file-{frappe.generate_hash(length=6)}.png",
            content=png.getvalue(),
        )
        self.assertTrue(doc.file_url.startswith("/files/"), doc.file_url)

        webp_name = f"framework-file-{frappe.generate_hash(length=6)}.webp"
        with Image.open(doc.get_full_path()) as image:
            image.save(get_files_path(webp_name), "WEBP")
        self.addCleanup(
            lambda: os.path.exists(get_files_path(webp_name)) and os.remove(get_files_path(webp_name))
        )
        os.remove(doc.get_full_path())
        doc.file_url = f"/files/{webp_name}"
        doc.file_name = webp_name
        doc.save(ignore_permissions=True)

        doc.reload()
        self.assertEqual(doc.file_url, f"/files/{webp_name}")
        self.assertTrue(os.path.isfile(get_files_path(webp_name)))

    def test_rewriting_a_private_url_to_the_public_folder_stays_refused(self):
        doc = self._file(is_private=1)
        self.assertTrue(doc.file_url.startswith("/private/files/"), doc.file_url)
        doc.is_private = 0
        doc.file_url = f"/files/{doc.file_name}"
        with self.assertRaises(frappe.ValidationError):
            doc.save(ignore_permissions=True)

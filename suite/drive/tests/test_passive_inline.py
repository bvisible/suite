# //// Neoffice — added file (no upstream equivalent). A file the Drive shows in place stays passive: an HTML or SVG
# //// file opened from its link is a sandboxed download, and the Drive's own CSP never erases the sandbox
# //// (passive_inline in suite/drive/api/files.py, apply in suite/suite_core/v15_response_headers.py).
from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from unittest import TestCase

import frappe
from werkzeug.datastructures import Headers
from werkzeug.test import EnvironBuilder
from werkzeug.utils import send_file
from werkzeug.wrappers import Response

from suite.drive.api import product
from suite.drive.api.files import passive_inline
from suite.suite_core import v15_response_headers


def sent(name: str) -> Response:
    """What get_file_internal answers for a file called `name`: werkzeug guesses the type from the name."""
    response = send_file(
        BytesIO(b"<script>alert(1)</script>"),
        as_attachment=False,
        download_name=name,
        environ=EnvironBuilder().get_environ(),
    )
    return passive_inline(response, name)


class TestPassiveInline(TestCase):
    def test_active_content_is_a_sandboxed_download(self):
        for name in ("page.html", "picture.svg", "feed.xml", "script.js", "notes.md", "blob.bin"):
            response = sent(name)
            self.assertEqual(response.headers.get("Content-Security-Policy"), "sandbox", name)
            self.assertTrue(response.headers.get("Content-Disposition", "").startswith("attachment"), name)
            self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff", name)

    def test_passive_files_stay_viewable_in_place(self):
        for name in (
            "photo.png",
            "photo.JPG",
            "invoice.pdf",
            "INVOICE.PDF",
            "readme.txt",
            "clip.mp4",
            "song.mp3",
        ):
            response = sent(name)
            self.assertNotIn("Content-Security-Policy", response.headers, name)
            self.assertFalse(response.headers.get("Content-Disposition", "").startswith("attachment"), name)
            self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff", name)

    def test_the_drives_own_policy_does_not_erase_the_sandbox(self):
        # the two hooks a request to /api/method/ goes through after the file is sent
        response = sent("page.html")
        kept = getattr(frappe.local, "response_headers", None)
        frappe.local.response_headers = Headers()
        try:
            product.after_request(SimpleNamespace(path="/api/method/suite.drive.api.files.get_file_content"))
            v15_response_headers.apply(response)
        finally:
            if kept is None:
                del frappe.local.response_headers
            else:
                frappe.local.response_headers = kept
        policies = response.headers.getlist("Content-Security-Policy")
        self.assertIn("sandbox", policies)
        self.assertTrue(any(p.startswith("frame-ancestors") for p in policies), policies)
        self.assertTrue(response.headers.get("Content-Disposition", "").startswith("attachment"))

# //// Neoffice — added file (no upstream equivalent): what the Slides media proxy lets a browser run, and what the
# //// Slides loader writes into innerHTML (neoffice-maintenance#2296).
"""The Slides media proxy streams files attached to a presentation on the app's own origin.

Images, video and audio are drawn inline as before; any other type (an uploaded .html or .svg) is sent as a
download, in a sandbox, and never sniffed into something else.
"""

from __future__ import annotations

import os
from pathlib import Path

import frappe
from frappe.tests import UnitTestCase
from frappe.tests.roles import as_role
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from suite.slides.api import file as media

FRONTEND = Path(frappe.get_app_path("suite")).parent / "frontend" / "src" / "apps" / "slides"


class TestMediaProxyHeaders(UnitTestCase):
    def setUp(self):
        self.paths = []
        self.previous = getattr(frappe.local, "request", None)
        frappe.local.request = Request(
            EnvironBuilder(path="/api/method/suite.slides.api.file.get_media_file").get_environ()
        )

    def tearDown(self):
        for path in self.paths:
            os.remove(path)
        if self.previous is None:
            del frappe.local.request
        else:
            frappe.local.request = self.previous

    def response_for(self, name: str, content: bytes):
        path = frappe.get_site_path("private", "files", name)
        Path(path).write_bytes(content)
        self.paths.append(path)
        with as_role("sales_user"):
            return media.get_media_response(f"/private/files/{name}")

    def test_an_uploaded_page_is_a_sandboxed_download(self):
        for name, content in (
            ("slides-proxy-test.html", b"<script>alert(1)</script>"),
            ("slides-proxy-test.svg", b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>'),
        ):
            with self.subTest(name=name):
                response = self.response_for(name, content)
                self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
                self.assertEqual(response.headers.get("Content-Disposition"), f"attachment; filename={name}")
                self.assertIn("sandbox", response.headers.get("Content-Security-Policy", ""))
                response.close()

    def test_slide_media_still_draws_inline(self):
        for name in ("slides-proxy-test.png", "slides-proxy-test.mp4"):
            with self.subTest(name=name):
                response = self.response_for(name, b"\x00\x01")
                self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
                self.assertEqual(response.headers.get("Content-Disposition"), f"inline; filename={name}")
                self.assertNotIn("Content-Security-Policy", response.headers)
                self.assertEqual(response.headers.get("Accept-Ranges"), "bytes")
                response.close()


class TestSlidesLoader(UnitTestCase):
    def test_text_content_is_measured_through_the_sanitizer(self):
        presentation = (FRONTEND / "stores" / "presentation.js").read_text()
        self.assertNotIn("tempDiv.innerHTML = el.content", presentation)
        self.assertIn("tempDiv.innerHTML = sanitizeSlideHTML(el.content || '')", presentation)
        element = (FRONTEND / "stores" / "element.js").read_text()
        self.assertNotIn("tempTextElement.innerHTML = html\n", element)
        self.assertIn("tempTextElement.innerHTML = sanitizeSlideHTML(html || '')", element)

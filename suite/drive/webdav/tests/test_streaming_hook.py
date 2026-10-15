# //// Neoffice — added file (no upstream equivalent): the frappe v15 fork honours `streaming_request_paths`.
"""The body of a /dav request is left unread by frappe, so the dispatcher can stream a big PUT.

Frappe v16 reads the hook `streaming_request_paths`; the v15 fork of Neoffice does since the hook was ported
(frappe/app.py, `is_streaming_request`). Without it every body was read in memory under `max_file_size`, and a WebDAV
upload past 25 MB answered 413 whatever nginx allowed.
"""

from __future__ import annotations

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request


def _request(
    path: str, *, size: int = 64, method: str = "PUT", content_type: str = "application/octet-stream"
):
    builder = EnvironBuilder(method=method, path=path, data=b"x" * size, content_type=content_type)
    return Request(builder.get_environ())


class TestStreamingRequestPaths(IntegrationTestCase):
    def test_the_suite_names_the_dav_prefix(self):
        self.assertIn("/dav/", frappe.get_hooks("streaming_request_paths"))

    def test_only_those_paths_stream(self):
        from frappe.app import is_streaming_request

        self.assertTrue(is_streaming_request(_request("/dav/Home/a.bin")))
        self.assertFalse(is_streaming_request(_request("/api/method/ping", method="POST")))
        self.assertFalse(is_streaming_request(_request("/davsomething")))
        self.assertFalse(is_streaming_request(_request("/drive/home", method="GET")))

    def test_without_an_app_that_names_a_path_nothing_streams(self):
        from frappe.app import is_streaming_request

        with patch("frappe.get_hooks", return_value=[]):
            self.assertFalse(is_streaming_request(_request("/dav/Home/a.bin")))

    def test_the_body_of_a_streaming_path_is_left_unread(self):
        from frappe.app import make_form_dict

        size = 3 * 1024 * 1024
        request = _request("/dav/Home/a.bin", size=size)
        request.max_content_length = None
        make_form_dict(request, streaming=True)
        self.assertEqual(dict(frappe.local.form_dict), {})
        # still there, for the app to read as a stream
        self.assertEqual(len(request.stream.read()), size)

    def test_the_query_string_of_a_streaming_path_is_still_parsed(self):
        from frappe.app import make_form_dict

        request = _request("/dav/Home/a.bin?x=1&_=17", size=8)
        make_form_dict(request, streaming=True)
        self.assertEqual(frappe.local.form_dict.get("x"), "1")
        self.assertNotIn("_", frappe.local.form_dict)

    def test_the_other_bodies_are_read_and_capped_as_before(self):
        from frappe.app import make_form_dict

        body = _request("/api/method/ping", size=2048, method="POST", content_type="application/json")
        body.max_content_length = 1024
        with self.assertRaises(RequestEntityTooLarge):
            make_form_dict(body)

        form = EnvironBuilder(method="POST", path="/api/method/ping", data={"a": "b"}).get_request()
        make_form_dict(form)
        self.assertEqual(frappe.local.form_dict.get("a"), "b")

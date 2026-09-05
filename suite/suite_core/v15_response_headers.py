# //// Neoffice — added file (no upstream equivalent).
"""Provide `frappe.local.response_headers` on Frappe v15.

Upstream writes response headers through `frappe.local.response_headers`, a
per-request `Headers` object that v16 creates on every request and merges into the
outgoing response. v15 has neither half, so every write raises
``AttributeError: response_headers`` — which is how /suite and /drive answered
HTTP 500 to every visitor after the merge (measured on osiris, 31.08.2026).

Six call sites in production code depend on it, and two of them are security
headers:

* ``suite/www/suite.py`` — ``X-Suite-Guest``, so the Slides service worker does not
  keep the shell as the offline app for an anonymous visitor
* ``suite/drive/api/product.py`` — ``Content-Security-Policy`` and the removal of
  ``X-Frame-Options``, which is what allows a Drive document to be embedded
* ``suite/drive/webdav/options.py`` and ``dispatch.py`` — ``DAV``,
  ``MS-Author-Via`` and the OAuth ``WWW-Authenticate`` challenge, all three
  required by the WebDAV protocol itself

A shim that merely absorbed the writes would be worse than the crash: a
Content-Security-Policy nobody applies looks exactly like one that works. So this
reproduces both halves of the v16 behaviour — the object is created on
``before_request`` and merged into the response on ``after_request``, which are
the same two points v16 uses.

Drop this module (and its two hooks) when the fleet moves to Frappe v16, where
the framework does this itself.
"""

from __future__ import annotations

import frappe


def _has_native_support() -> bool:
	"""True when the framework manages response_headers itself (v16+)."""
	return hasattr(frappe.local, "response_headers")


def create() -> None:
	"""before_request: give the request an empty Headers to write into."""
	if _has_native_support():
		return
	from werkzeug.datastructures import Headers

	frappe.local.response_headers = Headers()


def apply(response=None, request=None) -> None:
	"""after_request: copy what the request wrote onto the outgoing response.

	`extend` rather than `set`: a header may legitimately appear more than once,
	and the response may already carry one the framework set itself.
	"""
	headers = getattr(frappe.local, "response_headers", None)
	if not headers or response is None:
		return

	for key, value in headers.items():
		response.headers[key] = value

# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from frappe.model.document import Document


class DriveDAVProperty(Document):
    """A WebDAV dead property (RFC 4918 §4.4). All access goes through
    suite.drive.webdav.deadprops — never through generic doc APIs."""

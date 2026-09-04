# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from frappe.model.document import Document


class DriveDAVLock(Document):
    """A WebDAV write lock (RFC 4918 §6). DB-backed so it survives gunicorn
    worker recycling; all protocol access goes through suite.drive.webdav.locks."""

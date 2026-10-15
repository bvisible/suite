# //// Neoffice — added file (no upstream equivalent): a computer paired to keep a folder in step with the Drive.
from __future__ import annotations

import hashlib

from frappe.model.document import Document

TOKEN_PREFIX = "ndsk_"


def hash_token(token: str) -> str:
    """What is stored of a device token: its SHA-256. The token is 256 random bits, so a fast hash is enough, and
    a lookup by hash is one indexed read on every request."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class DriveSyncDevice(Document):
    """One paired computer. Created by `suite.drive.api.sync.register_device`, which hands the token over once;
    accepted by the Drive's WebDAV as a Bearer credential (suite.drive.webdav.auth); stopped by revoking it."""

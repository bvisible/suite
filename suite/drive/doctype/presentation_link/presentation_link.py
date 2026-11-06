# //// Neoffice — added file (no upstream equivalent): a link that opens a presentation of the Drive to the addresses
# //// it accepts, after a code sent by e-mail (suite/drive/presentation/).
from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import get_url

from suite.drive.presentation.rules import entry_file, new_secret, normalize_domains, normalize_emails

DEFAULT_INTRO_SECONDS = 1.2
MAX_INTRO_SECONDS = 10


class PresentationLink(Document):
    def before_insert(self):
        self.token = new_secret(18)

    def validate(self):
        self.allowed_domains = "\n".join(normalize_domains(self.allowed_domains))
        self.allowed_emails = "\n".join(normalize_emails(self.allowed_emails))
        entry_file(self.presentation)
        if not self.token:
            self.token = new_secret(18)
        self.url = get_url(f"/p/{self.token}")
        seconds = self.intro_seconds or DEFAULT_INTRO_SECONDS
        self.intro_seconds = min(max(seconds, 0), MAX_INTRO_SECONDS)
        if not self.allow_forward:
            self.forward_outside = 0
        if self.reference_name and not self.reference_doctype:
            frappe.throw(frappe._("Choose the type of the linked document."))

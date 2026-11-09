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
        self.preview_token = new_secret(18)

    def onload(self):
        """What the record's head says beside the name (presentation_link.js, the hero's detail block): sent with the
        document, so the head is drawn at once, without a second request."""
        from suite.drive.presentation.api import head_of

        self.set_onload("np_header", head_of(self))

    def validate(self):
        self.allowed_domains = "\n".join(normalize_domains(self.allowed_domains))
        self.allowed_emails = "\n".join(normalize_emails(self.allowed_emails))
        entry_file(self.presentation)
        if not self.token:
            self.token = new_secret(18)
        if not self.preview_token:
            self.preview_token = new_secret(18)
        self.url = get_url(f"/p/{self.token}")
        self.preview_url = preview_url_of(self)
        seconds = self.intro_seconds or DEFAULT_INTRO_SECONDS
        self.intro_seconds = min(max(seconds, 0), MAX_INTRO_SECONDS)
        if not self.allow_forward:
            self.forward_outside = 0
        if self.reference_name and not self.reference_doctype:
            frappe.throw(frappe._("Choose the type of the linked document."))
        from suite.drive.presentation.sources import roots_of

        self.nora_sites = "\n".join(roots_of(self))

    def on_update(self):
        # the sites Nora reads are read again when they change (sources.py); every day after that
        if self.has_value_changed("nora_sites") and self.nora_sites:
            frappe.enqueue(
                "suite.drive.presentation.sources.refresh_link",
                queue="long",
                name=self.name,
                job_id=f"presentation_sources:{self.name}",
                deduplicate=True,
                enqueue_after_commit=True,
            )


def preview_url_of(link) -> str:
    """The preview link of `link`: ours only, it opens the presentation without a code and counts nothing
    (suite/drive/presentation/renderer.py)."""
    return get_url(f"/p/{link.token}/preview/{link.preview_token}")

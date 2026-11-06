# //// Neoffice — added file (no upstream equivalent): the owner of a saved document is not the caller's to change.
"""The owner of a saved document stays the one it was created by (neoffice-maintenance#2296).

Frappe's document API (PUT /api/resource, frappe.client.save and set_value) applies the request to the document
before it checks the write right, so the check runs on the changed document. Several rights of the Suite follow
`owner`: the Drive's owner short-circuit on a File, the `if_owner` rows on Sheet, the owner test of Writer Template
and of a Presentation template. A request that set `owner` to its caller passed the check it was changing, and the
caller took the document over. Code that hands a document to someone else writes the column itself (`db_set`), and
Administrator may still do it through the API.
"""

from __future__ import annotations

import frappe
from frappe import _


def refuse_owner_change(doc) -> None:
    """Throw when a save changes the owner of a saved document (call it from `validate`)."""
    if doc.is_new() or doc.flags.allow_owner_change or frappe.session.user == "Administrator":
        return
    before = doc.get_doc_before_save()
    if before is not None and before.owner != doc.owner:
        frappe.throw(_("The owner of a document cannot be changed"), frappe.PermissionError)

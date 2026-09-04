#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe


def execute() -> None:
    """Rename the "Mail Admin" role to "Suite Admin".

    The admin role is now suite-wide. ``rename_doc`` cascades the change to the ``Has Role``
    and ``DocPerm`` rows that link to it, so existing assignments are preserved. The role is
    shipped as a fixture, but fixtures sync only after post_model_sync patches, so renaming
    here first avoids ending up with both "Mail Admin" and "Suite Admin".
    """

    if frappe.db.exists("Role", "Mail Admin") and not frappe.db.exists("Role", "Suite Admin"):
        frappe.rename_doc("Role", "Mail Admin", "Suite Admin", force=True)

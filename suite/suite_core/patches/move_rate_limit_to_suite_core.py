#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe


def execute() -> None:
    """Retag the Rate Limit DocType from the Mail module to Suite Core.

    The DocType was moved to ``suite.suite_core.doctype.rate_limit`` so it can be
    shared across modules. On upgraded sites the DocType record may still be
    stored with ``module = "Mail"``, so retag it before anything tries to resolve
    it. This is a plain DB update and never loads the relocated controller.
    """
    frappe.db.set_value("DocType", "Rate Limit", "module", "Suite Core", update_modified=False)

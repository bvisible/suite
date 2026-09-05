# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe


def execute():
    """One row per (entity, ns, prop_name) — PROPPATCH upserts assume it."""
    if not frappe.db.table_exists("Drive DAV Property"):
        return
    # idempotent: checks information_schema before issuing the DDL
    frappe.db.add_unique(
        "Drive DAV Property", ["entity", "ns", "prop_name"], constraint_name="unique_entity_prop"
    )

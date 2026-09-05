# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe

STORE_FIELDS = ["data_store", "blob_store", "search_store", "in_memory_store"]


def execute() -> None:
    """Delete Mail Cluster Store records left over from the legacy schema.

    The DocType was removed and re-introduced with a new schema, so rows created
    under the old schema must not survive model sync. Sites migrating from the
    standalone mail app, however, arrive with live store records that Mail
    Cluster links to (wiping those fails configure_mail_cluster with a
    LinkValidationError), so only rows no cluster references are deleted.
    """

    if not frappe.db.table_exists("Mail Cluster Store"):
        return

    referenced = get_referenced_store_names()

    if referenced:
        frappe.db.delete("Mail Cluster Store", {"name": ("not in", sorted(referenced))})
    else:
        # Nothing links to any store, so every row predates the new schema.
        # Old suite sites, where the DocType was removed before any cluster
        # could reference it, land here and get the original full cleanup.
        frappe.db.delete("Mail Cluster Store")


def get_referenced_store_names() -> set[str]:
    if not frappe.db.table_exists("Mail Cluster"):
        return set()

    cluster = frappe.qb.DocType("Mail Cluster")
    referenced = set()

    for field in STORE_FIELDS:
        if not frappe.db.has_column("Mail Cluster", field):
            continue

        stores = frappe.qb.from_(cluster).select(cluster[field]).distinct().run(pluck=True)
        referenced.update(store for store in stores if store)

    return referenced

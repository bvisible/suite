# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe
from frappe import _

from suite.utils import execute_with_logging


def execute() -> None:
    def _configure(server) -> None:
        doc = frappe.get_doc("Mail Server", server)
        doc.recovery_http_port = doc.recovery_http_port or 8080
        doc.bootstrap_ndjson = doc.bootstrap_ndjson or doc._generate_bootstrap_ndjson()
        doc.save()

    for server in frappe.db.get_all("Mail Server", {}, pluck="name"):
        execute_with_logging(
            func=lambda: _configure(server),
            title=_("Failed to configure Mail Server {0}").format(frappe.bold(server)),
            module="Mail",
        )

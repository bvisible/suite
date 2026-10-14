# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe


def execute():
    method_path = "suite.meet.api.meeting.validate_guest_session"
    frappe.db.delete("Rate Limit", {"method_path": method_path})
    frappe.cache.hdel("rate_limits", method_path)

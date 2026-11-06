# //// Neoffice — added file (no upstream equivalent): who reads a shared presentation's links, people, visits and
# //// questions. Only the staff (System Users). A portal account is given `Suite User` when it is created, and that
# //// role reads these DocTypes: without this, a customer of the portal listed every link and the address of every
# //// visitor through /api/resource. The visitor's page never needs them: its guest methods (api.py) read for it.
from __future__ import annotations

import frappe


def _is_staff(user: str | None) -> bool:
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    return frappe.get_cached_value("User", user, "user_type") == "System User"


def has_permission(doc=None, ptype=None, user=None, debug=False):
    """No for anyone but the staff; for the staff, the roles decide."""
    return None if _is_staff(user) else False


def query_conditions(user=None, doctype=None):
    return "" if _is_staff(user) else "1=0"

#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe

from suite.utils.user import is_administrator, is_suite_user


def has_app_permission() -> bool:
    user = frappe.session.user
    return is_administrator(user) or is_suite_user(user)

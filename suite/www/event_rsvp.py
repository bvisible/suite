# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Guest RSVP landing page.

The invitation email's Yes / Maybe / No links point here with a signed token. This page
verifies the token, records the response on the organizer's copy of the event via JMAP,
and shows a branded confirmation that auto-closes.
"""
from __future__ import annotations

import frappe
from frappe import _

from suite.calendar.api.rsvp import resolve_rsvp

no_cache = 1

# Confirmation page auto-close countdown on success (seconds; 0 disables).
AUTO_CLOSE_SECONDS = 10


def get_context(context):
    token = frappe.form_dict.get("token")
    if token:
        result = resolve_rsvp(token)
    else:
        result = {
            "success": False,
            "title": _("Invalid Link"),
            "message": _("This response link is invalid or has expired."),
        }

    context.no_cache = 1
    context.update(result)
    context.auto_close_seconds = AUTO_CLOSE_SECONDS
    return context

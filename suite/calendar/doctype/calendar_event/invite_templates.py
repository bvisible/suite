# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""On-disk event invitation email templates.

The HTML bodies live under `suite/templates/emails/` so they can be edited or replaced on
disk. Each action maps to a fixed template file and a default subject.
"""
from __future__ import annotations

TEMPLATE_DIR = "templates/emails"

# action -> template name (file under TEMPLATE_DIR without the .html extension). "response" is
# the organizer-facing notification sent when a guest RSVPs; the rest go to the guests.
DEFAULT_TEMPLATES = {
    "invite": "event_invite",
    "update": "event_update",
    "cancel": "event_cancel",
    "response": "event_response",
}

# action -> email subject (Jinja string rendered with the invite context)
DEFAULT_SUBJECTS = {
    "invite": "Invitation: {{ title }}",
    "update": "Updated: {{ title }}",
    "cancel": "Cancelled: {{ title }}",
    "response": '{{ responder_name }} responded "{{ response_label }}": {{ title }}',
}


def template_path(name: str) -> str:
    """Returns the app-relative Jinja path for an event email template name."""

    return f"{TEMPLATE_DIR}/{name}.html"

"""Sheets AI Settings — singleton vault for the AI Assist configuration.

Holds the Anthropic API key (encrypted at rest via the Password fieldtype),
the enable toggle, and the model id. The desk form is unused — configuration
happens in-app via the ``get_ai_settings`` / ``save_ai_settings`` endpoints
(see ``suite.sheets.api``). The key is never returned to the browser; the server
reads the cleartext with ``self.get_password("api_key")`` only when calling
the Anthropic API.
"""
# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations

import frappe
from frappe.model.document import Document


class SheetsAISettings(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        api_key: DF.Password | None
        enabled: DF.Check
        model: DF.Data | None
    # end: auto-generated types

    pass

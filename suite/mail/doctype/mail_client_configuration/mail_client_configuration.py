# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from frappe.model.document import Document


class MailClientConfiguration(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        connection_security: DF.Literal["SSL/TLS", "STARTTLS", "None"]
        hostname: DF.Data
        parent: DF.Data
        parentfield: DF.Data
        parenttype: DF.Data
        port: DF.Int
        protocol: DF.Literal["SMTP", "IMAP", "POP3"]
    # end: auto-generated types

    pass

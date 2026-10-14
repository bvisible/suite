# //// Neoffice — added file (no upstream equivalent): see the DocType's description and suite/calendar/local.py (maintenance#1387).
# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe
from frappe.model.document import Document


class LocalCalendar(Document):
    def autoname(self) -> None:
        # The JMAP id of the calendar: letters and digits, as the mail server's.
        self.name = frappe.generate_hash(length=12)

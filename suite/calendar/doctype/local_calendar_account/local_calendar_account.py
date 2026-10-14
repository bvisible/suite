# //// Neoffice — added file (no upstream equivalent): see the DocType's description and suite/calendar/local.py (maintenance#1387).
# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe
from frappe.model.document import Document

from suite.calendar.local import LOCAL_PREFIX


class LocalCalendarAccount(Document):
    def autoname(self) -> None:
        # The account id travels in the calendar's URLs and the Calendar doctypes split their names on "|":
        # a recognisable prefix, letters and digits only after it.
        self.name = f"{LOCAL_PREFIX}{frappe.generate_hash(length=12)}"

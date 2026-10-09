# //// Neoffice — added file (no upstream equivalent): see the DocType's description and suite/calendar/local.py (maintenance#1387).
import frappe
from frappe.model.document import Document


class LocalCalendarEvent(Document):
    def autoname(self) -> None:
        # The JMAP id of the event: letters and digits only. An occurrence of a series is "<id>.<its start>"
        # (suite/calendar/local.py), which a dot keeps apart.
        self.name = frappe.generate_hash(length=16)

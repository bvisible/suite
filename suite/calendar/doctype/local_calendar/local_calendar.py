# //// Neoffice — added file (no upstream equivalent): see the DocType's description and suite/calendar/local.py (maintenance#1387).
import frappe
from frappe.model.document import Document


class LocalCalendar(Document):
    def autoname(self) -> None:
        # The JMAP id of the calendar: letters and digits, as the mail server's.
        self.name = frappe.generate_hash(length=12)

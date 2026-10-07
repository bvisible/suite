# //// Neoffice — added file (no upstream equivalent). Writer's document list, called the way the browser calls
# //// it: start and limit as text from the query string.
import frappe
from frappe.tests.utils import FrappeTestCase

from suite.writer.api.general import get_document_list


class TestDocumentListTakesTextParams(FrappeTestCase):
    def test_start_and_limit_sent_as_text(self):
        # On live traffic frappe casts nothing on a module with deferred annotations (PEP 563,
        # typing_validations' report-only pass, maintenance#244): the function gets the query string's text.
        # A test run is strict and would cast it, so it is switched off for the call.
        in_test = frappe.flags.in_test
        frappe.flags.in_test = False
        try:
            # Before the cint, `limit + 1` raised "can only concatenate str (not "int") to str".
            get_document_list(start="0", limit="5")
        finally:
            frappe.flags.in_test = in_test

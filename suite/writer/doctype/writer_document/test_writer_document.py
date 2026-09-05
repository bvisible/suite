# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe
from frappe.tests import IntegrationTestCase

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class IntegrationTestWriterDocument(IntegrationTestCase):
    """
    Integration tests for WriterDocument.
    Use this class for testing interactions between multiple components.
    """

    def test_delete_purges_versions(self):
        doc = frappe.new_doc("Writer Document")
        doc.save()
        version = frappe.get_doc(
            {
                "doctype": "Writer Version",
                "doc": doc.name,
                "snapshot": "<p>hello</p>",
                "title": "2026-01-01 00:00",
            }
        ).insert()

        # a version links back to the document — without the cascade the
        # framework's link check refuses the delete
        doc.delete()

        self.assertFalse(frappe.db.exists("Writer Document", doc.name))
        self.assertFalse(frappe.db.exists("Writer Version", version.name))

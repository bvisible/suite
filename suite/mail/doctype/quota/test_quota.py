# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

# import frappe
#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from frappe.tests import IntegrationTestCase

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class IntegrationTestQuota(IntegrationTestCase):
    """
    Integration tests for Quota.
    Use this class for testing interactions between multiple components.
    """

    pass

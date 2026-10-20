# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
# //// Neoffice — added file (no upstream equivalent): the uid a JMAP client gives its new event (client_uid).
"""Which uid a client gives its new event is kept: one that iCalendar carries as it is, and nothing else."""

# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations

import inspect

from frappe.tests import UnitTestCase

from suite.calendar.doctype.calendar_event.calendar_event import (
    MAX_CLIENT_UID,
    add_calendar_event,
    client_uid,
)


class TestClientUid(UnitTestCase):
    def test_a_uid_icalendar_carries_as_it_is_is_kept(self):
        for uid in ("0f6c3b2e-8d41-4c7a-9a52-6b1f0e2d3c4b", "event-1@example.org", "x", "é" * MAX_CLIENT_UID):
            self.assertEqual(client_uid(uid), uid)

    def test_anything_else_gets_a_uid_of_its_own(self):
        for uid in (
            None,
            "",
            " lead",
            "trail ",
            "two\nlines",
            "tab\tin",
            "del\x7f",
            "x" * (MAX_CLIENT_UID + 1),
            42,
        ):
            self.assertIsNone(client_uid(uid), repr(uid))

    def test_the_desks_method_takes_it(self):
        self.assertIn("uid", inspect.signature(add_calendar_event).parameters)

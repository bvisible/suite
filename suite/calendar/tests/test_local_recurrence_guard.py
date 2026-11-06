# //// Neoffice — added file (no upstream equivalent): a repeat rule a calendar kept in Frappe refuses to store,
# //// because every expansion of it would walk for seconds (neoffice-maintenance#2296).
"""dateutil walks a rule from the series' start and stops only on a date it gives, or at year 9999.

A rule that never gives one (the 30th of February) walked to 9999 on every store, every query of the calendar and
every minute of the alert scheduler; a rule more frequent than daily walks every second, minute or hour since its
start. Both are refused when a local calendar stores the event; every rule the calendar's screens make is kept.
"""

from __future__ import annotations

import time

from frappe.tests import UnitTestCase

from suite.calendar import local

START = "2026-11-06T10:00:00"


def event(rule: dict, start: str = START) -> dict:
    return {
        "start": start,
        "duration": "PT1H",
        "timeZone": "Europe/Zurich",
        "recurrenceRule": {"@type": "RecurrenceRule", **rule},
    }


class StubConnection:
    """What event_set needs of a local account to reach store_event; nothing is written."""

    account = "local-recurrence-test"
    time_zone = "Europe/Zurich"
    store_event = local.LocalJMAPConnection.store_event

    def calendars(self):
        return [{"id": "calendar-1", "isDefault": True}]


class TestRecurrenceGuard(UnitTestCase):
    def test_a_rule_that_never_gives_a_date_is_refused_quickly(self):
        for rule in (
            {"frequency": "daily", "byMonth": ["2"], "byMonthDay": [30]},
            {"frequency": "weekly", "byMonth": ["4"], "byMonthDay": [31]},
            {"frequency": "monthly", "byMonth": ["2"], "byMonthDay": [30], "count": 5},
            {"frequency": "yearly", "byMonth": ["11"], "byMonthDay": [31], "until": "9999-01-01T00:00:00"},
            # every fourth year from 2027 is never a leap year
            {"frequency": "yearly", "interval": 4, "byMonth": ["2"], "byMonthDay": [29]},
        ):
            with self.subTest(rule=rule):
                began = time.monotonic()
                with self.assertRaises(ValueError):
                    local.check_rule(event(rule, start="2027-02-01T10:00:00"), "UTC")
                self.assertLess(time.monotonic() - began, 2)

    def test_a_rule_more_frequent_than_daily_is_refused(self):
        for frequency in ("hourly", "minutely", "secondly"):
            with self.subTest(frequency=frequency), self.assertRaises(ValueError):
                local.check_rule(event({"frequency": frequency}), "UTC")

    def test_an_interval_below_one_is_refused(self):
        with self.assertRaises(ValueError):
            local.check_rule(event({"frequency": "daily", "interval": -1}), "UTC")

    def test_every_rule_the_calendar_makes_is_kept(self):
        for rule in (
            {"frequency": "daily"},
            {"frequency": "daily", "interval": 3, "count": 10},
            {"frequency": "weekly", "byDay": [{"day": "mo"}, {"day": "we"}, {"day": "fr"}]},
            {"frequency": "weekly", "interval": 2, "until": "2027-06-30T23:59:59"},
            {"frequency": "monthly", "byMonthDay": [31]},
            {"frequency": "monthly", "byDay": [{"day": "fr", "nthOfPeriod": 5}]},
            {"frequency": "monthly", "byDay": [{"day": "mo", "nthOfPeriod": -1}]},
            {"frequency": "yearly"},
            {"frequency": "yearly", "byMonth": ["2"], "byMonthDay": [29]},
            {"frequency": "yearly", "interval": 4, "byMonth": ["2"], "byMonthDay": [29]},
        ):
            with self.subTest(rule=rule):
                local.check_rule(event(rule, start="2028-01-10T09:00:00"), "UTC")

    def test_an_event_without_a_rule_is_not_looked_at(self):
        local.check_rule({"start": START, "duration": "PT1H"}, "UTC")

    def test_the_local_account_answers_a_refused_rule_as_invalid_properties(self):
        refused = event({"frequency": "daily", "byMonth": ["2"], "byMonthDay": [30]})
        result = local.event_set(StubConnection(), {"create": {"new-1": refused}})
        self.assertEqual(result["created"], {})
        self.assertEqual(result["notCreated"]["new-1"]["type"], "invalidProperties")

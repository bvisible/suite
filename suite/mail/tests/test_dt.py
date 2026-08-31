# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
"""The mail wire-format contract: APIs speak and listen UTC ``...Z``; only Frappe DB fields
and server-rendered text leave that format."""
from __future__ import annotations

import unittest
from datetime import UTC, datetime
from unittest import mock

from suite.mail.utils import dt as mail_dt
from suite.utils import dt as suite_dt


class NormalizeUtcZ(unittest.TestCase):
    """``normalize_utc_z`` — wire values in, wire values out; naive means UTC."""

    def test_offset_form_is_converted_to_z(self):
        # Stalwart's second shape: 2026-03-23T20:03:40-05:00.
        self.assertEqual(mail_dt.normalize_utc_z("2026-03-23T20:03:40-05:00"), "2026-03-24T01:03:40Z")

    def test_z_form_passes_through(self):
        self.assertEqual(mail_dt.normalize_utc_z("2026-07-29T09:06:54Z"), "2026-07-29T09:06:54Z")

    def test_naive_is_read_as_utc(self):
        self.assertEqual(mail_dt.normalize_utc_z("2026-07-29 09:06:54"), "2026-07-29T09:06:54Z")

    def test_fractional_seconds_are_dropped(self):
        self.assertEqual(mail_dt.normalize_utc_z("2026-07-29T09:06:54.123Z"), "2026-07-29T09:06:54Z")

    def test_aware_datetime_object(self):
        aware = datetime(2026, 7, 29, 9, 6, 54, tzinfo=UTC)
        self.assertEqual(mail_dt.normalize_utc_z(aware), "2026-07-29T09:06:54Z")

    def test_blank_stays_blank(self):
        self.assertIsNone(mail_dt.normalize_utc_z(None))
        self.assertIsNone(mail_dt.normalize_utc_z(""))


class UtcNow(unittest.TestCase):
    """``utcnow`` — Stalwart write paths use it, so it must emit the canonical wire shape."""

    def test_emits_second_precision_z(self):
        value = suite_dt.utcnow()
        self.assertRegex(value, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(mail_dt.normalize_utc_z(value), value)


class ToUtcZ(unittest.TestCase):
    """``to_utc_z`` — a naive value is a Frappe DB field, read as system time."""

    def test_naive_is_read_as_system_time(self):
        with mock.patch.object(suite_dt, "get_system_timezone", return_value="Asia/Kolkata"):
            self.assertEqual(mail_dt.to_utc_z("2026-07-28 14:32:30"), "2026-07-28T09:02:30Z")

    def test_aware_value_ignores_the_system_zone(self):
        with mock.patch.object(suite_dt, "get_system_timezone", return_value="Asia/Kolkata"):
            self.assertEqual(mail_dt.to_utc_z("2026-03-23T20:03:40-05:00"), "2026-03-24T01:03:40Z")

    def test_blank_stays_blank(self):
        self.assertIsNone(mail_dt.to_utc_z(None))


class FromUtcZ(unittest.TestCase):
    """``from_utc_z`` — the one inbound conversion, for values written to Frappe DB fields."""

    def test_z_becomes_a_system_time_string(self):
        # Frappe's datetime-string format carries microseconds.
        with mock.patch.object(suite_dt, "get_system_timezone", return_value="Asia/Kolkata"):
            self.assertEqual(mail_dt.from_utc_z("2026-07-28T09:02:30Z"), "2026-07-28 14:32:30.000000")

    def test_blank_stays_blank(self):
        self.assertIsNone(mail_dt.from_utc_z(None))


class ParseIsoDatetime(unittest.TestCase):
    """``parse_iso_datetime`` — a naive wire value is UTC, never the OS process zone."""

    def test_naive_is_read_as_utc(self):
        with mock.patch.object(suite_dt, "get_system_timezone", return_value="Asia/Kolkata"):
            self.assertEqual(suite_dt.parse_iso_datetime("2026-08-01T10:00:00"), "2026-08-01 15:30:00.000000")

    def test_offset_form_is_converted(self):
        with mock.patch.object(suite_dt, "get_system_timezone", return_value="Asia/Kolkata"):
            self.assertEqual(
                suite_dt.parse_iso_datetime("2026-03-23T20:03:40-05:00"), "2026-03-24 06:33:40.000000"
            )


class ToUserTimezone(unittest.TestCase):
    """``to_user_timezone`` — server-rendered text only; browser conversion happens client-side."""

    def test_uses_the_users_zone(self):
        with mock.patch.object(mail_dt, "frappe") as frappe:
            frappe.session.user = "user@example.com"
            frappe.db.get_value.return_value = "America/New_York"
            converted = mail_dt.to_user_timezone("2026-03-24T01:03:40Z")
        # EDT on that date: UTC-4.
        self.assertEqual(converted.strftime("%Y-%m-%d %H:%M:%S"), "2026-03-23 21:03:40")

    def test_falls_back_to_the_system_zone(self):
        with (
            mock.patch.object(mail_dt, "frappe") as frappe,
            mock.patch.object(mail_dt, "get_system_timezone", return_value="Asia/Kolkata"),
        ):
            frappe.session.user = "user@example.com"
            frappe.db.get_value.return_value = None
            converted = mail_dt.to_user_timezone("2026-07-28T09:02:30Z")
        self.assertEqual(converted.strftime("%Y-%m-%d %H:%M:%S"), "2026-07-28 14:32:30")


if __name__ == "__main__":
    unittest.main()

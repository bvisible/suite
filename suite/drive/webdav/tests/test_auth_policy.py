# //// Neoffice — added file (no upstream equivalent): /dav obeys the account's IP allowlist, login hours and forced
# //// password change, and its log keeps one request on one line (neoffice-maintenance#2296).
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from suite.drive.webdav import auth, log
from suite.drive.webdav.errors import AuthRequired
from suite.drive.webdav.tests.test_auth import PASSWORD, authenticate, make_user
from suite.drive.webdav.tests.utils import ensure_system_settings_saveable

ALLOWED = "198.51.100."
INSIDE = "198.51.100.20"
OUTSIDE = "203.0.113.7"


class TestWebDAVAuthPolicy(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_system_settings_saveable()

    def setUp(self):
        self.addCleanup(setattr, frappe.local, "request_ip", getattr(frappe.local, "request_ip", None))

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def _api_keys(self, user: str) -> tuple[str, str]:
        from frappe.core.doctype.user.user import generate_keys

        with self.set_user("Administrator"):
            secret = generate_keys(user)["api_secret"]
        return frappe.db.get_value("User", user, "api_key"), secret

    def test_a_password_from_outside_the_ip_allowlist_is_refused(self):
        user = make_user("policy-ip")
        frappe.db.set_value("User", user, "restrict_ip", ALLOWED)
        frappe.local.request_ip = OUTSIDE
        with self.assertRaises(AuthRequired):
            authenticate(user, PASSWORD)
        frappe.local.request_ip = INSIDE
        self.assertEqual(authenticate(user, PASSWORD), user)

    def test_api_credentials_from_outside_the_ip_allowlist_are_refused(self):
        user = make_user("policy-ip-key")
        api_key, secret = self._api_keys(user)
        frappe.db.set_value("User", user, "restrict_ip", ALLOWED)
        frappe.local.request_ip = OUTSIDE
        with self.assertRaises(AuthRequired):
            authenticate(api_key, secret)
        frappe.local.request_ip = INSIDE
        self.assertEqual(authenticate(api_key, secret), user)

    def test_a_device_token_from_outside_the_ip_allowlist_is_refused(self):
        user = make_user("policy-ip-token")
        frappe.db.set_value("User", user, "restrict_ip", ALLOWED)
        with patch.object(auth, "_authenticate_device", return_value=user):
            frappe.local.request_ip = OUTSIDE
            with self.assertRaises(AuthRequired):
                authenticate(None, header="Bearer any-token")
            frappe.local.request_ip = INSIDE
            self.assertEqual(authenticate(None, header="Bearer any-token"), user)

    def test_a_password_outside_the_login_hours_is_refused(self):
        user = make_user("policy-hours")
        frappe.db.set_value("User", user, "login_after", 24)  # never reached: no hour of the day is allowed
        with self.assertRaises(AuthRequired):
            authenticate(user, PASSWORD)
        frappe.db.set_value("User", user, "login_after", 0)
        self.assertEqual(authenticate(user, PASSWORD), user)

    def test_a_password_past_its_forced_change_is_refused(self):
        user = make_user("policy-expired")
        with self.change_settings("System Settings", force_user_to_reset_password=30):
            frappe.db.set_value("User", user, "last_password_reset_date", add_days(today(), -60))
            with self.assertRaises(AuthRequired):
                authenticate(user, PASSWORD)
            frappe.db.set_value("User", user, "last_password_reset_date", today())
            self.assertEqual(authenticate(user, PASSWORD), user)

    def test_a_line_break_in_the_request_stays_on_one_log_line(self):
        request = SimpleNamespace(
            method="GET",
            path="/dav/x\n2026-01-01 00:00:00,000 INFO forged entry",
            user_agent=SimpleNamespace(string="agent\r\nforged"),
            headers={},
            remote_addr="127.0.0.1",
        )
        with patch.dict(frappe.local.conf, {"drive_webdav_log_level": "info"}):
            log.start_request(request)
        log.note("refused\nforged note")
        with self.assertLogs(f"suite.drive.webdav-{frappe.local.site}", level="INFO") as logs:
            log.log_response(request, SimpleNamespace(status_code=404))
        line = logs.output[0]
        self.assertNotIn("\n", line)
        self.assertNotIn("\r", line)
        self.assertIn("/dav/x\\n2026-01-01", line)

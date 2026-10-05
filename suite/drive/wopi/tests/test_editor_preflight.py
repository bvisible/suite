# //// Neoffice — added file (no upstream equivalent). An Office document opened while Collabora is still
# //// waking up must wait for the editor, never be told "this file type is not supported" (05.10.2026 on
# //// osiris: an .xlsx opened from Drive fell back to the Microsoft warning). Each test pins one link of that
# //// chain: the order of the editor pre-flight, the idle watchdog during a start, and a cache flush.
from __future__ import annotations

from unittest.mock import patch
from xml.etree import ElementTree

import frappe
from frappe.tests import IntegrationTestCase

from suite.drive.wopi import discovery, editor, lifecycle

PREFLIGHT = getattr(editor.can_edit_file, "__wrapped__", editor.can_edit_file)

SPREADSHEET = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DISCOVERY = ElementTree.fromstring(
    f'<wopi-discovery><net-zone name="external-http"><app name="{SPREADSHEET}">'
    '<action default="true" ext="xlsx" name="edit" urlsrc="http://127.0.0.1:9980/browser/x/cool.html?"/>'
    "</app></net-zone></wopi-discovery>"
)


class TestTheEditorPreflight(IntegrationTestCase):
    def ask(self, file_name: str, discovered, enabled: bool = True):
        with (
            patch.object(editor.frappe.db, "exists", return_value=True),
            patch("suite.drive.api.permissions.user_has_permission", return_value=True),
            patch.object(editor.frappe.db, "get_value", return_value=file_name),
            patch.object(discovery, "get_wopi_settings", return_value={"enabled": int(enabled)}),
            patch.object(discovery, "get_collabora_url", return_value="http://127.0.0.1:9980"),
            patch.object(discovery, "get_discovery_xml", return_value=discovered) as fetch,
        ):
            return PREFLIGHT("a-file-id"), fetch

    def test_a_server_still_starting_asks_the_preview_to_wait(self):
        # The cold start outran its timeout: no discovery yet. The file type is unknown, not unsupported.
        answer, fetch = self.ask("sheet.xlsx", None)
        self.assertFalse(answer["can_edit"])
        self.assertTrue(answer.get("wopi_enabled"), answer)
        self.assertTrue(answer.get("retryable"), answer)
        # Only one wake-up per click: the daemon is started once, by the status check.
        self.assertEqual([call.kwargs.get("start_if_down") for call in fetch.call_args_list], [True])

    def test_a_running_server_opens_what_it_edits_and_refuses_the_rest(self):
        answer, fetch = self.ask("sheet.xlsx", DISCOVERY)
        self.assertTrue(answer["can_edit"], answer)
        # The type check reads the discovery the status check just fetched: it never starts the daemon again.
        self.assertEqual([call.kwargs.get("start_if_down") for call in fetch.call_args_list], [True, False])

        answer, _ = self.ask("notes.xyz", DISCOVERY)
        self.assertFalse(answer["can_edit"])
        self.assertTrue(answer.get("wopi_enabled"), answer)
        self.assertFalse(answer.get("retryable"), answer)

    def test_an_instance_without_collabora_says_so(self):
        answer, _ = self.ask("sheet.xlsx", None, enabled=False)
        self.assertFalse(answer["can_edit"])
        self.assertFalse(answer.get("wopi_enabled"), answer)
        self.assertFalse(answer.get("retryable"), answer)


class TestTheIdleWatchdogLetsAStartFinish(IntegrationTestCase):
    def test_a_watchdog_tick_during_a_start_keeps_the_daemon(self):
        # Right after a cache flush nothing says coolwsd was ever used, which the watchdog reads as idle.
        frappe.cache().delete_value(lifecycle.COLLABORA_LAST_ACTIVITY_KEY)
        state = {"active": False}
        actions, verdicts = [], []

        def systemctl(action, timeout=10):
            actions.append(action)
            if action == "start":
                # The cron tick lands while coolwsd is up but still binding its port.
                state["active"] = True
                verdicts.append(lifecycle.stop_if_idle())
            return True, ""

        with (
            patch.object(lifecycle, "is_coolwsd_active", side_effect=lambda: state["active"]),
            patch.object(lifecycle, "_count_active_websockets", return_value=0),
            patch.object(lifecycle, "_discovery_responds", side_effect=lambda *a, **k: state["active"]),
            patch.object(lifecycle, "_systemctl", side_effect=systemctl),
        ):
            self.assertTrue(lifecycle.ensure_running(timeout=2))

        self.assertNotIn("stop", actions)
        self.assertEqual(verdicts[0]["action"], "kept", verdicts)

    def test_a_cache_flush_keeps_the_activity_stamp(self):
        self.assertIn(
            lifecycle.COLLABORA_LAST_ACTIVITY_KEY, frappe.get_hooks("persistent_cache_keys", app_name="suite")
        )
        lifecycle._record_activity()
        frappe.cache().delete_value("app_hooks")
        frappe.clear_cache()
        self.assertIsNotNone(lifecycle._last_activity())

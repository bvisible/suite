# //// Neoffice — added file (no upstream equivalent): where a sheet's collaboration events go, and the tab names
# //// the formula autocomplete draws (neoffice-maintenance#2296).
"""A sheet's live edits reach the people who may read the sheet, not every desk user of the site.

The collaboration endpoints publish to the sheet's own room (`doc:Sheet/<name>`), which frappe's socket server lets
a socket join only after its read check; they used to publish to the site-wide room every desk user's socket joins.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.realtime import get_doc_room, get_site_room
from frappe.tests import UnitTestCase
from frappe.tests.roles import as_role

from suite.sheets import api
from suite.sheets.versioning import snapshots

FRONTEND = Path(frappe.get_app_path("suite")).parent / "frontend" / "src" / "apps" / "sheets"
SHEET = "sheet-room-test"


class TestSheetRealtimeRoom(UnitTestCase):
    def rooms_of(self, call) -> list[str]:
        with (
            as_role("sales_user"),
            patch.object(api.frappe, "has_permission", return_value=True),
            patch("frappe.realtime.emit_via_redis") as emit,
        ):
            call()
        return [c.args[2] for c in emit.call_args_list]

    def test_every_collaboration_event_goes_to_the_sheets_own_room(self):
        calls = {
            "yjs_relay": lambda: api.yjs_relay(SHEET, "yjs_update", '{"update": "AAE="}'),
            "broadcast_op": lambda: api.broadcast_op(SHEET, '{"op": 1}'),
            "broadcast_cursor": lambda: api.broadcast_cursor(SHEET, 1, 2, "Sheet1"),
            "ping_presence": lambda: api.ping_presence(SHEET),
        }
        for name, call in calls.items():
            with self.subTest(endpoint=name):
                rooms = self.rooms_of(call)
                self.assertEqual(rooms, [get_doc_room("Sheet", SHEET)])
                self.assertNotIn(get_site_room(), rooms)

    def test_a_snapshot_is_announced_in_the_sheets_room(self):
        source = inspect.getsource(snapshots.create)
        self.assertIn('doctype="Sheet"', source)
        self.assertIn("docname=sheet", source)

    def test_the_sheets_client_joins_the_room(self):
        source = (FRONTEND / "collab" / "realtime-adapter.js").read_text()
        self.assertIn("'doc_subscribe', 'Sheet', sheetId", source)
        self.assertIn("'connect', subscribe", source)


class TestFormulaAutocomplete(UnitTestCase):
    def test_tab_names_are_escaped_before_innerhtml(self):
        source = (FRONTEND / "canvas" / "index.js").read_text()
        self.assertNotIn(">${item.name}</span>", source)
        self.assertIn("${_acEsc(item.name)}", source)
        self.assertIn("${_acEsc(ctx.fn)}", source)
        self.assertIn("'<': '&lt;'", source)

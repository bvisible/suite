# //// Neoffice — added file (no upstream equivalent): the dates of the ERP, shown in the calendar as calendars of
# //// their own and read-only (maintenance#1428, suite/calendar/sources.py). An app puts a small provider behind the
# //// `suite_calendar_sources` hook; the calendar's two calls (get_calendars, get_calendar_events) add what it says.
# //// Everything goes through those two calls, on a local account: no mail server is needed, and none is touched
# //// (the users are made with the mailbox provisioning switched off, so a clone of a site with Stalwart does not
# //// create real mailboxes).
from __future__ import annotations

from datetime import date, datetime
from unittest import mock

import frappe
from frappe.tests import IntegrationTestCase

DESK = "calendar-sources-desk@example.com"
OTHER = "calendar-sources-other@example.com"
PORTAL = "calendar-sources-portal@example.com"
ZURICH = "Europe/Zurich"


def _user(email: str, user_type: str) -> str:
    if not frappe.db.exists("User", email):
        with mock.patch("suite.mail.events._should_provision_mail", return_value=False):
            frappe.get_doc(
                {
                    "doctype": "User",
                    "email": email,
                    "first_name": "Calendar sources",
                    "send_welcome_email": 0,
                    "user_type": user_type,
                    "roles": [{"role": "System Manager"}] if user_type == "System User" else [],
                }
            ).insert(ignore_permissions=True)
    frappe.db.set_value("User", email, {"user_type": user_type, "time_zone": ZURICH})
    return email


class Provider:
    """What an app puts behind the `suite_calendar_sources` hook: the sources a person may have, the entries of one
    of them in a period, and where the person's choices are kept."""

    def __init__(self):
        self.enabled = {"things": True, "quiet": False, "broken": True}
        self.scope = "mine"
        self.asked = []
        self.entries = {
            "things": [
                {
                    "id": "todo-1",
                    "title": "Call the notary",
                    "start": date(2026, 10, 15),
                    "end": None,
                    "all_day": True,
                    "doctype": "ToDo",
                    "name": "TODO-1",
                    "route": "/app/todo/TODO-1",
                    "status": "Open",
                    "late": True,
                    "meta": "Task",
                },
                {
                    "id": "leave-1",
                    "title": "Away",
                    "start": date(2026, 10, 12),
                    "end": date(2026, 10, 14),
                    "all_day": True,
                    "doctype": "Leave Application",
                    "name": "HR-LAP-1",
                    "route": "/app/leave-application/HR-LAP-1",
                },
                {
                    "id": "visit-1",
                    "title": "Site visit",
                    "start": datetime(2026, 10, 12, 14, 30),
                    "end": datetime(2026, 10, 12, 15, 30),
                    "all_day": False,
                    "doctype": "Activity",
                    "name": "ACT-1",
                    "route": "/app/activity/ACT-1",
                },
                {
                    "id": "ping-1",
                    "title": "Ping",
                    "start": datetime(2026, 10, 13, 9, 0),
                    "end": None,
                    "all_day": False,
                    "doctype": "Reminder",
                    "name": "REM-1",
                    "route": "/app/reminder/REM-1",
                },
            ],
            "quiet": [
                {
                    "id": "q-1",
                    "title": "Should not be asked",
                    "start": date(2026, 10, 20),
                    "end": None,
                    "all_day": True,
                    "doctype": "ToDo",
                    "name": "TODO-9",
                    "route": "/app/todo/TODO-9",
                }
            ],
            "broken": [],
        }

    def calendar_sources(self, user):
        return [
            {
                "id": "things",
                "title": "Things",
                "palette": "green",
                "icon": "lucide-check",
                "enabled": self.enabled["things"],
                "scoped": True,
            },
            {
                "id": "quiet",
                "title": "Quiet",
                "palette": "amber",
                "icon": "lucide-bell",
                "enabled": self.enabled["quiet"],
                "scoped": False,
            },
            {
                "id": "broken",
                "title": "Broken",
                "palette": "pink",
                "icon": "lucide-x",
                "enabled": self.enabled["broken"],
                "scoped": False,
            },
        ]

    def calendar_scope(self, user):
        return self.scope

    def calendar_entries(self, user, source, start, end, scope):
        self.asked.append((user, source, start, end, scope))
        if source == "broken":
            raise RuntimeError("this source is down")
        return list(self.entries[source])

    def set_calendar_source_enabled(self, user, source, enabled):
        self.enabled[source] = bool(enabled)

    def set_calendar_scope(self, user, scope):
        self.scope = scope


def _events(account, start="2026-10-01T00:00:00Z", end="2026-11-30T00:00:00Z"):
    from suite.calendar.api import get_calendar_events

    return get_calendar_events(account, start, end, ZURICH, erp_dates=1)


class TestCalendarSources(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for doctype in ("local_calendar_account", "local_calendar", "local_calendar_event"):
            frappe.reload_doc("calendar", "doctype", doctype)
        _user(DESK, "System User")
        _user(OTHER, "System User")
        _user(PORTAL, "Website User")

    def setUp(self):
        from suite.calendar.local import ensure_local_calendar_account

        frappe.set_user(DESK)
        self.account = ensure_local_calendar_account()
        self.provider = Provider()
        from suite.calendar.sources import FAILURE_KEY

        for source in ("broken", "sources", "scope"):  # a failure said a moment ago is not said again
            frappe.cache.delete_value(FAILURE_KEY.format(source))
        for patch in (
            mock.patch("suite.calendar.sources._providers", return_value=[self.provider]),
            mock.patch("suite.calendar.sources.get_system_timezone", return_value=ZURICH),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def tearDown(self):
        frappe.set_user("Administrator")

    def virtual(self, calendars=None):
        from suite.calendar.api import get_calendars

        return [c for c in (calendars or get_calendars(self.account, erp_dates=1)) if c.get("virtual")]

    # --- the calendars -------------------------------------------------------------------------------------

    def test_the_sources_follow_the_real_calendars_as_calendars_of_their_own(self):
        from suite.calendar.api import get_calendars

        calendars = get_calendars(self.account, erp_dates=1)
        real = [c for c in calendars if not c.get("virtual")]
        virtual = self.virtual(calendars)

        self.assertEqual(len(real), 1, "the person's own calendar is still there, first")
        self.assertTrue(real[0]["default"])
        self.assertEqual([c["id"] for c in virtual], ["erp:things", "erp:quiet", "erp:broken"])
        things = virtual[0]
        self.assertEqual(things["name"], f"{self.account}|erp:things")
        self.assertEqual(things["_name"], "Things")
        self.assertEqual(things["palette"], "green")
        self.assertEqual(things["icon"], "lucide-check")
        self.assertEqual(
            (things["visible"], virtual[1]["visible"]), (1, 0), "the person's switch, from the provider"
        )
        self.assertEqual((things["may_admin"], things["may_write_all"], things["may_delete"]), (0, 0, 0))
        self.assertEqual(things["share_with"], [])
        self.assertTrue(things["read_only"])
        self.assertEqual((things["scoped"], virtual[1]["scoped"]), (1, 0))
        self.assertEqual(things["scope"], "mine")

    def test_an_app_that_puts_nothing_behind_the_hook_changes_nothing(self):
        from suite.calendar.api import get_calendars

        with mock.patch("suite.calendar.sources._providers", return_value=[]):
            self.assertEqual(self.virtual(), [])
            self.assertEqual(len(get_calendars(self.account, erp_dates=1)), 1)
            self.assertEqual(_events(self.account), [])

    def test_the_other_callers_of_the_calendar_get_only_the_calendar(self):
        # The mail sidebar and Meet list today's events from the same call: a task is not their business.
        from suite.calendar.api import get_calendar_events, get_calendars

        self.assertEqual(self.virtual(get_calendars(self.account)), [])
        self.assertEqual(
            [
                e
                for e in get_calendar_events(
                    self.account, "2026-10-01T00:00:00Z", "2026-11-30T00:00:00Z", ZURICH
                )
                if e.get("virtual")
            ],
            [],
        )
        self.assertEqual(self.provider.asked, [], "and nothing was read for them")

    # --- the events -------------------------------------------------------------------------------------------

    def test_an_entry_becomes_an_event_the_screen_can_draw(self):
        events = {event["id"]: event for event in _events(self.account) if event.get("virtual")}

        self.assertEqual(
            sorted(events),
            ["erp:things:leave-1", "erp:things:ping-1", "erp:things:todo-1", "erp:things:visit-1"],
        )
        todo = events["erp:things:todo-1"]
        self.assertEqual(todo["name"], f"{self.account}|erp:things:todo-1")
        self.assertEqual(todo["title"], "Call the notary")
        self.assertEqual(todo["calendars"][0]["calendar"], f"{self.account}|erp:things")
        # A day without an hour is a whole day: the midnight to midnight shape the screen reads.
        self.assertEqual(
            (todo["start"], todo["duration"], todo["show_without_time"]), ("2026-10-15T00:00:00", "P1D", 1)
        )
        self.assertEqual(todo["time_zone"], ZURICH)
        self.assertTrue(todo["virtual"] and todo["read_only"])
        self.assertEqual(todo["route"], "/app/todo/TODO-1")
        self.assertEqual((todo["doctype"], todo["docname"]), ("ToDo", "TODO-1"))
        self.assertTrue(todo["late"])
        self.assertEqual(todo["source"], "things")
        self.assertEqual(todo["palette"], "green")
        for key in ("participants", "locations", "links", "alerts"):
            self.assertEqual(todo[key], [], key)
        self.assertEqual((todo["organizer"], todo["recurrence_id"], todo["draft"]), ("", None, 0))
        self.assertEqual(todo["recurrence_rule"], "{}")

        span = events["erp:things:leave-1"]  # the last day counts: 12 to 14 October is three days
        self.assertEqual(
            (span["start"], span["duration"], span["show_without_time"]), ("2026-10-12T00:00:00", "P3D", 1)
        )

        timed = events["erp:things:visit-1"]
        self.assertEqual(
            (timed["start"], timed["duration"], timed["show_without_time"]),
            ("2026-10-12T14:30:00", "PT1H", 0),
        )

        short = events["erp:things:ping-1"]  # no end: a hand's width, not a point
        self.assertEqual((short["start"], short["duration"]), ("2026-10-13T09:00:00", "PT30M"))

    def test_only_the_sources_that_are_on_are_read(self):
        _events(self.account)
        self.assertEqual({asked[1] for asked in self.provider.asked}, {"things", "broken"})

    def test_the_period_reaches_the_provider_as_the_wall_clock_of_the_site(self):
        _events(self.account, "2026-10-01T00:00:00Z", "2026-11-30T00:00:00Z")

        (asked,) = [a for a in self.provider.asked if a[1] == "things"]
        user, _source, start, end, scope = asked
        self.assertEqual(user, DESK)
        # 1 October is summer time in Zurich (UTC+2), 30 November winter time (UTC+1).
        self.assertEqual((start, end), (datetime(2026, 10, 1, 2, 0), datetime(2026, 11, 30, 1, 0)))
        self.assertEqual(scope, "mine")

    def test_a_source_that_fails_costs_its_own_entries_and_nothing_else(self):
        with mock.patch("suite.calendar.sources.frappe.log_error") as log_error:
            events = _events(self.account)
            _events(self.account)  # the screen asks again at every move to another month

        self.assertEqual(len([e for e in events if e.get("source") == "things"]), 4)
        self.assertEqual([e for e in events if e.get("source") == "broken"], [])
        self.assertEqual(log_error.call_count, 1, "said once in a while, not at every look")
        title, _message = log_error.call_args.args
        self.assertLessEqual(len(title), 140, "frappe.log_error(title, message): the title first and short")

    def test_a_source_is_capped(self):
        many = [
            {"id": f"t-{n}", "title": f"Task {n}", "start": date(2026, 10, 1 + n % 28), "end": None, "all_day": True,
             "doctype": "ToDo", "name": f"TODO-{n}", "route": f"/app/todo/TODO-{n}"}
            for n in range(500)
        ]  # fmt: skip
        self.provider.entries["things"] = many

        events = [e for e in _events(self.account) if e.get("source") == "things"]

        self.assertEqual(len(events), 300)

    # --- the choices -------------------------------------------------------------------------------------------

    def test_the_switch_of_a_source_is_kept_by_the_provider_not_by_the_mail_server(self):
        from suite.calendar.doctype.calendar.calendar import set_calendar_visibility

        set_calendar_visibility(self.account, "erp:quiet", 1)
        set_calendar_visibility(self.account, "erp:things", 0)

        self.assertEqual((self.provider.enabled["quiet"], self.provider.enabled["things"]), (True, False))
        by_id = {c["id"]: c for c in self.virtual()}
        self.assertEqual((by_id["erp:quiet"]["visible"], by_id["erp:things"]["visible"]), (1, 0))
        events = _events(self.account)
        self.assertFalse([e for e in events if e.get("source") == "things"], "an off source is not read")
        self.assertTrue([e for e in events if e.get("source") == "quiet"])

    def test_a_source_that_does_not_exist_is_refused(self):
        from suite.calendar.doctype.calendar.calendar import set_calendar_visibility

        with self.assertRaises(frappe.ValidationError):
            set_calendar_visibility(self.account, "erp:nothing", 1)

    def test_the_scope_is_chosen_through_the_account(self):
        from suite.calendar.sources import set_calendar_scope

        set_calendar_scope(self.account, "all")
        self.assertEqual(self.provider.scope, "all")
        self.assertEqual(self.virtual()[0]["scope"], "all")
        _events(self.account)
        self.assertEqual(self.provider.asked[-1][4] if self.provider.asked else None, "all")

        with self.assertRaises(frappe.ValidationError):
            set_calendar_scope(self.account, "everybody")
        self.assertEqual(self.provider.scope, "all")

    # --- who gets them -----------------------------------------------------------------------------------------

    def test_the_account_of_somebody_else_gets_none_even_for_a_system_manager(self):
        from suite.calendar.sources import virtual_calendars, virtual_events

        frappe.set_user(OTHER)  # System Manager: may open another's local calendar, must not read his dates
        self.assertEqual(virtual_calendars(self.account), [])
        self.assertEqual(virtual_events(self.account, "2026-10-01T00:00:00Z", "2026-11-30T00:00:00Z"), [])
        with self.assertRaises(frappe.PermissionError):
            from suite.calendar.sources import set_calendar_scope

            set_calendar_scope(self.account, "all")

    def test_a_portal_user_gets_none(self):
        from suite.calendar.sources import virtual_calendars, virtual_events

        frappe.set_user(PORTAL)
        self.assertEqual(virtual_calendars(self.account), [])
        self.assertEqual(virtual_events(self.account, "2026-10-01T00:00:00Z", "2026-11-30T00:00:00Z"), [])

    def test_the_personal_mail_account_gets_them_too(self):
        from suite.calendar.sources import applies_to

        self.assertTrue(applies_to(self.account))
        with mock.patch(
            "suite.mail.doctype.user_account.user_account.get_user_personal_jmap_account",
            return_value="mail-1",
        ):
            self.assertTrue(applies_to("mail-1"))
            self.assertFalse(applies_to("mail-2"))

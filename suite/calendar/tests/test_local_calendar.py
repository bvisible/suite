# //// Neoffice — added file (no upstream equivalent): the calendar of a desk user who has no mailbox
# //// (maintenance#1387, suite/calendar/local.py). Everything goes through the endpoints the calendar's screens call,
# //// on a local account: no mail server is needed, and none is touched (the users are made with the mailbox
# //// provisioning switched off, so a clone of a site with Stalwart does not create real mailboxes).
from __future__ import annotations

from unittest import mock

import frappe
from frappe.tests import IntegrationTestCase

DESK = "local-calendar-desk@example.com"
OTHER = "local-calendar-other@example.com"
PORTAL = "local-calendar-portal@example.com"
ZURICH = "Europe/Zurich"


def _user(email: str, user_type: str) -> str:
    if not frappe.db.exists("User", email):
        with mock.patch("suite.mail.events._should_provision_mail", return_value=False):
            user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": email,
                    "first_name": "Local calendar",
                    "send_welcome_email": 0,
                    "user_type": user_type,
                    "roles": [{"role": "System Manager"}] if user_type == "System User" else [],
                }
            )
            user.insert(ignore_permissions=True)
    frappe.db.set_value("User", email, {"user_type": user_type, "time_zone": ZURICH})
    return email


def _events(
    account: str, start: str = "2026-10-01T00:00:00Z", end: str = "2026-11-30T00:00:00Z"
) -> list[dict]:
    from suite.calendar.api import get_calendar_events

    return get_calendar_events(account, start, end, ZURICH)


class TestLocalCalendar(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for doctype in ("local_calendar_account", "local_calendar", "local_calendar_event"):
            frappe.reload_doc("calendar", "doctype", doctype)
        _user(DESK, "System User")
        _user(OTHER, "System User")
        _user(PORTAL, "Website User")

    def setUp(self):
        # The guard's way: where a mailbox could be made but was not, it asks for the local account.
        from suite.calendar.local import ensure_local_calendar_account

        frappe.set_user(DESK)
        self.account = ensure_local_calendar_account()

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_a_desk_user_without_a_mailbox_gets_a_calendar_of_his_own(self):
        from suite.calendar.api import get_calendars
        from suite.mail.api.account import get_user_info

        info = get_user_info()
        self.assertEqual(info.accounts, [])
        self.assertTrue(self.account.startswith("local-"))
        self.assertNotIn("|", self.account)
        self.assertEqual(info.local_calendar_account, self.account)  # the same one, made once
        defaults = [calendar for calendar in get_calendars(self.account) if calendar["default"]]
        self.assertEqual(len(defaults), 1)
        self.assertEqual(defaults[0]["may_write_all"], 1)

    def test_administrator_who_never_gets_a_mailbox_gets_a_calendar(self):
        # Jérémy, 09.10, on osiris as Administrator: « Aucun compte de calendrier pour le moment ».
        from suite.mail.api.account import get_user_info

        frappe.set_user("Administrator")
        account = get_user_info().local_calendar_account
        self.assertTrue(account and account.startswith("local-"))

    def test_where_a_mailbox_can_be_made_the_guard_tries_it_first(self):
        from suite.calendar.local import ensure_local_calendar_account
        from suite.mail.api.account import get_user_info

        frappe.set_user("Administrator")  # only Administrator may give a user the System Manager role
        fresh = _user("local-calendar-fresh@example.com", "System User")
        frappe.set_user(fresh)
        with mock.patch("suite.calendar.local.mailbox_possible", return_value=True):
            self.assertIsNone(get_user_info().local_calendar_account)
        self.assertTrue(ensure_local_calendar_account().startswith("local-"))

    def test_a_portal_user_gets_no_calendar(self):
        from suite.calendar.local import ensure_local_calendar_account
        from suite.mail.api.account import get_user_info

        frappe.set_user(PORTAL)
        self.assertIsNone(get_user_info().local_calendar_account)
        self.assertIsNone(ensure_local_calendar_account())

    def test_an_event_is_made_found_changed_and_deleted_through_the_calendar(self):
        from suite.calendar.api import edit_calendar_event
        from suite.calendar.doctype.calendar_event.calendar_event import (
            add_calendar_event,
            delete_calendar_events,
        )

        id = add_calendar_event(
            self.account,
            title="Visite de chantier",
            start="2026-10-12T09:00:00",
            duration="PT1H30M",
            time_zone=ZURICH,
            description="Avec le maître d'ouvrage",
            locations=[{"name": "Lausanne"}],
        )
        found = [event for event in _events(self.account) if event["id"] == id]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["title"], "Visite de chantier")
        self.assertEqual(found[0]["start"], "2026-10-12T09:00:00")
        self.assertEqual(found[0]["duration"], "PT1H30M")
        self.assertEqual(found[0]["time_zone"], ZURICH)
        self.assertEqual([location["_name"] for location in found[0]["locations"]], ["Lausanne"])
        self.assertEqual(len(found[0]["calendars"]), 1)

        edit_calendar_event(self.account, id, title="Visite reportée", start="2026-10-13T14:00:00")
        found = [event for event in _events(self.account) if event["id"] == id]
        self.assertEqual((found[0]["title"], found[0]["start"]), ("Visite reportée", "2026-10-13T14:00:00"))

        delete_calendar_events(self.account, [id])
        self.assertFalse([event for event in _events(self.account) if event["id"] == id])

    def test_a_weekly_series_unrolls_in_the_period_and_one_occurrence_can_go(self):
        from suite.calendar.doctype.calendar_event.calendar_event import (
            add_calendar_event,
            delete_calendar_event_instance,
        )

        master = add_calendar_event(
            self.account,
            title="Point d'équipe",
            start="2026-10-05T08:30:00",
            duration="PT30M",
            time_zone=ZURICH,
            recurrence_rule={
                "@type": "RecurrenceRule",
                "frequency": "weekly",
                "byDay": [{"day": "mo"}],
                "count": 4,
            },
        )
        series = sorted(
            (event for event in _events(self.account) if event.get("master_id") == master),
            key=lambda event: event["start"],
        )
        self.assertEqual(
            [event["start"] for event in series],
            ["2026-10-05T08:30:00", "2026-10-12T08:30:00", "2026-10-19T08:30:00", "2026-10-26T08:30:00"],
        )
        self.assertTrue(all(event["recurrence_id"] for event in series))

        delete_calendar_event_instance(self.account, master, series[1]["recurrence_id"])
        left = [event["start"] for event in _events(self.account) if event.get("master_id") == master]
        self.assertEqual(sorted(left), ["2026-10-05T08:30:00", "2026-10-19T08:30:00", "2026-10-26T08:30:00"])

    def test_a_series_keeps_its_wall_clock_across_the_change_of_hour(self):
        # Switzerland leaves summer time on 25.10.2026: 08:30 there is 06:30 UTC before, 07:30 UTC after.
        from suite.calendar.doctype.calendar_event.calendar_event import add_calendar_event
        from suite.calendar.local import LocalJMAPConnection, occurrences, parse_utc

        master = add_calendar_event(
            self.account,
            title="Café du lundi",
            start="2026-10-19T08:30:00",
            duration="PT15M",
            time_zone=ZURICH,
            recurrence_rule={"@type": "RecurrenceRule", "frequency": "weekly", "count": 2},
        )
        event = LocalJMAPConnection(self.account, DESK).event(master)
        utc = [
            instance["_start_utc"].strftime("%H:%M")
            for instance in occurrences(
                event, parse_utc("2026-10-01T00:00:00Z"), parse_utc("2026-11-30T00:00:00Z"), ZURICH
            )
        ]
        self.assertEqual(utc, ["06:30", "07:30"])

    def test_an_all_day_event_covers_its_day(self):
        from suite.calendar.doctype.calendar_event.calendar_event import add_calendar_event

        id = add_calendar_event(
            self.account,
            title="Fête du personnel",
            start="2026-10-16T00:00:00",
            duration="P1D",
            time_zone=ZURICH,
            show_without_time=True,
        )
        on_the_day = [
            event
            for event in _events(self.account, "2026-10-16T00:00:00Z", "2026-10-16T12:00:00Z")
            if event["id"] == id
        ]
        self.assertEqual(len(on_the_day), 1)
        self.assertEqual(on_the_day[0]["show_without_time"], 1)
        self.assertFalse(
            [
                event
                for event in _events(self.account, "2026-10-18T00:00:00Z", "2026-10-19T00:00:00Z")
                if event["id"] == id
            ]
        )

    def test_another_user_cannot_read_or_write_my_calendar(self):
        from suite.calendar.doctype.calendar_event.calendar_event import add_calendar_event

        # A System Manager may act on any account, as on a mail account: the other user is not one.
        frappe.set_user("Administrator")
        frappe.get_doc("User", OTHER).remove_roles("System Manager")
        frappe.set_user(OTHER)
        with self.assertRaises(frappe.ValidationError):
            _events(self.account)
        with self.assertRaises(frappe.ValidationError):
            add_calendar_event(
                self.account, title="Intrus", start="2026-10-12T09:00:00", duration="PT1H", time_zone=ZURICH
            )

    def test_a_local_calendar_sends_no_invitation(self):
        # With the client-side invitations on, adding an event with a participant queues the sending of an
        # invitation, which goes out through the mail server: a local calendar never queues it.
        from suite.calendar.doctype.calendar_event import calendar_event

        with (
            mock.patch.object(calendar_event, "custom_event_invites_enabled", return_value=True),
            mock.patch.object(calendar_event, "acting_as_organizer", return_value=True),
            mock.patch.object(calendar_event, "_enqueue_event_notification") as queued,
        ):
            calendar_event.add_calendar_event(
                self.account,
                title="Avec un invité",
                start="2026-10-14T10:00:00",
                duration="PT1H",
                time_zone=ZURICH,
                participants=[{"email": "guest@example.com", "name": "Guest", "roles": {"attendee": True}}],
                send_scheduling_messages=True,
            )
        queued.assert_not_called()

    def test_sharing_finds_nobody_to_share_with(self):
        from suite.calendar.doctype.calendar.calendar import get_shareable_principals

        self.assertEqual(get_shareable_principals(self.account), [])

    def test_a_calendar_is_added_renamed_hidden_and_removed_with_its_events(self):
        from suite.calendar.api import get_calendars
        from suite.calendar.doctype.calendar.calendar import (
            add_calendar,
            delete_calendars,
            set_calendar_visibility,
            update_calendar,
        )
        from suite.calendar.doctype.calendar_event.calendar_event import add_calendar_event

        calendar = add_calendar(self.account, name="Chantiers", color="#5F8A5A")
        update_calendar(self.account, calendar, name="Chantiers 2026", color="#5F8A5A")
        set_calendar_visibility(self.account, calendar, 0)
        mine = {c["id"]: c for c in get_calendars(self.account)}[calendar]
        self.assertEqual((mine["_name"], mine["visible"], mine["default"]), ("Chantiers 2026", 0, 0))

        id = add_calendar_event(
            self.account,
            calendar_ids=[calendar],
            title="Dalle",
            start="2026-10-20T07:00:00",
            duration="PT8H",
            time_zone=ZURICH,
        )
        self.assertEqual(
            [c["calendar_id"] for c in next(e for e in _events(self.account) if e["id"] == id)["calendars"]],
            [calendar],
        )

        delete_calendars(self.account, [calendar])
        self.assertNotIn(calendar, {c["id"] for c in get_calendars(self.account)})
        self.assertFalse([event for event in _events(self.account) if event["id"] == id])

    def test_what_needs_a_mail_account_says_so(self):
        from suite.calendar.local import LocalJMAPConnection

        connection = LocalJMAPConnection(self.account, DESK)
        with self.assertRaises(NotImplementedError):
            connection.request(json={"methodCalls": [["CalendarEvent/parse", {"blobIds": ["x"]}, "0"]]})

    def test_a_meet_room_is_attached_to_an_event_of_a_local_calendar(self):
        from suite.meet.api.schedule import create_meet_link, create_scheduled_meeting

        made = create_scheduled_meeting(
            account=self.account,
            title="Revue en visio",
            start="2026-10-15T15:00:00",
            duration="PT45M",
            time_zone=ZURICH,
        )
        self.assertIn("/meet/", made["meeting_url"])
        event = next(event for event in _events(self.account) if event["id"] == made["event_id"])
        self.assertIn(made["meeting_url"], [link["href"] for link in event["links"]])
        self.assertIn("/meet/", create_meet_link(self.account, title="Point")["meeting_url"])

    def test_participants_are_suggested_from_the_sites_users(self):
        from suite.mail.api.mail import get_email_suggestions

        # A desk user, found by a piece of his address (the other test user loses his desk role in another test).
        found = get_email_suggestions(self.account, "local-calendar-desk")
        self.assertEqual([suggestion["email"] for suggestion in found], [DESK])

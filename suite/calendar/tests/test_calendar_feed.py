# //// Neoffice — added file (no upstream equivalent): the person's agenda as an iCal address (maintenance#1428,
# //// suite/calendar/feed.py). The address, what it answers and what it publishes. The two calls of the calendar page
# //// are replaced where a mail server or a local account would be needed: what is checked is the address (made,
# //// shown again, revoked, refused), what the answer says (iCalendar, readable by a parser) and what is left out.
from __future__ import annotations

from datetime import date, timedelta
from unittest import mock

import frappe
from frappe.tests import IntegrationTestCase
from icalendar import Calendar

from suite.calendar import feed

DESK = "calendar-feed-desk@example.com"
OTHER = "calendar-feed-other@example.com"
PORTAL = "calendar-feed-portal@example.com"
ZURICH = "Europe/Zurich"


def _user(email: str, user_type: str = "System User") -> str:
    if not frappe.db.exists("User", email):
        with mock.patch("suite.mail.events._should_provision_mail", return_value=False):
            frappe.get_doc(
                {
                    "doctype": "User",
                    "email": email,
                    "first_name": "Calendar feed",
                    "send_welcome_email": 0,
                    "user_type": user_type,
                    "roles": [{"role": "System Manager"}] if user_type == "System User" else [],
                }
            ).insert(ignore_permissions=True)
    frappe.db.set_value("User", email, {"user_type": user_type, "enabled": 1, "time_zone": ZURICH})
    return email


def _event(**extra) -> dict:
    return {
        "id": "e1",
        "uid": "uid-1",
        "title": "Meeting",
        "start": "2026-10-12T14:00:00",
        "duration": "PT1H",
        "time_zone": ZURICH,
        "show_without_time": 0,
        "status": "Confirmed",
        "description": "",
        "locations": [],
        "calendars": [{"calendar": "acc|b", "calendar_id": "b", "calendar_name": "Perso"}],
        "recurrence_id": None,
        **extra,
    }


def _parse(content: bytes):
    return Calendar.from_ical(content)


def _components(content: bytes) -> list:
    return [component for component in _parse(content).walk("VEVENT")]


class AddressCase(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _user(DESK)
        _user(OTHER)
        _user(PORTAL, "Website User")

    def setUp(self):
        # What an earlier test did to a person (disabled, no longer a desk user) is not this test's.
        _user(DESK)
        _user(OTHER)
        _user(PORTAL, "Website User")
        frappe.db.delete("DefaultValue", {"parent": ["in", [DESK, OTHER, PORTAL]], "defkey": feed.PREF_KEY})
        self.addCleanup(frappe.set_user, "Administrator")

    def as_user(self, user):
        frappe.set_user(user)

    def token_of(self, answer):
        return answer["url"].rsplit("t=", 1)[1]


class TestTheAddress(AddressCase):
    def test_nobody_shares_until_they_ask_and_the_address_belongs_to_them_alone(self):
        self.as_user(DESK)
        self.assertEqual(feed.get_calendar_feed(), {"enabled": False, "url": ""})

        mine = feed.enable_calendar_feed()
        self.as_user(OTHER)
        theirs = feed.enable_calendar_feed()

        self.assertTrue(mine["enabled"])
        self.assertRegex(self.token_of(mine), r"^[0-9a-f]{48}$")
        self.assertIn("/api/method/suite.calendar.feed.calendar_feed?t=", mine["url"])
        self.assertEqual(feed.user_for(self.token_of(mine)), DESK)
        self.assertEqual(feed.user_for(self.token_of(theirs)), OTHER)
        self.assertNotEqual(self.token_of(mine), self.token_of(theirs))

    def test_the_address_can_be_shown_again_it_is_not_a_secret_kept_for_once(self):
        self.as_user(DESK)
        first = feed.enable_calendar_feed()

        self.assertEqual(feed.get_calendar_feed(), first)
        self.assertEqual(feed.enable_calendar_feed(), first, "asking twice does not change it")

    def test_a_token_that_is_not_the_person_s_is_nobody(self):
        self.as_user(DESK)
        token = self.token_of(feed.enable_calendar_feed())
        self.as_user(OTHER)
        other = self.token_of(feed.enable_calendar_feed())
        flipped = token[:-1] + ("0" if token[-1] != "0" else "1")

        for wrong in (flipped, other[:16] + token[16:], token[:16] + other[16:], token[:-2], token + "00", "", None, "z" * 48, token.upper()):
            self.assertIsNone(feed.user_for(wrong), repr(wrong))

    def test_a_new_address_replaces_the_old_one_wherever_it_was_pasted(self):
        self.as_user(DESK)
        old = self.token_of(feed.enable_calendar_feed())

        new = self.token_of(feed.regenerate_calendar_feed())

        self.assertNotEqual(old, new)
        self.assertIsNone(feed.user_for(old))
        self.assertEqual(feed.user_for(new), DESK)

    def test_stopping_the_share_closes_every_address_and_sharing_again_reopens_the_same(self):
        self.as_user(DESK)
        token = self.token_of(feed.enable_calendar_feed())

        stopped = feed.disable_calendar_feed()

        self.assertEqual(stopped, {"enabled": False, "url": ""})
        self.assertIsNone(feed.user_for(token))
        self.assertEqual(self.token_of(feed.enable_calendar_feed()), token)
        self.assertEqual(feed.user_for(token), DESK)

    def test_a_person_who_is_not_a_desk_user_any_more_reads_nothing(self):
        self.as_user(DESK)
        token = self.token_of(feed.enable_calendar_feed())

        frappe.db.set_value("User", DESK, "enabled", 0)
        self.assertIsNone(feed.user_for(token), "a disabled account")
        frappe.db.set_value("User", DESK, {"enabled": 1, "user_type": "Website User"})
        self.assertIsNone(feed.user_for(token), "an account that is no longer a desk account")

    def test_the_calls_to_manage_it_are_for_desk_users(self):
        for user in (PORTAL, "Guest"):
            self.as_user(user)
            for call in (
                feed.get_calendar_feed,
                feed.enable_calendar_feed,
                feed.regenerate_calendar_feed,
                feed.disable_calendar_feed,
            ):
                with self.assertRaises(frappe.PermissionError, msg=f"{user} {call.__name__}"):
                    call()


class TestWhatItPublishes(IntegrationTestCase):
    def render(self, events, shown=("b",)):
        return feed.render_ics(events, set(shown), name="Ada", time_zone=ZURICH)

    def test_an_hour_is_a_timed_event_in_its_own_zone_and_a_day_is_a_whole_day(self):
        content = self.render(
            [
                _event(),
                _event(
                    id="e2", uid="uid-2", title="Day off", start="2026-10-13T00:00:00", duration="P1D", show_without_time=1
                ),
                _event(
                    id="e3", uid="uid-3", title="Away", start="2026-10-14T00:00:00", duration="P3D", show_without_time=1
                ),
            ]
        )

        timed, day, span = _components(content)

        self.assertEqual(str(timed["summary"]), "Meeting")
        self.assertEqual(timed["dtstart"].dt.isoformat(), "2026-10-12T14:00:00+02:00")
        self.assertEqual(timed["dtend"].dt.isoformat(), "2026-10-12T15:00:00+02:00")
        self.assertIn(b"DTSTART;TZID=Europe/Zurich:20261012T140000", content)
        self.assertEqual(day["dtstart"].dt, date(2026, 10, 13))
        self.assertEqual(day["dtend"].dt, date(2026, 10, 14), "a whole day ends the day after, the way iCalendar says it")
        self.assertEqual((span["dtstart"].dt, span["dtend"].dt), (date(2026, 10, 14), date(2026, 10, 17)))

    def test_a_whole_day_without_a_duration_is_one_day(self):
        (component,) = _components(
            self.render([_event(start="2026-10-13T00:00:00", duration="", show_without_time=1)])
        )

        self.assertEqual((component["dtstart"].dt, component["dtend"].dt), (date(2026, 10, 13), date(2026, 10, 14)))

    def test_it_is_iCalendar_a_parser_reads_back_with_the_zone_it_names(self):
        content = self.render([_event()])

        calendar = _parse(content)

        self.assertEqual(str(calendar["version"]), "2.0")
        self.assertEqual(str(calendar["method"]), "PUBLISH")
        self.assertIn("Ada", str(calendar["x-wr-calname"]))
        self.assertEqual(str(calendar["x-wr-timezone"]), ZURICH)
        self.assertTrue(content.startswith(b"BEGIN:VCALENDAR\r\n"), "iCalendar lines end with CR LF")
        self.assertTrue(content.rstrip().endswith(b"END:VCALENDAR"))
        self.assertTrue(list(calendar.walk("VTIMEZONE")), "a zone that is named is defined")

    def test_only_the_calendars_the_person_shows_are_published(self):
        hidden = _event(
            id="e9", uid="uid-9", title="Hidden", calendars=[{"calendar": "acc|z", "calendar_id": "z", "calendar_name": "Old"}]
        )

        titles = [str(c["summary"]) for c in _components(self.render([_event(), hidden], shown=("b",)))]

        self.assertEqual(titles, ["Meeting"])
        self.assertEqual([str(c["summary"]) for c in _components(self.render([hidden], shown=()))], [])

    def test_a_date_of_the_erp_says_where_the_document_is_and_does_not_block_the_time(self):
        erp = _event(
            id="erp:tasks:todo:1",
            uid="erp:tasks:todo:1",
            title="Call the supplier",
            start="2026-10-13T00:00:00",
            duration="P1D",
            show_without_time=1,
            virtual=1,
            route="/app/todo/TODO-1",
            late=1,
            meta="Task",
            calendars=[{"calendar": "acc|erp:tasks", "calendar_id": "erp:tasks", "calendar_name": "To-dos and tasks"}],
        )

        (component,) = _components(self.render([erp], shown=("erp:tasks",)))

        self.assertTrue(str(component["url"]).endswith("/app/todo/TODO-1"))
        self.assertTrue(str(component["url"]).startswith("http"))
        self.assertEqual(str(component["transp"]), "TRANSPARENT")
        self.assertIn("Task", str(component["description"]))
        self.assertIn("Late", str(component["description"]))
        self.assertIn("To-dos and tasks", component["categories"].to_ical().decode())

    def test_each_occurrence_of_a_repeating_event_is_an_event_of_its_own(self):
        events = [
            _event(id="a", uid="series", start="2026-10-12T09:00:00", recurrence_id="2026-10-12T09:00:00"),
            _event(id="b", uid="series", start="2026-10-19T09:00:00", recurrence_id="2026-10-19T09:00:00"),
            _event(id="c", uid="single", start="2026-10-20T09:00:00"),
        ]

        uids = [str(component["uid"]) for component in _components(self.render(events))]

        self.assertEqual(len(set(uids)), 3, "the same address twice would be one event for the reader")
        self.assertTrue(uids[2].startswith("single@"), "an event that does not repeat keeps its address")

    def test_what_a_title_may_hold_is_escaped_and_what_is_missing_is_left_out(self):
        tricky = _event(title="Lunch, with: Ada; Bob\nand Carol", description="Line one\nLine two", locations=[{"name": "Café, Lausanne"}])
        no_start = _event(id="n", uid="n", start="")

        components = _components(self.render([tricky, no_start]))

        self.assertEqual(len(components), 1)
        self.assertEqual(str(components[0]["summary"]), "Lunch, with: Ada; Bob\nand Carol")
        self.assertEqual(str(components[0]["location"]), "Café, Lausanne")
        self.assertEqual(str(components[0]["description"]), "Line one\nLine two")

    def test_a_zone_nobody_knows_and_a_duration_of_nothing_do_not_stop_the_feed(self):
        odd = _event(time_zone="Mars/Olympus", duration="PT0S")

        (component,) = _components(self.render([odd]))

        self.assertEqual(component["dtstart"].dt.isoformat()[:19], "2026-10-12T14:00:00")
        self.assertEqual(component["dtend"].dt - component["dtstart"].dt, timedelta(minutes=30))

    def test_durations_are_read_as_iso_8601(self):
        self.assertEqual(feed.parse_duration("PT1H30M"), timedelta(hours=1, minutes=30))
        self.assertEqual(feed.parse_duration("P2D"), timedelta(days=2))
        self.assertEqual(feed.parse_duration("P1W"), timedelta(weeks=1))
        self.assertEqual(feed.parse_duration("P1DT2H"), timedelta(days=1, hours=2))
        self.assertEqual(feed.parse_duration("nonsense"), timedelta(0))
        self.assertEqual(feed.parse_duration(None), timedelta(0))


class TestWhatItReads(AddressCase):
    def test_it_reads_the_two_calls_of_the_calendar_page_as_the_person_around_today(self):
        calls, acting = [], []

        def get_calendars(account, erp_dates=0):
            acting.append(frappe.session.user)
            return [
                {"id": "b", "visible": 1},
                {"id": "z", "visible": 0},
                {"id": "erp:tasks", "visible": 1},
            ]

        def get_calendar_events(account, from_date, to_date, time_zone, erp_dates=0):
            acting.append(frappe.session.user)
            calls.append((account, from_date, to_date, time_zone, erp_dates))
            return [_event(id=f"e-{from_date}", uid=f"u-{from_date}", start=from_date[:10] + "T10:00:00")]

        with mock.patch.object(feed, "_account_of", return_value="acc"), mock.patch(
            "suite.calendar.api.get_calendars", side_effect=get_calendars
        ), mock.patch("suite.calendar.api.get_calendar_events", side_effect=get_calendar_events):
            content = feed.build_ics(DESK)

        self.assertEqual(set(acting), {DESK}, "as the person, not as the one who asked")
        self.assertEqual(frappe.session.user, "Administrator", "and the caller's session is back")
        self.assertTrue(all(call[0] == "acc" and call[3] == ZURICH and call[4] == 1 for call in calls))
        first = date.fromisoformat(calls[0][1][:10])
        last = date.fromisoformat(calls[-1][2][:10])
        today = frappe.utils.getdate()
        self.assertEqual(first, today - timedelta(days=feed.DAYS_BEFORE))
        self.assertEqual(last, today + timedelta(days=feed.DAYS_AFTER))
        for (_a, from_date, to_date, *_rest), following in zip(calls, calls[1:] + [None]):
            self.assertLessEqual(
                (date.fromisoformat(to_date[:10]) - date.fromisoformat(from_date[:10])).days, feed.CHUNK_DAYS
            )
            self.assertRegex(from_date, r"^\d{4}-\d{2}-\d{2}T00:00:00Z$")
            if following:
                self.assertEqual(to_date, following[1], "the chunks follow each other, without a gap or a repeat")
        self.assertEqual(len(_components(content)), len(calls))

    def test_an_event_that_two_chunks_both_return_is_published_once(self):
        same = _event(id="long", uid="long", start="2026-10-12T10:00:00")
        with mock.patch.object(feed, "_account_of", return_value="acc"), mock.patch(
            "suite.calendar.api.get_calendars", return_value=[{"id": "b", "visible": 1}]
        ), mock.patch("suite.calendar.api.get_calendar_events", return_value=[same]):
            content = feed.build_ics(DESK)

        self.assertEqual(len(_components(content)), 1)

    def test_a_person_without_a_calendar_account_publishes_an_empty_calendar(self):
        with mock.patch.object(feed, "_account_of", return_value=None):
            content = feed.build_ics(DESK)

        self.assertEqual(_components(content), [])
        self.assertEqual(str(_parse(content)["version"]), "2.0")


class TestWhatTheAddressAnswers(AddressCase):
    def setUp(self):
        super().setUp()
        frappe.cache.delete_value(feed._cache_key(DESK))
        frappe.local.response = frappe._dict()

    def test_a_good_address_answers_iCalendar_that_a_calendar_shows_instead_of_downloading(self):
        self.as_user(DESK)
        token = self.token_of(feed.enable_calendar_feed())
        frappe.set_user("Guest")

        with mock.patch.object(feed, "build_ics", return_value=b"BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n"):
            feed.calendar_feed(token)

        response = frappe.local.response
        self.assertEqual(response.type, "download")
        self.assertEqual(response.content_type, "text/calendar; charset=utf-8")
        self.assertEqual(response.display_content_as, "inline")
        self.assertEqual(response.filecontent, b"BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n")
        self.assertTrue(response.filename.endswith(".ics"))

    def test_an_address_that_is_not_one_is_not_found_and_says_nothing_of_why(self):
        for token in ("", "not-a-token", "0" * 48):
            with self.assertRaises(frappe.DoesNotExistError, msg=repr(token)):
                feed.calendar_feed(token)

    def test_an_address_that_was_stopped_is_not_found(self):
        self.as_user(DESK)
        token = self.token_of(feed.enable_calendar_feed())
        feed.disable_calendar_feed()
        frappe.set_user("Guest")

        with self.assertRaises(frappe.DoesNotExistError):
            feed.calendar_feed(token)

    def test_what_was_built_is_kept_for_a_few_minutes_and_dropped_when_the_address_changes(self):
        self.as_user(DESK)
        token = self.token_of(feed.enable_calendar_feed())
        frappe.set_user("Guest")

        with mock.patch.object(feed, "build_ics", return_value=b"one") as build:
            feed.calendar_feed(token)
            feed.calendar_feed(token)
            self.assertEqual(build.call_count, 1)
            self.as_user(DESK)
            new = self.token_of(feed.regenerate_calendar_feed())
            frappe.set_user("Guest")
            feed.calendar_feed(new)
            self.assertEqual(build.call_count, 2, "a new address is a new answer")

# //// Neoffice — added file (no upstream equivalent): the calendars other people shared with the person, in their
# //// own calendar (maintenance#1579, suite/calendar/shared.py). No mail server is touched: what the other accounts
# //// answer is put in place with mocks, the way the calls that read them return it.
from __future__ import annotations

from unittest import mock

import frappe
from frappe.tests import IntegrationTestCase

from suite.calendar import shared
from suite.calendar.shared import compose, resolves_shared, split_id

ME = "test-shared-me"
THEIRS = "test-shared-theirs"
OTHER = "test-shared-other"


def _calendar(calendar_id: str, title: str, **over) -> dict:
    return {
        "name": f"{THEIRS}|{calendar_id}",
        "_name": title,
        "id": calendar_id,
        "color": None,
        "description": None,
        "visible": 1,
        "default": 1,
        "subscribed": 1,
        "may_admin": 0,
        "may_write_all": 0,
        "may_delete": 0,
        "may_read_items": 1,
        **over,
    }


class TestComposedIds(IntegrationTestCase):
    def test_an_id_of_another_account_names_its_account(self):
        self.assertEqual(compose("c", "e1"), "c~e1")
        self.assertEqual(split_id("c~e1"), ("c", "e1"))

    def test_a_plain_id_is_left_alone(self):
        self.assertEqual(split_id("e1"), (None, "e1"))
        self.assertEqual(split_id(None), (None, None))
        self.assertEqual(split_id("~e1"), (None, "~e1"))  # no account named: not one of ours
        self.assertEqual(split_id("c~"), (None, "c~"))


class TestResolvesShared(IntegrationTestCase):
    def test_a_call_with_plain_ids_goes_through_untouched(self):
        @resolves_shared("id", lists=("calendar_ids",))
        def endpoint(account, id, calendar_ids=None):
            return account, id, calendar_ids

        self.assertEqual(endpoint("e", "x", ["k"]), ("e", "x", ["k"]))

    def test_an_id_that_names_an_account_makes_the_call_on_that_account(self):
        @resolves_shared("id", lists=("calendar_ids",))
        def endpoint(account, id, calendar_ids=None):
            return account, id, calendar_ids

        self.assertEqual(endpoint("e", "c~x", ["c~k"]), ("c", "x", ["k"]))
        self.assertEqual(endpoint(account="e", id="c~x"), ("c", "x", None))

    def test_a_list_of_ids_of_one_other_account(self):
        @resolves_shared(lists=("ids",))
        def endpoint(account, ids, send=False):
            return account, ids

        self.assertEqual(endpoint("e", ["c~a", "c~b"]), ("c", ["a", "b"]))

    def test_the_ids_taken_through_kwargs_are_read_too(self):
        @resolves_shared("id", lists=("calendar_ids",))
        def endpoint(account, id, **kwargs):
            return account, id, kwargs

        # edit_calendar_event takes the calendars in **kwargs, with a lot of other fields that are left as they are
        account, id, kwargs = endpoint("e", "c~x", calendar_ids=["c~k"], title="T")
        self.assertEqual((account, id), ("c", "x"))
        self.assertEqual(kwargs, {"calendar_ids": ["k"], "title": "T"})

    def test_two_accounts_in_one_call_are_refused(self):
        @resolves_shared("id", lists=("calendar_ids",))
        def endpoint(account, id, calendar_ids=None):
            return account

        with self.assertRaises(frappe.ValidationError):
            endpoint("e", "c~x", ["d~k"])

    def test_a_plain_id_next_to_an_id_of_another_account_is_refused(self):
        @resolves_shared("id", lists=("calendar_ids",))
        def endpoint(account, id, calendar_ids=None):
            return account

        # An event of the person's own account cannot be moved to a calendar of another account
        with self.assertRaises(frappe.ValidationError):
            endpoint("e", "x", ["c~k"])
        # …but a plain id on the account the call names is that account's: fine
        self.assertEqual(endpoint("c", "x", ["c~k"]), "c")

    def test_what_the_function_does_not_name_is_dropped_as_frappe_does_it(self):
        @resolves_shared("id")
        def endpoint(account, id):
            return account, id

        self.assertEqual(endpoint("e", "c~x", cmd="suite.calendar.api.x", data=1), ("c", "x"))


class TestSharedCalendarsAndEvents(IntegrationTestCase):
    def setUp(self):
        self.owner = mock.patch.object(shared, "owner_label", return_value="Alex")
        self.owner.start()

    def tearDown(self):
        self.owner.stop()

    def test_the_other_accounts_are_the_ones_of_the_user_that_are_not_the_one_open(self):
        with (
            mock.patch(
                "suite.mail.doctype.user_account.user_account.get_user_jmap_accounts",
                return_value=[ME, THEIRS, OTHER],
            ),
            mock.patch.object(shared, "_linked_with_session", side_effect=lambda user, linked: linked),
        ):
            self.assertEqual(shared.other_accounts(ME), [THEIRS, OTHER])
            # an account that is not the person's is not a starting point
            self.assertEqual(shared.other_accounts("test-shared-stranger"), [])

    def test_an_account_the_session_lists_without_a_link_is_linked_first(self):
        # The session was cached and the link was not made (the request that made it failed): the server's session
        # still says the person reaches that account, so the link is made as it is when the state changes.
        connection = mock.Mock(accounts={ME: {}, THEIRS: {}})
        with (
            mock.patch(
                "suite.mail.doctype.user_account.user_account.get_user_jmap_accounts", return_value=[ME]
            ),
            mock.patch("suite.mail.jmap.get_jmap_connection", return_value=connection),
            mock.patch("suite.mail.doctype.jmap_account.jmap_account.sync_jmap_accounts") as sync,
            mock.patch.object(shared.frappe.db, "get_all", return_value=[ME, THEIRS]),
        ):
            self.assertEqual(shared.other_accounts(ME), [THEIRS])

        sync.assert_called_once_with(frappe.session.user, connection.accounts)

    def test_a_session_that_lists_nothing_new_makes_no_link(self):
        connection = mock.Mock(accounts={ME: {}, THEIRS: {}})
        with (
            mock.patch(
                "suite.mail.doctype.user_account.user_account.get_user_jmap_accounts",
                return_value=[ME, THEIRS],
            ),
            mock.patch("suite.mail.jmap.get_jmap_connection", return_value=connection),
            mock.patch("suite.mail.doctype.jmap_account.jmap_account.sync_jmap_accounts") as sync,
        ):
            self.assertEqual(shared.other_accounts(ME), [THEIRS])

        sync.assert_not_called()

    def test_a_calendar_kept_in_neoffice_has_no_other_accounts(self):
        with mock.patch("suite.calendar.local.is_local_account", return_value=True):
            self.assertEqual(shared.other_accounts("local-abc"), [])

    def test_the_calendars_of_another_account_come_as_the_person_s_own_do_with_a_shared_mark(self):
        calendars = [
            _calendar("c", "Calendrier", may_write_all=1),
            _calendar("k", "Free busy only", may_read_items=0),
        ]
        with (
            mock.patch.object(shared, "other_accounts", return_value=[THEIRS]),
            mock.patch("suite.calendar.doctype.calendar.calendar.fetch_calendars", return_value=calendars),
        ):
            listed = shared.shared_calendars(ME)

        self.assertEqual(len(listed), 1)  # the one the person may not read items of is not there
        calendar = listed[0]
        self.assertEqual(calendar["id"], f"{THEIRS}~c")
        self.assertEqual(calendar["name"], f"{THEIRS}|c")
        self.assertEqual(calendar["_name"], "Calendrier (Alex)")
        self.assertEqual(calendar["shared_with_me"], 1)
        self.assertEqual(calendar["default"], 0)  # not THEIR default: an event goes to their own
        self.assertEqual(calendar["may_write_all"], 1)

    def test_an_account_that_does_not_answer_costs_its_calendars_not_the_page(self):
        def answer(account, **_):
            if account == THEIRS:
                raise RuntimeError("withdrawn")
            return [_calendar("c", "Other", name=f"{OTHER}|c")]

        with (
            mock.patch.object(shared, "other_accounts", return_value=[THEIRS, OTHER]),
            mock.patch("suite.calendar.doctype.calendar.calendar.fetch_calendars", side_effect=answer),
        ):
            listed = shared.shared_calendars(ME)

        self.assertEqual([c["id"] for c in listed], [f"{OTHER}~c"])

    def test_the_events_of_another_account_carry_ids_that_name_it_and_skip_the_ones_the_person_has(self):
        events = [
            {"id": "e1", "uid": "mine-too", "master_id": "e1"},
            {"id": "e2", "uid": "only-theirs", "master_id": "m2"},
        ]
        with (
            mock.patch.object(shared, "other_accounts", return_value=[THEIRS]),
            mock.patch(
                "suite.calendar.doctype.calendar_event.calendar_event.fetch_calendar_events",
                return_value=(events, 2),
            ),
            mock.patch("suite.calendar.api.enrich_events_with_master_data"),
        ):
            listed = shared.shared_events(
                ME, "2026-10-01T00:00:00Z", "2026-11-01T00:00:00Z", "Europe/Zurich", {"mine-too"}
            )

        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["id"], f"{THEIRS}~e2")
        self.assertEqual(listed[0]["master_id"], f"{THEIRS}~m2")
        self.assertEqual(listed[0]["shared_with_me"], 1)

    def test_the_calendar_page_gets_them_only_when_it_asks(self):
        from suite.calendar.api import get_calendars

        extra = [{"id": f"{THEIRS}~c", "shared_with_me": 1}]
        with (
            mock.patch("suite.calendar.api.ensure_default_alerts"),
            mock.patch(
                "suite.calendar.api.fetch_calendars", return_value=[_calendar("m", "Mine", name="me|m")]
            ),
            mock.patch("suite.calendar.api.shared_calendars", return_value=extra),
        ):
            plain = get_calendars(ME)
            with_shared = get_calendars(ME, shared=1)

        self.assertEqual([c["id"] for c in plain], ["m"])
        self.assertEqual([c["id"] for c in with_shared], ["m", f"{THEIRS}~c"])

# //// Neoffice — added file (no upstream equivalent): which of a user's accounts is their own mailbox
# //// (maintenance#1579, suite.mail.doctype.user_account.get_personal_accounts_of_user). The mail server is not
# //// needed and none is touched: the accounts are rows, and the session of each user is put in the cache the
# //// JMAP layer reads (jmap:sessions) the way the server's answer would be.
from __future__ import annotations

from unittest import mock

import frappe
from frappe.tests import IntegrationTestCase

from suite.mail.doctype.user_account.user_account import get_user_personal_jmap_account

OWNER = "shared-box-owner@example.com"
COLLEAGUE = "shared-box-colleague@example.com"
LATE = "shared-box-late@example.com"  # linked to a mailbox his cached session does not list yet
OWNERS_BOX = "test-shared-box-owners"
COLLEAGUES_BOX = "test-shared-box-colleagues"
LATE_BOX = "test-shared-box-late"
SESSIONS = "jmap:sessions"


def _user(email: str) -> None:
    if not frappe.db.exists("User", email):
        with mock.patch("suite.mail.events._should_provision_mail", return_value=False):
            frappe.get_doc(
                {
                    "doctype": "User",
                    "email": email,
                    "first_name": "Shared box",
                    "send_welcome_email": 0,
                    "user_type": "System User",
                }
            ).insert(ignore_permissions=True)
    # A user with no role is made a Website User on insert: the dates of the ERP are a desk user's.
    frappe.db.set_value("User", email, "user_type", "System User")


def _account(account_id: str, name: str) -> None:
    # Flagged personal, as the first session to see it (the owner's) writes it.
    frappe.get_doc(
        {
            "doctype": "JMAP Account",
            "name": account_id,
            "account_id": account_id,
            "_name": name,
            "is_personal": 1,
        }
    ).db_insert()


def _link(user: str, account: str) -> None:
    frappe.get_doc(
        {"doctype": "User Account", "name": f"{user}|{account}", "user": user, "account": account}
    ).db_insert()


def _session(user: str, personal: dict[str, bool] | None) -> None:
    """The session of `user` as the server's answer: which accounts it calls personal. None: not in the cache."""

    if personal is None:
        frappe.cache.hdel(SESSIONS, user)
        return
    accounts = {account: {"name": account, "isPersonal": flag} for account, flag in personal.items()}
    frappe.cache.hset(SESSIONS, user, {"accounts": accounts})


class TestPersonalAccountOfASharedMailbox(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _user(OWNER)
        _user(COLLEAGUE)
        _account(OWNERS_BOX, "owner@example.com")
        _account(COLLEAGUES_BOX, "colleague@example.com")
        _account(LATE_BOX, "late@example.com")
        # The owner's mailbox is shared with the colleague, who also has his own, linked after it.
        _link(OWNER, OWNERS_BOX)
        _link(COLLEAGUE, OWNERS_BOX)
        _link(COLLEAGUE, COLLEAGUES_BOX)
        _link(LATE, OWNERS_BOX)
        _link(LATE, LATE_BOX)

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        accounts = [OWNERS_BOX, COLLEAGUES_BOX, LATE_BOX]
        frappe.db.delete("User Account", {"account": ("in", accounts)})
        frappe.db.delete("JMAP Account", {"name": ("in", accounts)})
        for user in (OWNER, COLLEAGUE, LATE):
            frappe.cache.hdel(SESSIONS, user)
        for user in (OWNER, COLLEAGUE):
            if frappe.db.exists("User", user):
                frappe.delete_doc("User", user, force=True, ignore_permissions=True)
        super().tearDownClass()

    def setUp(self):
        self._forget_request_cache()
        for user in (OWNER, COLLEAGUE, LATE):
            _session(user, None)

    def tearDown(self):
        frappe.set_user("Administrator")
        self._forget_request_cache()

    @staticmethod
    def _forget_request_cache():
        # get_user_jmap_accounts is cached for the length of a request; a test is not one.
        cache = getattr(frappe.local, "request_cache", None)
        if cache is not None:
            cache.clear()

    def test_a_mailbox_shared_by_a_colleague_is_not_the_users_personal_account(self):
        _session(COLLEAGUE, {OWNERS_BOX: False, COLLEAGUES_BOX: True})

        self.assertEqual(get_user_personal_jmap_account(COLLEAGUE), COLLEAGUES_BOX)
        # No « several personal accounts » refusal for the one who has two mailboxes
        self.assertEqual(get_user_personal_jmap_account(COLLEAGUE, raise_exception=True), COLLEAGUES_BOX)

    def test_the_owner_keeps_the_mailbox_as_personal(self):
        _session(OWNER, {OWNERS_BOX: True})

        self.assertEqual(get_user_personal_jmap_account(OWNER, raise_exception=True), OWNERS_BOX)

    def test_without_a_session_in_the_cache_the_flag_of_the_document_answers(self):
        # What upstream does: both documents say personal, so there is no one answer.
        self.assertIsNone(get_user_personal_jmap_account(COLLEAGUE))
        with self.assertRaises(frappe.ValidationError):
            get_user_personal_jmap_account(COLLEAGUE, raise_exception=True)

    def test_a_session_that_names_no_personal_account_leaves_the_flag_of_the_document(self):
        _session(COLLEAGUE, {OWNERS_BOX: False, COLLEAGUES_BOX: False})

        self.assertIsNone(get_user_personal_jmap_account(COLLEAGUE))

    def test_a_mailbox_the_session_does_not_list_keeps_the_flag_of_the_document(self):
        # A session older than the link: what it says is kept, what it does not know is the document's.
        _session(LATE, {OWNERS_BOX: False, "test-shared-box-other": True})

        self.assertEqual(get_user_personal_jmap_account(LATE, raise_exception=True), LATE_BOX)

    def test_the_accounts_of_the_user_info_are_flagged_the_way_the_server_says_it(self):
        from suite.mail.api.account import get_user_info

        _session(COLLEAGUE, {OWNERS_BOX: False, COLLEAGUES_BOX: True})
        frappe.set_user(COLLEAGUE)

        accounts = {account["id"]: account["is_personal"] for account in get_user_info().accounts}

        # The calendar and the mail open the first personal account: it is his own.
        self.assertEqual(accounts, {OWNERS_BOX: False, COLLEAGUES_BOX: True})

    def test_the_dates_of_the_erp_go_to_his_own_mailbox_not_to_the_shared_one(self):
        from suite.calendar.sources import applies_to

        _session(COLLEAGUE, {OWNERS_BOX: False, COLLEAGUES_BOX: True})
        frappe.set_user(COLLEAGUE)

        self.assertTrue(applies_to(COLLEAGUES_BOX))
        self.assertFalse(applies_to(OWNERS_BOX))

    def test_an_account_the_session_lists_without_a_link_is_linked_when_the_session_is_read(self):
        from suite.mail.doctype.user_account.user_account import warm_user_jmap_session

        connection = mock.Mock(
            accounts={COLLEAGUES_BOX: {}, OWNERS_BOX: {}, LATE_BOX: {}, "test-shared-box-new": {}}
        )
        with (
            mock.patch("suite.mail.jmap.get_jmap_connection", return_value=connection),
            mock.patch("suite.mail.doctype.jmap_account.jmap_account.sync_jmap_accounts") as sync,
        ):
            warm_user_jmap_session(COLLEAGUE)  # linked to the first two only: a new account is listed
            sync.assert_called_once_with(COLLEAGUE, connection.accounts)

        connection = mock.Mock(accounts={COLLEAGUES_BOX: {}, OWNERS_BOX: {}})
        with (
            mock.patch("suite.mail.jmap.get_jmap_connection", return_value=connection),
            mock.patch("suite.mail.doctype.jmap_account.jmap_account.sync_jmap_accounts") as sync,
        ):
            warm_user_jmap_session(COLLEAGUE)  # nothing the person has no link to
            sync.assert_not_called()

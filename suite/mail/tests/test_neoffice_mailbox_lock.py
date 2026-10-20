# //// Neoffice — added file (no upstream equivalent): the mailbox of a deleted desk user is locked, its mail
# //// kept, on our own Stalwart (suite/mail/neoffice_stalwart.lock_account, suite/mail/events.lock_own_mailbox;
# //// maintenance#1743). Stalwart is never reached: its management API is played by a fake.
from __future__ import annotations

from typing import ClassVar
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

from suite.mail import events, neoffice_stalwart

ADDRESS = "ada@mail.example.org"


class FakeManagement:
    """Stalwart's management API as lock_account sees it: one domain, accounts named "ada" in two domains and
    "adam" beside them (a query by name matches as loosely as a substring), one app password; every call is kept,
    with the login it was made as. `left` is what reading the credentials back finds."""

    calls: ClassVar[list[tuple[str | None, str, dict]]] = []
    domains: ClassVar[dict[str, str]] = {"mail.example.org": "d1"}
    accounts: ClassVar[list[dict]] = [
        {"id": "a0", "name": "ada", "domainId": "d0"},
        {"id": "a2", "name": "adam", "domainId": "d1"},
        {"id": "a1", "name": "ada", "domainId": "d1"},
    ]
    left: ClassVar[dict] = {"0": {"@type": "Password"}}

    def __init__(self, login: str | None = None) -> None:
        self.login = login
        self.admin = "admin"

    def __enter__(self) -> FakeManagement:
        return self

    def __exit__(self, *exc: object) -> None:
        pass

    def call(self, method: str, **arguments) -> dict:
        FakeManagement.calls.append((self.login, method, arguments))
        if method == "Domain/query":
            found = self.domains.get(arguments["filter"]["name"])
            return {"ids": [found] if found else []}
        if method == "Account/query":
            name = arguments["filter"]["name"]
            return {"ids": [a["id"] for a in self.accounts if name in a["name"]]}
        if method == "Account/get":
            if arguments.get("properties") == ["credentials"]:
                return {"list": [{"credentials": self.left}]}
            return {"list": [a for a in self.accounts if a["id"] in arguments["ids"]]}
        if method == "AppPassword/query":
            return {"ids": ["p1"]}
        return {}

    find_id = neoffice_stalwart.Management.find_id
    _fail = staticmethod(neoffice_stalwart.Management._fail)


class TestLockAccount(IntegrationTestCase):
    def setUp(self) -> None:
        FakeManagement.calls = []
        FakeManagement.left = {"0": {"@type": "Password"}}

    def lock(self, address: str) -> bool:
        with patch.object(neoffice_stalwart, "Management", FakeManagement):
            return neoffice_stalwart.lock_account(address)

    def sets(self) -> list[tuple[str | None, dict]]:
        return [(login, args) for login, method, args in FakeManagement.calls if method.endswith("/set")]

    def test_the_credentials_become_one_password_nobody_holds_and_the_app_passwords_go(self) -> None:
        self.assertTrue(self.lock(" Ada@Mail.Example.org "))
        sets = self.sets()
        self.assertEqual([login for login, _ in sets], [None, f"{ADDRESS}%admin"])
        update = sets[0][1]["update"]
        self.assertEqual(list(update), ["a1"], "the account of that domain and that very name")
        credentials = update["a1"]["credentials"]
        self.assertEqual((list(credentials), credentials["0"]["@type"]), (["0"], "Password"))
        self.assertEqual(len(credentials["0"]["secret"]), 40)
        self.assertEqual(sets[1][1], {"destroy": ["p1"]}, "revoked as the account itself")
        self.assertFalse(any("destroy" in args for login, args in sets if login is None), "the account stays")

    def test_a_near_name_is_never_taken_for_the_name(self) -> None:
        self.assertTrue(self.lock("adam@mail.example.org"))
        self.assertEqual(list(self.sets()[0][1]["update"]), ["a2"])

    def test_two_locks_never_share_a_password(self) -> None:
        self.lock(ADDRESS)
        self.lock(ADDRESS)
        secrets = [
            args["update"]["a1"]["credentials"]["0"]["secret"] for login, args in self.sets() if login is None
        ]
        self.assertEqual(len(set(secrets)), 2)

    def test_a_server_that_keeps_another_credential_is_a_failure(self) -> None:
        FakeManagement.left = {"0": {"@type": "Password"}, "1": {"@type": "ApiKey"}}
        with self.assertRaises(frappe.ValidationError):
            self.lock(ADDRESS)

    def test_the_administrator_is_never_locked(self) -> None:
        for address in ("admin", "admin@mail.example.org"):
            with self.assertRaises(frappe.ValidationError):
                self.lock(address)
        self.assertEqual(self.sets(), [])

    def test_an_address_the_server_does_not_have_changes_nothing(self) -> None:
        for address in (
            "ada@elsewhere.example.org",
            "grace@mail.example.org",
            "no-domain",
            "@mail.example.org",
        ):
            FakeManagement.calls = []
            self.assertFalse(self.lock(address), address)
            self.assertEqual(self.sets(), [], address)


class UserCase(IntegrationTestCase):
    """A Website user (no mailbox is made for one) whose settings name a mailbox; everything around Stalwart played."""

    def setUp(self) -> None:
        frappe.set_user("Administrator")
        self.others: list[str] = []
        self.user = self.make_user(ADDRESS.upper())

    def make_user(self, username: str) -> str:
        user = f"lock-test-{frappe.generate_hash(length=6)}@example.org"
        frappe.get_doc(
            {
                "doctype": "User",
                "email": user,
                "first_name": "Lock",
                "user_type": "Website User",
                "send_welcome_email": 0,
            }
        ).insert(ignore_permissions=True)
        if not frappe.db.exists("User Settings", {"user": user}):
            frappe.get_doc({"doctype": "User Settings", "user": user}).insert(
                ignore_permissions=True, ignore_mandatory=True
            )
        frappe.db.set_value("User Settings", {"user": user}, "username", username)
        return user

    def tearDown(self) -> None:
        # Never the real server: whatever a test left goes without its mailbox being looked for.
        with patch.object(events, "is_stalwart_configured", return_value=False):
            for user in [self.user, *self.others]:
                if frappe.db.exists("User", user):
                    frappe.delete_doc("User", user, ignore_permissions=True, force=True)

    def played(self, cloud: bool, change) -> tuple[MagicMock, MagicMock, MagicMock]:
        enqueue, cloud_call, clear = MagicMock(), MagicMock(), MagicMock()
        with (
            patch.object(events, "is_suite_cloud_configured", return_value=cloud),
            patch.object(events, "is_stalwart_configured", return_value=True),
            patch.object(events, "is_jmap_configured", return_value=False),
            patch.object(events, "delete_mail_account", cloud_call),
            patch.object(events, "set_account_enabled", cloud_call),
            patch.object(events.frappe, "enqueue", enqueue),
            patch("suite.mail.jmap.clear_jmap_session", clear),
        ):
            change()
        return enqueue, cloud_call, clear

    @staticmethod
    def jobs(enqueue: MagicMock, method: str) -> list:
        return [c for c in enqueue.call_args_list if c.args and c.args[0] == f"suite.mail.events.{method}"]

    def set_enabled(self, enabled: int) -> None:
        doc = frappe.get_doc("User", self.user)
        doc.enabled = enabled
        doc.save(ignore_permissions=True)


class TestDeletedUser(UserCase):
    def delete(self, cloud: bool) -> tuple[MagicMock, MagicMock, MagicMock]:
        return self.played(
            cloud, lambda: frappe.delete_doc("User", self.user, ignore_permissions=True, force=True)
        )

    def test_on_our_own_server_the_lock_waits_for_the_commit_and_the_mailbox_is_kept(self) -> None:
        enqueue, cloud_call, clear = self.delete(False)
        jobs = self.jobs(enqueue, "lock_mailbox_now")
        self.assertEqual(len(jobs), 1)
        self.assertEqual((jobs[0].kwargs["address"], jobs[0].kwargs["user"]), (ADDRESS, self.user))
        self.assertTrue(
            jobs[0].kwargs["enqueue_after_commit"], "a deletion refused after on_trash locks nothing"
        )
        clear.assert_called_once_with(self.user)
        cloud_call.assert_not_called()
        self.assertFalse(frappe.db.exists("User", self.user))

    def test_a_mailbox_another_user_names_too_stays_open(self) -> None:
        self.others.append(self.make_user(ADDRESS))
        enqueue, _, _ = self.delete(False)
        self.assertEqual(self.jobs(enqueue, "lock_mailbox_now"), [])

    def test_with_suite_cloud_upstream_s_way_is_left_as_it_is(self) -> None:
        enqueue, _, _ = self.delete(True)
        self.assertEqual(self.jobs(enqueue, "lock_mailbox_now"), [])


class TestDisabledUser(UserCase):
    def test_disabled_the_mailbox_is_locked_after_the_commit_and_enabled_it_opens_again(self) -> None:
        enqueue, cloud_call, _ = self.played(False, lambda: self.set_enabled(0))
        locks = self.jobs(enqueue, "lock_mailbox_now")
        self.assertEqual(
            [(c.kwargs["address"], c.kwargs["user"], c.kwargs["enqueue_after_commit"]) for c in locks],
            [(ADDRESS, self.user, True)],
        )
        self.assertEqual(self.jobs(enqueue, "unlock_mailbox_now"), [])
        enqueue, _, _ = self.played(False, lambda: self.set_enabled(1))
        unlocks = self.jobs(enqueue, "unlock_mailbox_now")
        self.assertEqual(
            [(c.kwargs["address"], c.kwargs["user"], c.kwargs["enqueue_after_commit"]) for c in unlocks],
            [(ADDRESS, self.user, True)],
        )
        self.assertEqual(self.jobs(enqueue, "lock_mailbox_now"), [])
        cloud_call.assert_not_called()

    def test_a_save_that_does_not_change_enabled_does_nothing(self) -> None:
        def rename() -> None:
            doc = frappe.get_doc("User", self.user)
            doc.first_name = "Locked"
            doc.save(ignore_permissions=True)

        enqueue, _, _ = self.played(False, rename)
        self.assertEqual(
            self.jobs(enqueue, "lock_mailbox_now") + self.jobs(enqueue, "unlock_mailbox_now"), []
        )

    def test_with_suite_cloud_upstream_s_way_is_left_as_it_is(self) -> None:
        enqueue, _, _ = self.played(True, lambda: self.set_enabled(0))
        self.assertEqual(self.jobs(enqueue, "lock_mailbox_now"), [])


class TestJobs(UserCase):
    """The two jobs look at the user again when they run, and what could not be done is logged with the address."""

    def lock_now(self, lock_account: MagicMock, user: str | None = None) -> list[tuple[str, str]]:
        with (
            patch.object(neoffice_stalwart, "lock_account", lock_account),
            patch.object(events.frappe, "log_error") as log,
        ):
            events.lock_mailbox_now(ADDRESS, user)
        return [(c.args[0], c.args[1]) for c in log.call_args_list]

    def test_a_lock_logs_nothing(self) -> None:
        lock_account = MagicMock(return_value=True)
        self.assertEqual(self.lock_now(lock_account), [])
        lock_account.assert_called_once_with(ADDRESS)

    def test_a_failure_and_a_missing_account_name_the_address(self) -> None:
        failed = self.lock_now(MagicMock(side_effect=RuntimeError("unreachable")))
        self.assertEqual(failed[0][0], "Failed to lock the mail account of a user")
        self.assertIn(f"address={ADDRESS}", failed[0][1])
        missing = self.lock_now(MagicMock(return_value=False))
        self.assertEqual(missing, [("Mail account of a user not found", f"address={ADDRESS}")])

    def test_a_user_enabled_again_before_the_lock_ran_is_left_alone(self) -> None:
        lock_account = MagicMock(return_value=True)
        self.lock_now(lock_account, self.user)
        lock_account.assert_not_called()
        frappe.db.set_value("User", self.user, "enabled", 0)
        self.lock_now(lock_account, self.user)
        lock_account.assert_called_once_with(ADDRESS)

    def unlock_now(self, user: str) -> tuple[MagicMock, MagicMock]:
        create, clear = MagicMock(return_value="new-app-password"), MagicMock()
        # Saving the settings signs in to the JMAP server with the new password, as it must on a site: here the
        # password is a made-up one, and the server is never reached.
        settings = "suite.mail.doctype.user_settings.user_settings.UserSettings"
        with (
            patch.object(neoffice_stalwart, "create_app_password", create),
            patch("suite.mail.jmap.clear_jmap_session", clear),
            patch(f"{settings}.validate_jmap_settings"),
            patch(f"{settings}.on_update"),
            patch.object(events.frappe, "log_error"),
        ):
            events.unlock_mailbox_now(ADDRESS, user)
        return create, clear

    def test_enabled_again_the_user_gets_a_new_app_password(self) -> None:
        create, clear = self.unlock_now(self.user)
        create.assert_called_once_with(ADDRESS)
        settings = frappe.get_doc("User Settings", {"user": self.user})
        self.assertEqual(settings.get_password("app_password"), "new-app-password")
        clear.assert_called_once_with(self.user)

    def test_no_new_password_for_a_user_disabled_again_gone_or_now_on_another_mailbox(self) -> None:
        frappe.db.set_value("User", self.user, "enabled", 0)
        self.assertEqual(self.unlock_now(self.user)[0].call_count, 0)
        frappe.db.set_value("User", self.user, "enabled", 1)
        frappe.db.set_value("User Settings", {"user": self.user}, "username", "grace@mail.example.org")
        self.assertEqual(self.unlock_now(self.user)[0].call_count, 0)
        self.assertEqual(self.unlock_now("nobody@example.org")[0].call_count, 0)


class TestOrphanMailboxes(IntegrationTestCase):
    """lock_orphan_mailboxes: the mailboxes no existing user holds, and those of disabled users no enabled user holds
    too, listed, then locked when asked."""

    users: ClassVar[list] = [
        frappe._dict(name="kept@example.org", enabled=1),
        frappe._dict(name="named@example.org", enabled=1),
        frappe._dict(name="off@example.org", enabled=0),
        frappe._dict(name="off-team@example.org", enabled=0),
        frappe._dict(name="Administrator", enabled=1),
    ]
    links: ClassVar[list] = [
        frappe._dict(user="kept@example.org", account="J1"),
        frappe._dict(user="gone@example.org", account="J2"),
        frappe._dict(user="off@example.org", account="J8"),
    ]
    accounts: ClassVar[list] = [
        frappe._dict(name="J1", _name="kept@mail.example.org"),
        frappe._dict(name="J2", _name="Gone@mail.example.org"),
        frappe._dict(name="J3", _name="never@mail.example.org"),
        frappe._dict(name="J4", _name="broken@mail.example.org"),
        frappe._dict(name="J5", _name=""),
        # A stale record of a mailbox a user still holds under another id: never an orphan.
        frappe._dict(name="J6", _name="kept@mail.example.org"),
        # One no link holds, but a user's settings name it: never an orphan either.
        frappe._dict(name="J7", _name="named@mail.example.org"),
        frappe._dict(name="J8", _name="off@mail.example.org"),
    ]
    settings: ClassVar[list] = [
        frappe._dict(user="named@example.org", username="Named@mail.example.org"),
        frappe._dict(user="kept@example.org", username="kept@mail.example.org"),
        frappe._dict(user="off@example.org", username="off@mail.example.org"),
        # A disabled user on a mailbox an enabled user holds too: it stays open.
        frappe._dict(user="off-team@example.org", username="kept@mail.example.org"),
    ]
    real_get_all = staticmethod(frappe.get_all)

    def get_all(self, doctype: str, *args, **kwargs):
        # The lists the function reads are played; anything else (a role lookup) is the site's own.
        played = {
            "User": self.users,
            "User Account": self.links,
            "JMAP Account": self.accounts,
            "User Settings": self.settings,
        }
        return played[doctype] if doctype in played else self.real_get_all(doctype, *args, **kwargs)

    def run_it(self, lock: int, lock_account: MagicMock, configured: bool = True) -> dict:
        frappe.set_user("Administrator")
        with (
            patch.object(events.frappe, "get_all", side_effect=self.get_all),
            patch.object(events, "is_stalwart_configured", return_value=configured),
            patch.object(neoffice_stalwart, "lock_account", lock_account),
            patch.object(events.frappe, "log_error"),
        ):
            return events.lock_orphan_mailboxes(lock=lock)

    def test_they_are_listed_and_nothing_is_locked_unless_asked(self) -> None:
        lock_account = MagicMock()
        result = self.run_it(0, lock_account)
        self.assertEqual(
            result["orphans"], ["broken@mail.example.org", "gone@mail.example.org", "never@mail.example.org"]
        )
        self.assertEqual(result["disabled"], ["off@mail.example.org"])
        lock_account.assert_not_called()

    def test_asked_each_is_locked_or_said_missing_or_failed(self) -> None:
        def lock_account(address: str) -> bool:
            if address.startswith("broken"):
                raise RuntimeError("unreachable")
            return address.startswith(("gone", "off"))

        result = self.run_it(1, MagicMock(side_effect=lock_account))
        self.assertEqual(
            (result["locked"], result["not_found"], result["failed"]),
            (
                ["gone@mail.example.org", "off@mail.example.org"],
                ["never@mail.example.org"],
                ["broken@mail.example.org"],
            ),
        )

    def test_without_a_mail_server_it_says_so_and_locks_nothing(self) -> None:
        lock_account = MagicMock()
        result = self.run_it(1, lock_account, configured=False)
        self.assertFalse(result["configured"])
        lock_account.assert_not_called()

    def test_only_a_system_manager_may_ask(self) -> None:
        frappe.set_user("Guest")
        try:
            with self.assertRaises(frappe.PermissionError):
                events.lock_orphan_mailboxes()
        finally:
            frappe.set_user("Administrator")

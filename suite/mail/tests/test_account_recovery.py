# //// Neoffice — added file (no upstream equivalent): who may set a recovery address, who a reset link reaches,
# //// and what an admin of the mail dashboard may act on (neoffice-maintenance#2296).
"""The recovery address, the guest « forgot password » form, the reset key, and the admin's reach.

Each refusal sits next to the path a real person takes: a person sets their own backup address, a person with an
account gets a reset link built on the site's address, a fresh key still changes the mailbox password.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.tests.roles import as_role
from frappe.utils import add_days, now_datetime, today

from suite.mail import events
from suite.mail.api import account

STRONG = "Str0ng-recovery-pass-2296!"


def make_user(prefix: str, *roles: str) -> str:  # role-check: ok scenery: the accounts a test acts as
    frappe.set_user("Administrator")
    email = f"{prefix}-{frappe.generate_hash(length=6)}@example.test"
    # a desk role would provision a real mailbox on the clone's mail server: never from a test
    with patch("suite.mail.events._should_provision_mail", return_value=False):
        frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": prefix.title(),
                "send_welcome_email": 0,
                "roles": [{"role": role} for role in ("Suite User", *roles)],
            }
        ).insert(ignore_permissions=True)
    return email


def settings_of(user: str) -> str | None:
    return frappe.db.get_value("User Settings", {"user": user}, "name")


def drop_settings_of(user: str) -> None:  # role-check: ok scenery: an account that never opened the suite
    if name := settings_of(user):
        frappe.delete_doc("User Settings", name, ignore_permissions=True, force=True)


def keep_single(test: IntegrationTestCase, doctype: str, field: str, value) -> None:
    """Set a value of a Single for one test and put the site's own back afterwards (other modules commit)."""
    before = frappe.db.get_single_value(doctype, field)
    frappe.db.set_single_value(doctype, field, value)
    test.addCleanup(frappe.db.set_single_value, doctype, field, before)


class TestMailAccountRecovery(IntegrationTestCase):
    def setUp(self):
        frappe.local.request = None  # these calls are the functions, not request traffic (no rate limit)
        frappe.local.login_manager = MagicMock()
        frappe.local.response = frappe._dict()
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    # --- finding 2: a person makes, moves and points only their own recovery row ---------------------------

    def test_a_portal_user_cannot_make_the_settings_of_another_account(self):
        victim = make_user("recovery-victim")
        drop_settings_of(victim)
        attacker = make_user("recovery-portal", "Customer")
        with as_role(attacker), self.assertRaises(frappe.PermissionError):
            frappe.get_doc(
                {"doctype": "User Settings", "user": victim, "backup_email": "seed@elsewhere.example"}
            ).insert()
        self.assertIsNone(settings_of(victim))

    def test_a_suite_admin_cannot_point_another_accounts_recovery_elsewhere(self):
        victim = make_user("recovery-victim")
        admin = make_user("recovery-admin", "Suite Admin")
        with as_role(admin):
            doc = frappe.get_doc("User Settings", settings_of(victim))
            doc.backup_email = "seed@elsewhere.example"
            with self.assertRaises(frappe.PermissionError):
                doc.save()
        self.assertFalse(frappe.db.get_value("User Settings", settings_of(victim), "backup_email"))

    def test_a_person_sets_their_own_recovery_address(self):
        person = make_user("recovery-self", "Customer")
        with as_role(person):
            frappe.client.set_value("User Settings", settings_of(person), "backup_email", "me@backup.example")
        self.assertEqual(
            frappe.db.get_value("User Settings", settings_of(person), "backup_email"), "me@backup.example"
        )

        drop_settings_of(person)
        with as_role(person):
            frappe.get_doc(
                {"doctype": "User Settings", "user": person, "backup_email": "me@backup.example"}
            ).insert()
        self.assertTrue(settings_of(person))

    # --- findings 40 and 19: who the guest form resets, and where the link points ---------------------------

    def test_administrator_disabled_and_unknown_accounts_are_not_reset_and_not_told_apart(self):
        disabled = make_user("recovery-disabled")
        frappe.db.set_value("User", disabled, "enabled", 0)
        key_before = frappe.db.get_value("User", "Administrator", "reset_password_key")
        frappe.set_user("Guest")
        with patch.object(account.suite_email, "send") as send:
            for typed in ("Administrator", "administrator", disabled, "nobody-2296@example.test"):
                self.assertEqual(account.send_reset_password_link(user=typed), typed)
        send.assert_not_called()
        self.assertEqual(frappe.db.get_value("User", "Administrator", "reset_password_key"), key_before)
        self.assertFalse(frappe.db.get_value("User", disabled, "reset_password_key"))

    def test_the_reset_link_is_built_on_the_sites_address_not_on_the_request_host(self):
        person = make_user("recovery-reset")
        frappe.db.set_value("User Settings", settings_of(person), "backup_email", "back.up@backup.example")
        frappe.set_user("Guest")
        with (
            patch("frappe.utils.data.get_host_name_from_request", return_value="https://elsewhere.example"),
            patch.dict(frappe.local.conf, {"host_name": None, "hostname": None}),
            patch.object(account.suite_email, "send") as send,
        ):
            # what the site calls itself with no host_name configured: its own name, never the request's Host
            site_address = frappe.utils.get_url(allow_header_override=False)
            answer = account.send_reset_password_link(user=person)
        self.assertEqual(answer, "b******@backup.example")
        self.assertEqual(send.call_args.args[1], "back.up@backup.example")
        link = send.call_args.args[2]["link"]
        self.assertTrue(link.startswith(site_address + "/mail/reset-password/"), link)
        self.assertNotIn("elsewhere.example", link)

    # --- finding 24: an expired key no longer changes the mailbox password ----------------------------------

    def _reset_key_for(self, user: str, issued_at) -> str:
        key = account.set_reset_password_key(user)
        frappe.db.set_value("User", user, "last_reset_password_key_generated_on", issued_at)
        return key

    def test_an_expired_key_does_not_change_the_mailbox_password_and_a_fresh_one_does(self):
        person = make_user("recovery-key")
        keep_single(self, "System Settings", "reset_password_link_expiry_duration", 1200)
        with (
            patch("suite.mail.events.is_suite_cloud_configured", return_value=True),
            patch("suite.mail.events.is_jmap_configured", return_value=True),
            patch("suite.mail.events.update_mail_password") as mail_password,
        ):
            stale = self._reset_key_for(person, add_days(now_datetime(), -2))
            frappe.set_user("Guest")
            events.update_password(new_password=STRONG, key=stale)
            mail_password.assert_not_called()

            frappe.set_user("Administrator")
            fresh = self._reset_key_for(person, now_datetime())
            frappe.set_user("Guest")
            events.update_password(new_password=STRONG, key=fresh)
            mail_password.assert_called_once_with(person, new_password=STRONG)

    # --- finding 41 and the filters: what the guest signup endpoints answer ---------------------------------

    def test_the_address_check_is_closed_while_signup_is_off(self):
        person = make_user("recovery-known")
        keep_single(self, "Mail Settings", "allow_signup", 0)
        frappe.set_user("Guest")
        for address in (person, "nobody-2296@example.test"):
            with self.assertRaisesRegex(frappe.ValidationError, "Signup is disabled"):
                account.validate_email_assigned(email=address)

        frappe.db.set_single_value("Mail Settings", "allow_signup", 1)
        self.assertIsNone(account.validate_email_assigned(email="nobody-2296@example.test"))
        with self.assertRaisesRegex(frappe.ValidationError, "already taken"):
            account.validate_email_assigned(email=person)

    def test_a_filter_is_refused_as_a_request_key(self):
        # live traffic only reports a JSON object sent for a `str` of this module (it defers its annotations), where
        # tests refuse it on their own: play the live request, where the endpoint's own check is the only refusal
        self.enterContext(
            patch("frappe.utils.typing_validations._enforce_deferred_annotations", return_value=False)
        )
        frappe.set_user("Guest")
        any_request = [
            "like",
            "no-such-key-2296%",
        ]  # an operator and its value: a filter, matching nothing here
        with self.assertRaisesRegex(frappe.ValidationError, "Invalid request"):
            account.get_account_request(request_key=any_request)
        with self.assertRaisesRegex(frappe.ValidationError, "Invalid request"):
            account.create_account(request_key=any_request, first_name="X", last_name="Y", password=STRONG)
        with self.assertRaisesRegex(frappe.ValidationError, "Invalid request"):
            account.send_reset_password_link(user=["like", "nobody-2296%"])

    # --- finding 22: an admin acts only on a member whose roles it holds ------------------------------------

    def test_a_suite_admin_acts_only_on_members_whose_roles_it_holds(self):
        from suite.mail.api.admin import check_member_target

        admin = make_user("recovery-admin", "Suite Admin")
        plain = make_user("recovery-member")
        accountant = make_user("recovery-accountant", "Accounts User")
        for member in (plain, accountant):
            frappe.db.set_value("User Settings", settings_of(member), "username", member)

        with as_role(admin):
            self.assertEqual(check_member_target(plain), plain)
            with self.assertRaises(frappe.PermissionError):
                check_member_target(accountant)

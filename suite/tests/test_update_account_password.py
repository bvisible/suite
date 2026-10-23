# //// Neoffice — added file (no upstream equivalent): the mailbox follows the User's new password
# //// although frappe 15.124.0 empties User.__new_password before this app's on_update hook runs.
"""The mail account takes the password a User is saved with.

Frappe 15.124.0 empties the private ``User.__new_password`` at the end of ``User.on_update``; this app's
``on_update`` hook runs after that and read ``None``: the password of the mailbox never changed, with no error.
``validate`` keeps the value in the document's flags first (``remember_new_password``)."""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import frappe
from frappe.tests import IntegrationTestCase

from suite.mail import events


def new_user(enabled: int = 1):
    user = frappe.new_doc("User")
    user.email = f"update-account-password-{uuid4().hex[:8]}@example.com"
    user.first_name = "Update Account Password Test"
    user.enabled = enabled
    return user


class TestUpdateAccountPassword(IntegrationTestCase):
    def update(self, user, **cloud):
        configured = {"is_suite_cloud_configured": True, "is_jmap_configured": True} | cloud
        with (
            patch.object(
                events, "is_suite_cloud_configured", return_value=configured["is_suite_cloud_configured"]
            ),
            patch.object(events, "is_jmap_configured", return_value=configured["is_jmap_configured"]),
            patch.object(events, "update_mail_password") as update_mail_password,
            patch.object(events, "execute_with_logging", side_effect=lambda fn, **kw: fn()),
        ):
            events.update_account_password(user)
        return update_mail_password

    def test_the_mailbox_takes_the_password_frappe_emptied_after_validate(self):
        user = new_user()
        user._User__new_password = "Another-Password-1!"
        events.remember_new_password(user)  # validate, with the value still there
        user._User__new_password = None  # what User.on_update does from frappe 15.124.0 on
        user.flags.in_insert = False

        update_mail_password = self.update(user)

        update_mail_password.assert_called_once_with(user.name, new_password="Another-Password-1!")

    def test_the_attribute_still_serves_when_validate_did_not_run(self):
        user = new_user()
        user._User__new_password = "Another-Password-2!"
        user.flags.in_insert = False

        update_mail_password = self.update(user)

        update_mail_password.assert_called_once_with(user.name, new_password="Another-Password-2!")

    def test_no_new_password_changes_nothing(self):
        user = new_user()
        events.remember_new_password(user)
        user.flags.in_insert = False

        self.assertFalse(self.update(user).called)

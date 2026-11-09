# //// Neoffice — added file (no upstream equivalent): who may read the mail server's directory through the
# //// calendar's share dialog (neoffice-maintenance#1193). The mail server is replaced by a stand-in client, so no
# //// mail server is needed and none is touched; users are made with the mailbox provisioning switched off.
from __future__ import annotations

from unittest import mock

import frappe
from frappe.tests import IntegrationTestCase

DESK = "shareable-principals-desk@example.com"
PORTAL = "shareable-principals-portal@example.com"
ACCOUNT = "shareable-principals-account"


def _user(email: str, user_type: str) -> str:
    if not frappe.db.exists("User", email):
        with mock.patch("suite.mail.events._should_provision_mail", return_value=False):
            frappe.get_doc(
                {
                    "doctype": "User",
                    "email": email,
                    "first_name": "Shareable principals",
                    "send_welcome_email": 0,
                    "user_type": user_type,
                    "roles": [{"role": "System Manager"}] if user_type == "System User" else [],
                }
            ).insert(ignore_permissions=True)
    frappe.db.set_value("User", email, "user_type", user_type)
    frappe.clear_document_cache("User", email)
    return email


def _principal(principal_id: str, name: str, email: str) -> mock.Mock:
    principal = mock.Mock()
    principal.to_wire.return_value = {"id": principal_id, "name": name, "email": email}
    return principal


def _client() -> mock.MagicMock:
    """A mail server client whose directory holds three people, the account's own included."""

    client = mock.MagicMock()
    client.capabilities.attrs = {"principals": True}
    batch = client.batch.return_value.__enter__.return_value
    batch.principals.principal.query.return_value.result.ids = ["1", "2", ACCOUNT]
    batch.principals.principal.get.return_value.result.items = [
        _principal("1", "Colleague One", "one@example.test"),
        _principal("2", "Colleague Two", "two@example.test"),
        _principal(ACCOUNT, "Self", "self@example.test"),
    ]
    return client


class TestShareablePrincipals(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _user(DESK, "System User")
        _user(PORTAL, "Website User")

    def setUp(self):
        self.client = _client()
        patcher = mock.patch(
            "suite.calendar.doctype.calendar.calendar.get_account_client", return_value=self.client
        )
        self.get_account_client = patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_a_portal_account_gets_no_directory_and_the_mail_server_is_not_asked(self):
        from suite.calendar.doctype.calendar.calendar import get_shareable_principals

        frappe.set_user(PORTAL)

        self.assertEqual(get_shareable_principals(ACCOUNT), [])
        self.get_account_client.assert_not_called()

    def test_a_desk_account_gets_its_colleagues_and_not_itself(self):
        from suite.calendar.doctype.calendar.calendar import get_shareable_principals

        frappe.set_user(DESK)

        self.assertEqual(
            get_shareable_principals(ACCOUNT),
            [
                {"id": "1", "name": "Colleague One", "email": "one@example.test"},
                {"id": "2", "name": "Colleague Two", "email": "two@example.test"},
            ],
        )

    def test_the_method_is_not_open_to_guests(self):
        from suite.calendar.doctype.calendar.calendar import get_shareable_principals

        self.assertNotIn(get_shareable_principals, frappe.guest_methods)

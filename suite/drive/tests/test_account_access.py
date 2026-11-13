# //// Neoffice — added file (no upstream equivalent): who an invitation, a sign-up and its code let in
# //// (neoffice-maintenance#2296).
"""A Drive invitation, the sign-up it leads to and the e-mail code of a self sign-up.

Each refusal sits next to the path a real person takes: an invited person with an account signs in with their own
credentials and then accepts, a new invitee signs up from the link, a visitor who typed the right code goes on.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import frappe
from frappe.tests import IntegrationTestCase
from frappe.tests.roles import as_role
from frappe.utils import add_to_date, now_datetime

from suite.drive.api import product
from suite.drive.doctype.drive_user_invitation.drive_user_invitation import get_invite_token
from suite.tests.utils import ensure_user

EXISTING = "drive-invite-existing@example.test"
OTHER = "drive-invite-other@example.test"


# Live traffic only reports a JSON object sent for a `str` of a module that defers its annotations; tests refuse it
# on their own. These tests play the live request, where the endpoint's own check is the only refusal.
def live_traffic():
    return patch("frappe.utils.typing_validations._enforce_deferred_annotations", return_value=False)


def make_invitation(email: str, status: str = "Pending") -> str:  # role-check: ok scenery an admin prepares
    frappe.set_user("Administrator")
    frappe.db.delete("Drive User Invitation", {"email": email})
    doc = frappe.new_doc("Drive User Invitation")
    doc.email = email
    doc.status = status
    with patch.object(type(doc), "invite_via_email"):
        doc.insert(ignore_permissions=True)
    return doc.name


def make_account_request(email: str, otp: str = "123456") -> str:  # role-check: ok scenery of a sign-up
    frappe.set_user("Administrator")
    doc = frappe.get_doc({"doctype": "Account Request", "email": email, "signed_up": 0}).insert(
        ignore_permissions=True
    )
    doc.db_set({"otp": otp, "otp_generated_at": now_datetime()})
    return doc.name


class TestDriveAccountAccess(IntegrationTestCase):
    def setUp(self):
        # the rate limits read the request; these calls are the function, not request traffic
        frappe.local.request = None
        frappe.local.login_manager = MagicMock()
        frappe.local.response = frappe._dict()
        frappe.set_user("Administrator")
        ensure_user(EXISTING)
        ensure_user(OTHER)

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    # --- finding 1: the key is a name, never a filter -------------------------------------------------------

    def test_a_filter_as_invitation_key_is_refused(self):
        name = make_invitation(EXISTING)
        frappe.set_user("Guest")
        with live_traffic(), self.assertRaises(frappe.ValidationError):
            # a filter that would pick this invitation without knowing its key
            product.accept_invite(key={"email": EXISTING, "status": ["in", ["Pending", "Automatic"]]})
        frappe.local.login_manager.login_as.assert_not_called()
        self.assertEqual(frappe.db.get_value("Drive User Invitation", name, "status"), "Pending")

    def test_a_filter_as_account_request_is_refused(self):
        email = f"drive-signup-filter-{frappe.generate_hash(length=6)}@example.test"
        request = make_account_request(email)
        frappe.db.set_value("Account Request", request, "login_count", 1)  # its owner verified the address
        frappe.set_user("Guest")
        with live_traffic(), self.assertRaises(frappe.ValidationError):
            product.signup(
                account_request={"email": email, "signed_up": 0},
                first_name="X",
                password="Str0ng-pass-for-test!",
            )
        self.assertFalse(frappe.db.exists("User", email))

    # --- finding 17: an existing account signs in with its own credentials ----------------------------------

    def test_a_visitor_holding_the_key_of_an_existing_account_is_sent_to_sign_in(self):
        name = make_invitation(EXISTING)
        frappe.set_user("Guest")
        location = product.accept_invite(key=name)
        frappe.local.login_manager.login_as.assert_not_called()
        self.assertEqual(frappe.session.user, "Guest")
        self.assertTrue(location.startswith("/login?"))
        back = parse_qs(urlparse(location).query)["redirect-to"][0]
        self.assertEqual(back, f"/api/method/suite.drive.api.product.accept_invite?key={name}")
        self.assertEqual(frappe.db.get_value("Drive User Invitation", name, "status"), "Pending")

    def test_the_invited_person_signed_in_accepts(self):
        name = make_invitation(EXISTING)
        with as_role(EXISTING):
            self.assertEqual(product.accept_invite(key=name), "/drive/")
        self.assertEqual(frappe.db.get_value("Drive User Invitation", name, "status"), "Accepted")

    def test_another_signed_in_account_cannot_accept_it(self):
        name = make_invitation(EXISTING)
        with as_role(OTHER), self.assertRaises(frappe.PermissionError):
            product.accept_invite(key=name)
        self.assertEqual(frappe.db.get_value("Drive User Invitation", name, "status"), "Pending")

    def test_only_the_invited_person_withdraws_an_invitation(self):
        name = make_invitation(EXISTING)
        with as_role(OTHER), self.assertRaises(frappe.PermissionError):
            product.reject_invite(key=name)
        self.assertEqual(frappe.db.get_value("Drive User Invitation", name, "status"), "Pending")
        with as_role(EXISTING):
            product.reject_invite(key=name)
        self.assertEqual(frappe.db.get_value("Drive User Invitation", name, "status"), "Expired")

    # --- a new invitee signs up from the link; finding 45: the redirect stays on the site --------------------

    def test_a_new_invitee_signs_up_once_and_lands_on_a_path_of_the_site(self):
        email = f"drive-invite-new-{frappe.generate_hash(length=6)}@example.test"
        name = make_invitation(email, status="Automatic")
        frappe.set_user("Guest")
        # the token of the e-mailed link (GHSA-xqwr-x9c5-vvf8, test_drive_advisories)
        token = get_invite_token(name)
        product.accept_invite(key=name, redirect="https://elsewhere.example/phish", token=token)
        query = parse_qs(urlparse(frappe.local.response["location"]).query)
        self.assertNotIn("redirect-to", query)
        self.assertEqual(query["e"], [email])

        product.accept_invite(key=name, redirect="/drive/d/some-folder/", token=token)
        query = parse_qs(urlparse(frappe.local.response["location"]).query)
        self.assertEqual(query["redirect-to"], ["/drive/d/some-folder/"])
        request = query["r"][0]

        product.signup(account_request=request, first_name="New", password="Str0ng-pass-for-test!")
        self.assertTrue(frappe.db.exists("User", email))
        self.assertEqual(frappe.db.get_value("Drive User Invitation", name, "status"), "Accepted")
        with self.assertRaises(frappe.PermissionError):
            product.signup(account_request=request, first_name="Again", password="An0ther-pass-for-test!")

    def test_local_path_keeps_only_paths_of_the_site(self):
        for value in (
            "https://elsewhere.example/",
            "//elsewhere.example/",
            "/\\elsewhere.example",
            "javascript:x",
        ):
            self.assertIsNone(product.local_path(value), value)
        self.assertEqual(product.local_path("/drive/d/abc/"), "/drive/d/abc/")

    # --- finding 26: the sign-up code expires, is spent, and few guesses burn it ----------------------------

    def test_the_right_code_verifies_once(self):
        request = make_account_request("drive-otp-right@example.test")
        frappe.set_user("Guest")
        product.verify_otp(account_request=request, otp="123456")
        self.assertEqual(frappe.db.get_value("Account Request", request, "login_count"), 1)
        with self.assertRaises(frappe.ValidationError):
            product.verify_otp(account_request=request, otp="123456")

    def test_an_old_code_is_refused(self):
        request = make_account_request("drive-otp-old@example.test")
        frappe.db.set_value(
            "Account Request", request, "otp_generated_at", add_to_date(now_datetime(), minutes=-11)
        )
        frappe.set_user("Guest")
        with self.assertRaises(frappe.ValidationError):
            product.verify_otp(account_request=request, otp="123456")
        self.assertFalse(frappe.db.get_value("Account Request", request, "login_count"))

    def test_wrong_guesses_burn_the_code(self):
        request = make_account_request("drive-otp-guess@example.test")
        frappe.set_user("Guest")
        for guess in range(product.SIGNUP_OTP_MAX_FAILURES):
            with self.assertRaises(frappe.ValidationError):
                product.verify_otp(account_request=request, otp=f"{900000 + guess}")
        with self.assertRaises(frappe.ValidationError):
            product.verify_otp(account_request=request, otp="123456")
        self.assertFalse(frappe.db.get_value("Account Request", request, "login_count"))

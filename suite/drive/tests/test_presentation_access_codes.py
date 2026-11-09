# //// Neoffice — added file (no upstream equivalent): a code given with a shared presentation's link to one person
# //// (suite/drive/presentation/api.py new_access_code, enter_with_code; Jérémy, 09.11: « pouvoir lui donner un code »):
# //// the team makes it, the person enters with it as she types it, and a wrong, expired or other link's code opens
# //// nothing; a portal account cannot make one.
from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

import frappe
from frappe.tests.roles import as_role
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from suite.drive.presentation import api, rules
from suite.drive.tests.test_presentation_questions import _file, _user

PREFIX = "np-test-ac"
STAFF = "np-test-ac-staff@example.com"
PORTAL = "np-test-ac-portal@example.com"


class TestAccessCodeRules(TestCase):
    def test_a_code_has_eight_signs_that_cannot_be_mistaken(self):
        code = rules.new_access_code()
        self.assertRegex(code, r"^[2-9A-HJKMNP-Z]{4}-[2-9A-HJKMNP-Z]{4}$")
        self.assertEqual(rules.normalize_access_code(code.lower().replace("-", " ")), code.replace("-", ""))

    def test_what_cannot_be_a_code_is_nothing(self):
        for typed in ("", "ABCD", "ABCD-EFGH-J", "ABCD-EFG0", "ABCD-EFGI", None):
            self.assertEqual(rules.normalize_access_code(typed), "", typed)


class TestAccessCodes(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        home = frappe.db.get_value("File", {"is_home_folder": 1}) or "Home"
        cls.folder = _file(f"{PREFIX}-deck", folder=home, is_folder=1)
        cls.entry = _file(
            "index.html", folder=cls.folder.name, content="<html><body><p>Slide</p></body></html>"
        )
        _user(STAFF, "System User", ("Suite User",))
        _user(PORTAL, "Website User")

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        links = frappe.get_all("Presentation Link", filters={"title": ["like", f"{PREFIX}%"]}, pluck="name")
        for doctype in ("Presentation Access Code", "Presentation Visit", "Presentation Viewer"):
            for name in frappe.get_all(doctype, filters={"link": ["in", links or [""]]}, pluck="name"):
                frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
        for name in links:
            frappe.delete_doc("Presentation Link", name, force=True, ignore_permissions=True)
        for file in (cls.entry, cls.folder):
            frappe.delete_doc("File", file.name, force=True, ignore_permissions=True)
        for email in (STAFF, PORTAL):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.commit()
        super().tearDownClass()

    def setUp(self):
        frappe.set_user("Administrator")
        self.link = self.new_link()
        self.sent = []
        patcher = patch.object(frappe, "sendmail", side_effect=lambda **kw: self.sent.append(kw))
        patcher.start()
        self.addCleanup(patcher.stop)

    def new_link(self):
        return frappe.get_doc(
            {
                "doctype": "Presentation Link",
                "title": f"{PREFIX} link",
                "presentation": self.folder.name,
                "allowed_domains": "firm-example.ch",
            }
        ).insert()

    def give(self, email="Laurent@Firm-Example.ch", first_name="Laurent", link=None) -> dict:
        with as_role(STAFF):
            return api.new_access_code((link or self.link).name, email, first_name)

    def test_the_person_enters_with_her_code_as_she_types_it_and_no_mail_is_sent(self):
        given = self.give()
        self.assertEqual(given["email"], "laurent@firm-example.ch")
        self.assertTrue(given["url"].endswith(f"/p/{self.link.token}#code"))
        typed = given["code"].lower().replace("-", " ")
        with as_role("Guest"):
            result = api.enter_with_code(self.link.token, typed, "browser-1")
            again = api.enter_with_code(self.link.token, given["code"], "browser-2")
        self.assertTrue(result["ok"] and again["ok"])
        self.assertEqual(result["email"], "laurent@firm-example.ch")
        self.assertTrue(result["content"].startswith(f"/p/{self.link.token}/c/"))
        viewer = frappe.get_doc(
            "Presentation Viewer", {"link": self.link.name, "email": "laurent@firm-example.ch"}
        )
        self.assertEqual((viewer.first_name, viewer.entered_via), ("Laurent", "Link Sent"))
        self.assertEqual(self.sent, [])  # no code to wait for: the person has hers
        # only the code's fingerprint is kept
        row = frappe.get_doc("Presentation Access Code", {"link": self.link.name})
        self.assertNotIn(given["code"].replace("-", ""), row.code_hash)
        self.assertEqual(row.uses, 2)
        link = frappe.get_doc("Presentation Link", self.link.name)
        self.assertIn("laurent@firm-example.ch", link.recipients)

    def test_a_wrong_an_expired_or_another_links_code_opens_nothing(self):
        given = self.give()
        other = self.new_link()
        with as_role("Guest"):
            self.assertEqual(api.enter_with_code(self.link.token, "ABCD-EFGH")["reason"], "wrong_code")
            self.assertEqual(api.enter_with_code(self.link.token, "nonsense")["reason"], "wrong_code")
            self.assertEqual(api.enter_with_code(other.token, given["code"])["reason"], "wrong_code")
        frappe.db.set_value(
            "Presentation Access Code",
            {"link": self.link.name},
            "valid_until",
            add_to_date(now_datetime(), minutes=-1),
        )
        with as_role("Guest"):
            self.assertEqual(api.enter_with_code(self.link.token, given["code"])["reason"], "wrong_code")
        self.assertFalse(frappe.db.exists("Presentation Viewer", {"link": self.link.name}))

    def test_a_code_ends_with_the_link_and_a_withdrawn_link_takes_none(self):
        soon = add_to_date(now_datetime(), days=3)
        frappe.db.set_value("Presentation Link", self.link.name, "expires_on", soon)
        given = self.give()
        self.assertLessEqual(given["valid_until"][:16], str(soon)[:16])
        frappe.db.set_value("Presentation Link", self.link.name, "status", "Withdrawn")
        self.assertRaises(frappe.ValidationError, self.give)

    def test_a_portal_account_cannot_make_a_code(self):
        with as_role(PORTAL):
            self.assertRaises(
                frappe.PermissionError, api.new_access_code, self.link.name, "a@firm-example.ch"
            )
        self.assertFalse(frappe.db.exists("Presentation Access Code", {"link": self.link.name}))

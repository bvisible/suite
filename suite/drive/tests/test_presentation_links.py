# //// Neoffice — added file (no upstream equivalent): a presentation of the Drive shared by a link (suite/drive/presentation/):
# //// who may ask for a code, the code itself, the files a visit may read, the seconds a heartbeat may add, and what a
# //// visitor's page can and cannot reach.
from __future__ import annotations

import json
from unittest import TestCase
from unittest.mock import patch

import frappe
from frappe.tests.roles import as_role
from frappe.tests.utils import FrappeTestCase

from suite.drive.presentation import api, rules

PREFIX = "np-test"


class TestRules(TestCase):
    def test_a_domain_is_read_from_any_way_people_write_it(self):
        self.assertEqual(
            rules.normalize_domains(
                "example.ch\n@Other-Firm.CH, someone@third.com\nnot a domain\nexample.ch"
            ),
            ["example.ch", "other-firm.ch", "third.com"],
        )

    def test_only_real_addresses_are_kept(self):
        self.assertEqual(rules.normalize_emails("A.B@Example.ch\nnope\n a.b@example.ch "), ["a.b@example.ch"])

    def test_a_heartbeat_adds_at_most_thirty_seconds(self):
        merged = rules.merge_beat({}, {}, {"seconds": {"1": 25, "2": 25, "3": 25}, "slide": 3, "total": 37})
        self.assertEqual(merged["added"], 30)
        self.assertEqual(merged["slides"], {"1": 25.0, "2": 5.0})
        self.assertEqual(merged["total"], 37)
        self.assertEqual(merged["furthest"], 3)

    def test_a_heartbeat_ignores_what_is_not_a_slide_or_a_time(self):
        merged = rules.merge_beat(
            {"4": 10}, {}, {"seconds": {"0": 5, "x": 5, "9999": 5, "2": "nan", "3": -4}}
        )
        self.assertEqual(merged["slides"], {"4": 10.0})
        self.assertEqual(merged["added"], 0)

    def test_a_video_keeps_the_furthest_point_reached(self):
        merged = rules.merge_beat(
            {}, {"video/a.mp4": 80}, {"videos": {"video/a.mp4": 40, "video/b.mp4": 140}}
        )
        self.assertEqual(merged["videos"], {"video/a.mp4": 80, "video/b.mp4": 100})

    def test_a_slide_skipped_through_is_not_seen(self):
        self.assertEqual(rules.slides_seen({"1": 1.0, "2": 2.0, "3": 30}), 2)

    def test_the_device_is_told_from_the_browser(self):
        self.assertEqual(rules.device_of("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0) Mobile/15E148"), "Phone")
        self.assertEqual(rules.device_of("Mozilla/5.0 (iPad; CPU OS 18_0)"), "Tablet")
        self.assertEqual(rules.device_of("Mozilla/5.0 (Macintosh; Intel Mac OS X 15_0)"), "Computer")


class TestPresentationLink(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        home = frappe.db.get_value("File", {"is_home_folder": 1}) or "Home"
        cls.folder = _file(f"{PREFIX}-deck", folder=home, is_folder=1)
        cls.entry = _file(
            "index.html", folder=cls.folder.name, content="<html><body><p>Slide</p></body></html>"
        )
        cls.images = _file("img", folder=cls.folder.name, is_folder=1)
        cls.image = _file("cover.png", folder=cls.images.name, content="png")
        cls.outside = _file(f"{PREFIX}-outside.png", folder=home, content="secret")

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for doctype in ("Presentation Visit", "Presentation Viewer", "Presentation Link"):
            for name in frappe.get_all(doctype, filters=_ours(doctype), pluck="name"):
                frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
        for file in (cls.image, cls.images, cls.entry, cls.outside, cls.folder):
            frappe.delete_doc("File", file.name, force=True, ignore_permissions=True)
        frappe.db.commit()
        super().tearDownClass()

    def setUp(self):
        frappe.set_user("Administrator")
        self.link = frappe.get_doc(
            {
                "doctype": "Presentation Link",
                "title": f"{PREFIX} link",
                "presentation": self.folder.name,
                "allowed_domains": "@Firm-Example.ch",
            }
        ).insert()
        self.sent = []
        patcher = patch.object(frappe, "sendmail", side_effect=lambda **kw: self.sent.append(kw))
        patcher.start()
        self.addCleanup(patcher.stop)

    def code_sent(self) -> str:
        body = self.sent[-1]["message"]
        return next(part for part in body.replace(">", "<").split("<") if part.isdigit() and len(part) == 6)

    def enter(self, email="anna@firm-example.ch", first_name=None) -> dict:
        with as_role("Guest"):
            self.assertTrue(api.request_code(self.link.token, email, first_name)["ok"])
            return api.verify_code(self.link.token, email, self.code_sent(), "browser-1")

    def test_the_link_reads_its_domains_and_has_its_address(self):
        self.assertEqual(self.link.allowed_domains, "firm-example.ch")
        self.assertTrue(self.link.url.endswith(f"/p/{self.link.token}"))

    def test_an_address_of_an_accepted_domain_gets_a_code_and_enters(self):
        result = self.enter(first_name="Anna")
        self.assertTrue(result["ok"])
        self.assertTrue(result["content"].startswith(f"/p/{self.link.token}/c/"))
        self.assertTrue(result["content"].endswith("/start"))
        viewer = frappe.get_doc(
            "Presentation Viewer", {"link": self.link.name, "email": "anna@firm-example.ch"}
        )
        self.assertEqual(viewer.first_name, "Anna")
        self.assertEqual(viewer.entered_via, "Copied Link")
        self.assertEqual(frappe.db.get_value("Presentation Link", self.link.name, "status"), "Opened")

    def test_the_first_name_is_not_needed(self):
        self.assertTrue(self.enter()["ok"])

    def test_an_address_outside_the_domains_gets_no_code(self):
        with as_role("Guest"):
            result = api.request_code(self.link.token, "someone@elsewhere.com")
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "not_accepted")
        self.assertEqual(self.sent, [])

    def test_a_wrong_code_does_not_open_and_five_use_the_code_up(self):
        with as_role("Guest"):
            api.request_code(self.link.token, "anna@firm-example.ch")
            right = self.code_sent()
            wrong = "000000" if right != "000000" else "111111"
            for _attempt in range(rules.CODE_ATTEMPTS):
                self.assertFalse(api.verify_code(self.link.token, "anna@firm-example.ch", wrong)["ok"])
            self.assertFalse(api.verify_code(self.link.token, "anna@firm-example.ch", right)["ok"])

    def test_a_withdrawn_link_opens_nothing(self):
        result = self.enter()
        self.link.reload()
        self.link.status = "Withdrawn"
        self.link.save()
        with as_role("Guest"):
            self.assertRaises(
                frappe.PermissionError, api.request_code, self.link.token, "anna@firm-example.ch"
            )
            self.assertFalse(api.track(result["visit"], {"seconds": {"1": 5}})["ok"])
        self.assertIsNone(api.visit_for_content(self.link.token, result["visit"]))

    def test_a_heartbeat_adds_up_on_the_visit_the_person_and_the_link(self):
        visit = self.enter()["visit"]
        with as_role("Guest"):
            api.track(
                visit,
                json.dumps({"seconds": {"1": 12, "2": 3}, "slide": 2, "total": 5, "videos": {"v.mp4": 60}}),
            )
            api.track(visit, {"seconds": {"2": 9}, "slide": 3, "total": 5})
        viewer = frappe.get_doc(
            "Presentation Viewer", {"link": self.link.name, "email": "anna@firm-example.ch"}
        )
        self.assertEqual(viewer.total_seconds, 24)
        self.assertEqual(viewer.slides_seen, 2)
        self.assertEqual(viewer.furthest_slide, 3)
        self.assertEqual(viewer.video_percent, 60)
        self.assertEqual(frappe.db.get_value("Presentation Link", self.link.name, "total_seconds"), 24)

    def test_a_visit_reads_only_the_files_of_its_presentation(self):
        visit = self.enter()["visit"]
        self.assertIsNotNone(api.visit_for_content(self.link.token, visit))
        folder, entry = rules.entry_file(self.link.presentation)
        self.assertEqual(entry.name, self.entry.name)
        self.assertEqual(rules.resolve(folder, "img/cover.png").name, self.image.name)
        for path in (
            "../" + self.outside.file_name,
            "img/../index.html",
            "/etc/passwd",
            "img//cover.png",
            "",
        ):
            self.assertIsNone(rules.resolve(folder, path), path)
        self.assertIsNone(api.visit_for_content("another-token-0000000", visit))
        self.assertIsNone(api.visit_for_content(self.link.token, "not-a-visit"))

    def test_a_colleague_receives_it_in_their_name_and_enters(self):
        visit = self.enter(first_name="Anna")["visit"]
        with as_role("Guest"):
            self.assertTrue(api.forward(visit, "paul@firm-example.ch", "Paul")["ok"])
        self.assertIn("paul@firm-example.ch", self.sent[-1]["recipients"])
        self.assertIn(f"/p/{self.link.token}", self.sent[-1]["message"])
        result = self.enter("paul@firm-example.ch")
        self.assertTrue(result["ok"])
        paul = frappe.get_doc(
            "Presentation Viewer", {"link": self.link.name, "email": "paul@firm-example.ch"}
        )
        self.assertEqual(paul.entered_via, "Forwarded")
        self.assertEqual(paul.first_name, "Paul")

    def test_a_forward_outside_the_domains_needs_the_link_to_allow_it(self):
        visit = self.enter()["visit"]
        with as_role("Guest"):
            self.assertFalse(api.forward(visit, "out@elsewhere.com")["ok"])
        self.link.reload()
        self.link.forward_outside = 1
        self.link.save()
        with as_role("Guest"):
            self.assertTrue(api.forward(visit, "out@elsewhere.com")["ok"])

    def test_a_browser_that_entered_comes_back_without_a_code(self):
        result = self.enter()
        with as_role("Guest"):
            again = api.resume(self.link.token, "anna@firm-example.ch", result["remember"], "browser-1")
            self.assertTrue(again["ok"])
            self.assertFalse(
                api.resume(self.link.token, "anna@firm-example.ch", "a-guess", "browser-1")["ok"]
            )

    def test_a_visitor_cannot_read_the_statistics(self):
        self.enter()
        with as_role("Guest"):
            self.assertRaises(frappe.PermissionError, api.get_stats, self.link.name)
            self.assertRaises(frappe.PermissionError, api.send_link, self.link.name, "x@firm-example.ch")

    def test_a_portal_account_reads_no_link_person_or_visit(self):
        self.enter()
        email = f"{PREFIX}-portal@example.com"
        if not frappe.db.exists("User", email):
            frappe.get_doc(
                {
                    "doctype": "User",
                    "email": email,
                    "first_name": "Portal",
                    "user_type": "Website User",
                    "send_welcome_email": 0,
                }
            ).insert(ignore_permissions=True)
            frappe.get_doc("User", email).add_roles("Suite User")
        with as_role(email):
            for doctype in ("Presentation Link", "Presentation Viewer", "Presentation Visit"):
                self.assertEqual(frappe.get_list(doctype, limit=5), [], doctype)
            self.assertFalse(frappe.has_permission("Presentation Link", "read", self.link.name))
            self.assertRaises(frappe.PermissionError, api.get_stats, self.link.name)
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)

    def test_the_statistics_say_who_saw_what(self):
        visit = self.enter(first_name="Anna")["visit"]
        with as_role("Guest"):
            api.track(visit, {"seconds": {"1": 10, "2": 20}, "slide": 2, "total": 2})
        stats = api.get_stats(self.link.name)
        self.assertEqual(stats["slide_count"], 2)
        self.assertEqual(stats["per_slide"], {"1": 10.0, "2": 20.0})
        self.assertEqual([v.email for v in stats["viewers"]], ["anna@firm-example.ch"])
        self.assertEqual(stats["events"][0]["kind"], "visit")


def _file(name: str, folder: str, is_folder: int = 0, content: str | None = None):
    doc = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": name,
            "folder": folder,
            "is_folder": is_folder,
            "is_private": 1,
            "content": content if not is_folder else None,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc


def _ours(doctype: str) -> dict:
    if doctype == "Presentation Link":
        return {"title": ["like", f"{PREFIX}%"]}
    links = frappe.get_all("Presentation Link", filters={"title": ["like", f"{PREFIX}%"]}, pluck="name")
    return {"link": ["in", links or [""]]}

# //// Neoffice — added file (no upstream equivalent): the questions asked on a shared presentation
# //// (suite/drive/presentation/questions.py, maintenance#2337): what Nora may read for a link, an answer she is sure
# //// of and one she is not, the person who answers, the answers kept for the next people, and who reads the questions.
from __future__ import annotations

from datetime import timedelta
from unittest import TestCase
from unittest.mock import patch

import frappe
from frappe.tests.roles import as_role
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_datetime

from suite.drive.presentation import api
from suite.drive.presentation import questions as asking

PREFIX = "np-test-q"
STAFF = "np-test-q-staff@example.com"
PORTAL = "np-test-q-portal@example.com"
DECK = """<html><body>
<section class="slide" data-title="Couverture"><h1>Neoffice</h1><p>Le logiciel de votre fiduciaire.</p>
<script>window.secret = 1</script></section>
<section class="slide"><h2>La reprise</h2><p>467 comptes repris sur un seul dossier.</p>
<img src="a.png" alt="écran réel, société fictive"><aside class="notes">Ne pas dire le prix.</aside></section>
</body></html>"""


class TestSlides(TestCase):
    def test_each_slide_has_its_title_its_text_and_its_notes_apart(self):
        slides = asking.extract_slides(DECK)
        self.assertEqual([s["index"] for s in slides], [1, 2])
        self.assertEqual(slides[0]["title"], "Couverture")
        self.assertEqual(slides[1]["title"], "La reprise")
        self.assertIn("467 comptes repris", slides[1]["text"])
        self.assertIn("écran réel, société fictive", slides[1]["text"])
        self.assertNotIn("Ne pas dire le prix", slides[1]["text"])
        self.assertEqual(slides[1]["notes"], "Ne pas dire le prix.")
        self.assertNotIn("window.secret", slides[0]["text"])

    def test_the_parts_of_a_deck_are_named_by_their_first_slide(self):
        html = """<section class="slide" data-title="Couverture"></section>
<section class="slide" data-part="1" data-title="01 Neoservice"></section><section class="slide" data-part="1"></section>
<section class="slide" data-part="2" data-title="02 · WinBiz"></section>"""
        parts = asking.parts_of(asking.extract_slides(html))
        self.assertEqual(
            [(p["label"], p["start"], p["end"]) for p in parts], [("Neoservice", 2, 3), ("WinBiz", 4, 4)]
        )
        self.assertEqual(asking.parts_of(asking.extract_slides(DECK)), [])

    def test_a_reveal_deck_is_read_by_its_top_sections(self):
        html = '<div class="reveal"><div class="slides"><section><h2>Un</h2></section><section><h2>Deux</h2></section></div></div>'
        self.assertEqual([s["title"] for s in asking.extract_slides(html)], ["Un", "Deux"])


class TestQuestions(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        home = frappe.db.get_value("File", {"is_home_folder": 1}) or "Home"
        cls.folder = _file(f"{PREFIX}-deck", folder=home, is_folder=1)
        cls.entry = _file("index.html", folder=cls.folder.name, content=DECK)
        _user(STAFF, "System User", ("Suite User",))
        _user(PORTAL, "Website User")

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for doctype in (
            "Presentation Question",
            "Presentation Visit",
            "Presentation Viewer",
            "Presentation Link",
        ):
            for name in frappe.get_all(doctype, filters=_ours(doctype), pluck="name"):
                frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
        for file in (cls.entry, cls.folder):
            frappe.delete_doc("File", file.name, force=True, ignore_permissions=True)
        for email in (STAFF, PORTAL):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.commit()
        super().tearDownClass()

    def setUp(self):
        frappe.set_user("Administrator")
        self.link = self.new_link()
        self.sent, self.jobs, self.alerts = [], [], []
        patches = (
            # each mail keeps the language it was written in
            patch.object(
                frappe,
                "sendmail",
                side_effect=lambda **kw: self.sent.append({**kw, "lang": frappe.local.lang}),
            ),
            patch.object(frappe, "enqueue", side_effect=lambda *a, **kw: self.jobs.append(kw)),
            patch(
                "frappe.desk.doctype.notification_log.notification_log.enqueue_create_notification",
                side_effect=lambda user, doc: self.alerts.append(user),
            ),
        )
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.visit = self.enter()
        self.alerts.clear()  # the owner is told a new person entered (api._notify_owner): not a question

    def new_link(self, **values):
        return frappe.get_doc(
            {
                "doctype": "Presentation Link",
                "title": f"{PREFIX} link",
                "presentation": self.folder.name,
                "allowed_domains": "firm-example.ch",
                "questions_to": STAFF,
                **values,
            }
        ).insert()

    def enter(self, link=None, email="anna@firm-example.ch") -> str:
        link = link or self.link
        with as_role("Guest"):
            api.request_code(link.token, email, "Anna")
            body = self.sent[-1]["message"]
            code = next(p for p in body.replace(">", "<").split("<") if p.isdigit() and len(p) == 6)
            result = api.verify_code(link.token, email, code, "browser-1")
        self.assertTrue(result["ok"])
        self.assertTrue(result["questions"]["enabled"])
        self.assertEqual(result["questions"]["slides"], ["Couverture", "La reprise"])
        return result["visit"]

    def ask(self, text="Combien de comptes ont été repris ?", slide=2, visit=None) -> str:
        with as_role("Guest"):
            result = api.ask(visit or self.visit, text, slide)
        self.assertTrue(result["ok"], result)
        return result["question"]

    def answered_by(self, fake, name):
        with patch.object(asking, "_answerer", return_value=fake):
            asking.answer_question(name)
        return frappe.get_doc("Presentation Question", name)

    def thread(self, visit=None):
        with as_role("Guest"):
            return api.questions(visit or self.visit)["questions"]

    def test_a_question_is_kept_with_its_slide_and_sent_to_be_answered(self):
        name = self.ask()
        doc = frappe.get_doc("Presentation Question", name)
        self.assertEqual((doc.status, doc.slide, doc.slide_title), ("Asked", 2, "La reprise"))
        self.assertEqual((doc.email, doc.first_name), ("anna@firm-example.ch", "Anna"))
        self.assertEqual(self.jobs[-1]["name"], name)
        self.assertEqual(frappe.db.get_value("Presentation Link", self.link.name, "question_count"), 1)

    def test_nora_reads_the_slides_and_never_the_notes_unless_the_link_lends_them(self):
        lent = {p["id"]: p for p in asking.passages(self.link)}
        self.assertEqual(set(lent), {"S1", "S2"})
        self.link.db_set("nora_reads_notes", 1)
        self.assertIn(
            "N2", {p["id"] for p in asking.passages(frappe.get_doc("Presentation Link", self.link.name))}
        )

    def test_an_answer_nora_is_sure_of_reaches_the_person_with_its_sources(self):
        seen = {}

        def fake(**kwargs):
            seen.update(kwargs)
            return {
                "sure": True,
                "answer": "467 comptes, sur un seul dossier.",
                "sources": ["S2"],
                "reason": "answered",
            }

        doc = self.answered_by(fake, self.ask())
        self.assertEqual(doc.status, "Answered by Nora")
        self.assertEqual(seen["slide"], 2)
        self.assertEqual({p["id"] for p in seen["passages"]}, {"S1", "S2"})
        self.assertEqual(self.thread()[-1]["sources"], ["Slide 2"])
        self.assertEqual(self.thread()[-1]["slides"], [2])  # its chip turns the deck to slide 2
        self.assertNotIn([STAFF], [mail["recipients"] for mail in self.sent])  # nobody has to answer it
        self.assertEqual(self.alerts, [])

    def test_an_answer_nora_is_not_sure_of_waits_for_the_person_who_answers(self):
        fake = lambda **kw: {"sure": False, "answer": "", "sources": [], "reason": "price_or_commitment"}  # noqa: E731
        doc = self.answered_by(fake, self.ask("Combien coûte la reprise ?"))
        self.assertEqual((doc.status, doc.nora_reason), ("Waiting", "price_or_commitment"))
        mail = self.sent[-1]
        self.assertEqual(mail["recipients"], [STAFF])
        self.assertIn("Combien coûte la reprise ?", mail["message"])
        self.assertEqual(self.alerts, [STAFF])
        self.assertEqual(frappe.db.get_value("Presentation Link", self.link.name, "waiting_count"), 1)
        self.assertEqual(self.thread()[-1]["status"], "Waiting")

    def test_a_source_that_does_not_exist_is_not_an_answer(self):
        fake = lambda **kw: {"sure": True, "answer": "Oui.", "sources": ["S9"], "reason": "answered"}  # noqa: E731
        self.assertEqual(self.answered_by(fake, self.ask()).status, "Waiting")

    def test_a_silent_or_failing_answerer_forwards_the_question(self):
        self.assertEqual(self.answered_by(lambda **kw: None, self.ask()).status, "Waiting")

        def broken(**kw):
            raise RuntimeError("the model is down")

        self.assertEqual(self.answered_by(broken, self.ask("Et la TVA ?")).status, "Waiting")

    def test_a_link_that_forwards_every_question_never_asks_nora(self):
        self.link.db_set("questions_mode", asking.MODE_FORWARD)
        called = []
        doc = self.answered_by(lambda **kw: called.append(1), self.ask())
        self.assertEqual((doc.status, doc.nora_reason, called), ("Waiting", "forward_every_question", []))

    def test_a_link_without_questions_takes_none(self):
        self.link.db_set("questions_mode", asking.MODE_NONE)
        with as_role("Guest"):
            self.assertEqual(api.ask(self.visit, "Une question ?", 1)["reason"], "closed")

    def test_a_question_too_short_too_long_or_too_many(self):
        with as_role("Guest"):
            self.assertEqual(api.ask(self.visit, " ? ", 1)["reason"], "empty")
            self.assertEqual(api.ask(self.visit, "x" * 501, 1)["reason"], "too_long")
            with patch.object(asking, "PER_PERSON_A_DAY", 0):
                self.assertEqual(api.ask(self.visit, "Une question ?", 1)["reason"], "too_many")
            self.assertFalse(api.ask("not-a-visit", "Une question ?", 1)["ok"])

    def test_the_answer_of_the_person_reaches_the_visitor_and_is_lent_to_this_link_only(self):
        fake = lambda **kw: {"sure": False, "answer": "", "sources": [], "reason": "price_or_commitment"}  # noqa: E731
        name = self.answered_by(fake, self.ask("Combien coûte la reprise ?")).name
        with as_role(STAFF):
            api.reply_question(name, "Au forfait par dossier.", retained=1, send=1)
        doc = frappe.get_doc("Presentation Question", name)
        self.assertEqual((doc.status, doc.answered_by, doc.sent_to_visitor), ("Answered", STAFF, 1))
        mail = self.sent[-1]
        self.assertEqual(mail["recipients"], ["anna@firm-example.ch"])
        self.assertEqual(mail["reply_to"], STAFF)
        self.assertIn("Au forfait par dossier.", mail["message"])
        self.assertEqual(mail["message"].count("Anna,"), 1)  # the mail greets her
        self.assertEqual(self.thread()[-1]["answer"], "Au forfait par dossier.")
        kept = [p for p in asking.passages(self.link) if p["kind"] == "answer"]
        self.assertEqual(len(kept), 1)
        self.assertIn("Au forfait par dossier.", kept[0]["text"])
        other = self.new_link(title=f"{PREFIX} other link")
        self.assertEqual([p for p in asking.passages(other) if p["kind"] == "answer"], [])

    def test_the_question_reaches_the_person_who_answers_in_her_language_and_a_reply_reaches_the_visitor(
        self,
    ):
        # Nora's job forwards the question; a job of frappe runs in English whatever its user reads
        frappe.db.set_value("User", STAFF, "language", "de")
        frappe.clear_document_cache("User", STAFF)
        self.addCleanup(frappe.clear_document_cache, "User", STAFF)
        self.addCleanup(frappe.db.set_value, "User", STAFF, "language", None)
        before = frappe.local.lang
        frappe.local.lang = "en"
        self.addCleanup(setattr, frappe.local, "lang", before)
        fake = lambda **kw: {"sure": False, "answer": "", "sources": [], "reason": "price_or_commitment"}  # noqa: E731
        self.answered_by(fake, self.ask("Combien coûte la reprise ?"))
        mail = self.sent[-1]
        self.assertEqual((mail["recipients"], mail["lang"]), ([STAFF], "de"))
        self.assertEqual(frappe.local.lang, "en")  # the job's language comes back
        self.assertEqual(mail["reply_to"], "anna@firm-example.ch")  # « Reply » writes to the person who asked
        self.assertIn(f"/app/presentation-link/{self.link.name}?tab=questions", mail["message"])

    def test_an_answer_that_greets_her_itself_is_not_greeted_twice_and_comes_first(self):
        fake = lambda **kw: {"sure": False, "answer": "", "sources": [], "reason": "price_or_commitment"}  # noqa: E731
        name = self.answered_by(fake, self.ask("Combien coûte la reprise ?")).name
        with as_role(STAFF):
            api.reply_question(name, "Bonjour Anna,\nau forfait par dossier.", retained=0, send=1)
        message = self.sent[-1]["message"]
        self.assertEqual(message.count("Anna,"), 1)
        self.assertLess(message.index("au forfait par dossier."), message.index("Combien coûte la reprise ?"))

    def test_a_reply_to_the_link_mail_writes_to_the_one_who_sent_it(self):
        with as_role(STAFF):
            api.send_link(self.link.name, "paul@firm-example.ch", "Paul")
        self.assertEqual(
            (self.sent[-1]["recipients"], self.sent[-1]["reply_to"]), (["paul@firm-example.ch"], STAFF)
        )
        self.link.db_set("allow_forward", 1)
        with as_role("Guest"):
            self.assertTrue(api.forward(self.visit, "lea@firm-example.ch", "Léa")["ok"])
        self.assertEqual(self.sent[-1]["reply_to"], "anna@firm-example.ch")

    def test_a_person_sees_her_questions_only(self):
        self.ask("La question d'Anna ?")
        other = self.enter(email="marc@firm-example.ch")
        self.assertEqual(self.thread(other), [])

    def test_a_portal_account_reads_no_question_and_answers_none(self):
        name = self.ask()
        with as_role(PORTAL):
            self.assertEqual(_listed("Presentation Question"), [])
            self.assertFalse(frappe.has_permission("Presentation Question", "read", name))
            self.assertRaises(frappe.PermissionError, api.reply_question, name, "Non.")
            self.assertRaises(frappe.PermissionError, api.get_questions, self.link.name)

    def test_the_staff_see_the_waiting_questions_first(self):
        fake = lambda **kw: {"sure": False, "answer": "", "sources": [], "reason": "not_in_passages"}  # noqa: E731
        sure = lambda **kw: {"sure": True, "answer": "467.", "sources": ["S2"], "reason": "answered"}  # noqa: E731
        self.answered_by(sure, self.ask("Combien de comptes ?"))
        self.answered_by(fake, self.ask("Et la paie ?"))
        with as_role(STAFF):
            view = api.get_questions(self.link.name)
        self.assertEqual([q.status for q in view["questions"]], ["Waiting", "Answered by Nora"])
        self.assertEqual((view["count"], view["by_nora"], view["waiting"], view["slides"]), (2, 1, 1, 2))

    def test_a_reload_is_one_entry_and_another_device_is_told(self):
        first = frappe.get_all(
            "Presentation Visit", filters={"link": self.link.name}, fields=["name", "viewer", "started_on"]
        )[0]
        frappe.db.set_value("Presentation Visit", first.name, "device", "Computer")
        start = get_datetime(first.started_on)
        for minutes, device in ((5, "Computer"), (90, "Computer"), (120, "Phone")):
            _visit(self.link.name, first.viewer, start + timedelta(minutes=minutes), device)
        with as_role(STAFF):
            stats = api.get_stats(self.link.name)
        visits = [(e["again"], e["new_device"]) for e in stats["events"] if e["kind"] == "visit"]
        # the reload five minutes later is the same sitting; ninety minutes later she comes back; then on a phone
        self.assertEqual(visits, [(False, False), (True, False), (True, True)])
        self.assertEqual(stats["viewers"][0].device_kinds, ["Computer", "Phone"])
        self.assertEqual(stats["slide_titles"], ["Couverture", "La reprise"])

    def test_two_people_of_the_same_first_name_are_told_apart_by_their_address(self):
        self.enter(email="anna.b@firm-example.ch")  # an Anna again, another person
        with as_role(STAFF):
            stats = api.get_stats(self.link.name)
        self.assertEqual(
            sorted(v.who for v in stats["viewers"]),
            ["Anna (anna.b@firm-example.ch)", "Anna (anna@firm-example.ch)"],
        )

    def test_a_trial_answers_as_a_visitor_and_records_nothing(self):
        sure = lambda **kw: {"sure": True, "answer": "467.", "sources": ["S2", "S9"], "reason": "answered"}  # noqa: E731
        sent, jobs = len(self.sent), len(self.jobs)
        with patch.object(asking, "_answerer", return_value=sure), as_role(STAFF):
            result = api.try_question(self.link.name, "Combien de comptes ?", 2)
        # a source the link does not lend (S9) is dropped, the one it lends is told with its slide
        self.assertEqual((result["sure"], result["answer"], result["slides"]), (True, "467.", [2]))
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(frappe.db.count("Presentation Question", {"link": self.link.name}), 0)
        self.assertEqual((len(self.sent), len(self.jobs)), (sent, jobs))

    def test_a_trial_says_why_nora_would_forward_it(self):
        unsure = lambda **kw: {"sure": False, "answer": "", "sources": [], "reason": "price_or_commitment"}  # noqa: E731
        with patch.object(asking, "_answerer", return_value=unsure), as_role(STAFF):
            self.assertEqual(
                api.try_question(self.link.name, "Combien ça coûte ?"),
                {"sure": False, "reason": "price_or_commitment"},
            )
        every = self.new_link(questions_mode=asking.MODE_FORWARD)
        called = []
        with patch.object(asking, "_answerer", return_value=lambda **kw: called.append(kw)), as_role(STAFF):
            self.assertEqual(api.try_question(every.name, "Combien ?")["reason"], "forward_every_question")
        self.assertEqual(called, [])

    def test_a_portal_account_cannot_try_a_question(self):
        with as_role(PORTAL):
            self.assertRaises(frappe.PermissionError, api.try_question, self.link.name, "Combien ?")


def _listed(doctype: str) -> list:
    """What the acting account lists of `doctype`: a refusal lists nothing too."""
    try:
        return frappe.get_list(doctype, limit=5)
    except frappe.PermissionError:
        return []


def _visit(link: str, viewer: str, started_on, device: str):
    """A visit of `viewer`, as a browser that opens the link again leaves one."""
    return frappe.get_doc(
        {
            "doctype": "Presentation Visit",
            "link": link,
            "viewer": viewer,
            "started_on": started_on,
            "device": device,
            "slide_count": 2,
        }
    ).insert(ignore_permissions=True)


def _file(name: str, folder: str, is_folder: int = 0, content: str | None = None):
    return frappe.get_doc(
        {
            "doctype": "File",
            "file_name": name,
            "folder": folder,
            "is_folder": is_folder,
            "is_private": 1,
            "content": content if not is_folder else None,
        }
    ).insert(ignore_permissions=True)


def _user(email: str, user_type: str, roles=()):
    if not frappe.db.exists("User", email):
        frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "Questions",
                "user_type": user_type,
                "send_welcome_email": 0,
            }
        ).insert(ignore_permissions=True)
    if roles:
        frappe.get_doc("User", email).add_roles(*roles)
    frappe.db.set_value("User", email, "user_type", user_type)


def _ours(doctype: str) -> dict:
    if doctype == "Presentation Link":
        return {"title": ["like", f"{PREFIX}%"]}
    links = frappe.get_all("Presentation Link", filters={"title": ["like", f"{PREFIX}%"]}, pluck="name")
    return {"link": ["in", links or [""]]}

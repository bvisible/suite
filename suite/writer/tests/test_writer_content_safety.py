# //// Neoffice — added file (no upstream equivalent): what Writer stores and draws as markup, and what a commenter
# //// may change in the comments blob (neoffice-maintenance#2296).
"""Writer content that other people's screens draw as HTML.

- The document's `html` is drawn with v-html in the Writer home's grid view: it is filtered on every save path.
- A search snippet is drawn with v-html: it is text, with only the index's <mark> highlights.
- The comments blob is built by the client, owners included: a reader who may only comment changes their own
  comments and nobody else's, and a mention is announced in the name of the person who saves, never another.
- The print settings are written into a same-origin iframe's CSS: the Writer frontend escapes them.
"""

from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import patch

import frappe
import pycrdt
from frappe.tests import UnitTestCase
from frappe.tests.roles import as_role

from suite.writer.api import general
from suite.writer.doctype.writer_document import writer_document
from suite.writer.doctype.writer_document.writer_document import check_comment_changes, clean_html

FRONTEND = Path(frappe.get_app_path("suite")).parent / "frontend" / "src" / "apps" / "writer"
SCRIPT = "<img src=x onerror=alert(1)>"
FORMATTED = (
    "<h2>Title</h2><p>Some <strong>bold</strong> and <em>été</em></p><ul><li>one</li></ul>"
    '<table><tbody><tr><td style="color: red;">cell</td></tr></tbody></table>'
    '<p><a href="https://example.com/page">link</a><img src="/files/picture.png"></p>'
)


def comments_blob(comments: dict) -> str:
    doc = pycrdt.Doc()
    root = doc.get("comments", type=pycrdt.Map)
    for comment_id, comment in comments.items():
        root[comment_id] = comment
    return base64.b64encode(doc.get_update()).decode()


def comment(owner: str, text: str, replies: list | None = None, mentions: list | None = None) -> dict:
    return {"owner": owner, "text": text, "replies": replies or [], "mentions": mentions or []}


class TestStoredHtml(UnitTestCase):
    def test_save_doc_stores_the_html_through_the_xss_filter(self):
        doc = frappe.new_doc("Writer Document")
        doc.name = "writer-html-test"
        doc.content = ""
        for html in (f"<p>Hello</p>{SCRIPT}", f'"{SCRIPT}"'):
            with (
                self.subTest(html=html),
                as_role("sales_user"),
                patch.object(type(doc), "check_permission"),
                patch.object(type(doc), "update_file"),
                patch.object(frappe.db, "set_value") as set_value,
            ):
                doc.save_doc(data="", html=html)
                stored = next(call.args[3] for call in set_value.call_args_list if call.args[2] == "html")
                self.assertNotIn("onerror", stored)

    def test_save_html_filters_a_value_that_parses_as_json(self):
        doc = frappe.new_doc("Writer Document")
        doc.name = "writer-html-test"
        with (
            as_role("sales_user"),
            patch.object(type(doc), "check_permission"),
            patch.object(type(doc), "update_file"),
            patch.object(type(doc), "save"),
        ):
            doc.save_html(html=f'"{SCRIPT}"')
        self.assertNotIn("onerror", doc.html)

    def test_ordinary_formatting_is_kept(self):
        cleaned = clean_html(FORMATTED)
        for kept in (
            "<h2>Title</h2>",
            "<strong>bold</strong>",
            "<em>été</em>",
            "<li>one</li>",
            "cell</td>",
            "color: red",
            'href="https://example.com/page"',
            'src="/files/picture.png"',
        ):
            self.assertIn(kept, cleaned)


class TestSearchSnippet(UnitTestCase):
    def test_a_snippet_goes_out_escaped_with_its_highlights(self):
        results = {
            "results": [{"name": "doc-1", "content": f"before {SCRIPT} <mark>word</mark> after"}],
            "summary": {},
        }
        with (
            as_role("sales_user"),
            patch.object(general, "WriterSearch") as writer_search,
            patch.object(general, "search_drive_files", return_value=[]),
            patch.object(general, "get_drive_file_meta", return_value={"doc-1": {"name": "file-1"}}),
            patch.object(general, "get_user_access", return_value={"read": 1}),
        ):
            writer_search.return_value.search.return_value = results
            found = general.search("word")

        content = found["results"][0]["content"]
        self.assertNotIn("<img", content)
        self.assertIn("&lt;img", content)
        self.assertIn("<mark>word</mark>", content)


class TestComments(UnitTestCase):
    alice = "alice@example.test"
    carol = "carol@example.test"

    def stored(self, user: str) -> dict:
        return {
            "c1": comment(self.alice, "first", replies=[{"id": "r1", "owner": self.carol, "text": "agreed"}]),
            "c2": comment(user, "mine"),
        }

    def test_a_commenter_cannot_rewrite_or_remove_another_persons_comment(self):
        with as_role("sales_user") as user:
            old = self.stored(user)
            rewritten = {**old, "c1": {**old["c1"], "text": "changed"}}
            without_reply = {**old, "c1": {**old["c1"], "replies": []}}
            without_comment = {"c2": old["c2"]}
            forged = {**old, "c3": comment(self.alice, "in alice's name")}
            for new in (rewritten, without_reply, without_comment, forged):
                with self.subTest(new=new), self.assertRaises(frappe.PermissionError):
                    check_comment_changes(old, new, user)

    def test_a_commenter_replies_and_edits_their_own(self):
        with as_role("sales_user") as user:
            old = self.stored(user)
            reply = {"id": "r2", "owner": user, "text": "me too"}
            new = {
                # the client writes the comment back with fields of its own (`top`), and the new reply
                "c1": {**old["c1"], "top": 120, "replies": [*old["c1"]["replies"], reply]},
                "c2": {**old["c2"], "text": "mine, edited"},
                "c3": comment(user, "a new one"),
            }
            check_comment_changes(old, new, user)

    def test_a_mention_is_announced_only_for_what_the_saver_wrote(self):
        with as_role("sales_user") as user:
            doc = frappe.new_doc("Writer Document")
            doc.name = "writer-comments-test"
            doc.ycomments = None
            data = comments_blob(
                {
                    "c1": comment(
                        self.alice,
                        "first",
                        mentions=[{"id": "dave@example.test"}],
                        replies=[{"id": "r1", "owner": user, "text": "x", "mentions": [{"id": self.carol}]}],
                    )
                }
            )
            with (
                patch.object(frappe.db, "set_value"),
                patch.object(writer_document.frappe, "enqueue") as enqueue,
            ):
                doc.save_comments(data, frappe._dict(file_name="Doc"), can_write=True)

        mentions = [m for call in enqueue.call_args_list for m in call.kwargs["mentions"]]
        self.assertEqual(mentions, [{"id": self.carol, "owner": user}])

    def test_a_commenter_without_write_is_refused_before_anything_is_stored(self):
        with as_role("sales_user") as user:
            doc = frappe.new_doc("Writer Document")
            doc.name = "writer-comments-test"
            doc.ycomments = comments_blob(self.stored(user))
            data = comments_blob({"c2": comment(user, "mine")})
            with (
                patch.object(frappe.db, "set_value") as set_value,
                self.assertRaises(frappe.PermissionError),
            ):
                doc.save_comments(data, frappe._dict(file_name="Doc"), can_write=False)
            set_value.assert_not_called()


class TestWriterScreens(UnitTestCase):
    """The frontend fixes, read from the source (the built bundle is made from it in CI)."""

    def test_the_grid_thumbnail_is_sanitized(self):
        source = (FRONTEND / "components" / "RoundedListView.vue").read_text()
        self.assertNotIn('v-html="row.html"', source)
        self.assertIn('v-html="thumbnailHtml(row.html)"', source)
        self.assertIn("DOMPurify.sanitize(", source)

    def test_print_settings_are_escaped_into_the_css(self):
        source = (FRONTEND / "utils" / "index.js").read_text()
        for key in ("print_header_left", "print_header_right", "print_footer_left", "print_footer_right"):
            self.assertNotIn(f'"${{settings?.{key}', source)
            self.assertIn(f"cssString(settings?.{key})", source)
        self.assertNotIn("${settings?.font_size || 15}", source)
        self.assertIn("cssNumber(settings?.font_size, 15)", source)

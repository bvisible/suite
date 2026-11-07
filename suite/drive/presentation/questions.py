# //// Neoffice — added file (no upstream equivalent): the questions asked on a shared presentation (maintenance#2337).
# //// A person watching it asks about the slide on screen; an app may answer from what the link lends it (the hook
# //// `presentation_question_answerer`, which nora provides), otherwise the question waits for the person who answers
# //// for the link, who answers by e-mail from the link's record. What she answers, kept, is lent to the answerer for
# //// the next people of the same link, never of another link (an answer may name a price for one client only).
from __future__ import annotations

import json
import re
from contextlib import contextmanager

import frappe
from frappe import _
from frappe.translate import get_user_lang
from frappe.utils import cint, escape_html, get_fullname, now_datetime

from suite.drive.presentation import rules

MODE_NORA = "Nora Answers, Else Forwards"
MODE_FORWARD = "Forward Every Question"
MODE_NONE = "No Questions"

MIN_CHARS = 3
MAX_CHARS = 500
# A person asks at most this many questions a day on a link, and a link takes this many a day from everyone.
PER_PERSON_A_DAY = 30
PER_LINK_A_DAY = 200
SLIDE_CHARS = 2500
NOTES_CHARS = 1500
DECK_CACHE_SECONDS = 24 * 3600
ANSWERS_LENT = 40
# An answer that greets the person itself (French, German, Italian, English: the languages of the fleet's clients).
_GREETING = re.compile(
    r"\s*(bonjour|bonsoir|salut|cher|chère|madame|monsieur|grüezi|guten (tag|morgen|abend)|hallo|liebe|lieber|"
    r"sehr geehrte|buongiorno|buonasera|ciao|gentile|caro|cara|hello|hi|dear)\b",
    re.I,
)


# ---------------------------------------------------------------------------------------------------------------------
# What a presentation says, slide by slide
# ---------------------------------------------------------------------------------------------------------------------
def extract_slides(html: str) -> list[dict]:
    """The slides of a web presentation, in the order the bridge counts them (bridge.js): the top sections of a
    reveal.js deck, else the elements marked `.slide`. Each: its `index` (from 1), `title` (`data-title`, else its
    first heading), `text` (images' alternative texts included), the speaker's `notes` (`aside.notes`) and the
    `part` it belongs to (`data-part`, 0 when the deck has no parts)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or "", "html.parser")
    nodes = soup.select(".reveal .slides > section") or soup.select(".slide")
    slides = []
    for index, node in enumerate(nodes, start=1):
        notes = " ".join(_text(aside) for aside in node.select("aside.notes"))
        for aside in node.select("aside.notes"):
            aside.decompose()
        for junk in node.select("script, style, template, noscript"):
            junk.decompose()
        for image in node.select("img[alt]"):
            alt = (image.get("alt") or "").strip()
            image.replace_with(f" {alt} " if alt else " ")
        heading = node.find(["h1", "h2", "h3"])
        title = (node.get("data-title") or (_text(heading) if heading else "") or "").strip()
        slides.append(
            {
                "index": index,
                "title": title[:140],
                "text": _text(node)[:SLIDE_CHARS],
                "notes": notes[:NOTES_CHARS],
                "part": cint(node.get("data-part") or 0),
            }
        )
    return slides


def parts_of(slides: list[dict]) -> list[dict]:
    """The parts of a deck that marks them (`data-part`), in order: each its number, the slides it spans, and its
    name, the title of its first slide without its number (« 04 WinBiz » → « WinBiz »)."""
    parts: list[dict] = []
    for slide in slides:
        number = slide.get("part") or 0
        if not number:
            continue
        if parts and parts[-1]["part"] == number:
            parts[-1]["end"] = slide["index"]
            continue
        label = re.sub(r"^\s*\d+[\s.·:\u2013-]*", "", slide.get("title") or "").strip()
        parts.append(
            {"part": number, "label": label or str(number), "start": slide["index"], "end": slide["index"]}
        )
    return parts


def _text(node) -> str:
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True) if node else "").strip()


def deck_slides(link) -> list[dict]:
    """The slides of the link's presentation, read once per version of its entry file."""
    from suite.drive.presentation.renderer import _read

    _, entry = rules.entry_file(link.presentation)
    modified = frappe.db.get_value("File", entry.name, "modified")
    key = f"presentation_slides:v2:{entry.name}:{modified}"  # v2: each slide carries its part
    cached = frappe.cache.get_value(key)
    if cached is not None:
        return cached
    html = _read(frappe.get_doc("File", entry.name)).decode("utf-8", errors="replace")
    slides = extract_slides(html)
    frappe.cache.set_value(key, slides, expires_in_sec=DECK_CACHE_SECONDS)
    return slides


def slide_titles(link) -> list[str]:
    try:
        return [slide["title"] for slide in deck_slides(link)]
    except Exception:
        return []


def passages(link, slides: list[dict] | None = None) -> list[dict]:
    """What the answerer may read for this link, and nothing else: each slide (`S<n>`), its notes when the link lends
    them (`N<n>`), and the answers kept for this link (`R<n>`)."""
    slides = deck_slides(link) if slides is None else slides
    out = []
    for slide in slides:
        if slide["text"]:
            out.append(
                {
                    "id": f"S{slide['index']}",
                    "kind": "slide",
                    "slide": slide["index"],
                    "title": slide["title"],
                    "text": slide["text"],
                }
            )
        if link.nora_reads_notes and slide.get("notes"):
            out.append(
                {
                    "id": f"N{slide['index']}",
                    "kind": "notes",
                    "slide": slide["index"],
                    "title": slide["title"],
                    "text": slide["notes"],
                }
            )
    kept = frappe.get_all(
        "Presentation Question",
        filters={"link": link.name, "status": "Answered", "retained": 1},
        fields=["name", "question", "answer", "answered_by", "slide"],
        order_by="answered_on asc",
        limit=ANSWERS_LENT,
    )
    for number, row in enumerate(kept, start=1):
        if (row.answer or "").strip():
            out.append(
                {
                    "id": f"R{number}",
                    "kind": "answer",
                    "slide": row.slide,
                    "title": _("Answer of {0}").format(get_fullname(row.answered_by)),
                    "text": f"{row.question.strip()}\n{row.answer.strip()}",
                }
            )
    return out


# ---------------------------------------------------------------------------------------------------------------------
# Asking
# ---------------------------------------------------------------------------------------------------------------------
def enabled(link) -> bool:
    return (link.questions_mode or MODE_NORA) != MODE_NONE


def answers_for(link) -> str:
    """The user who answers the questions of the link."""
    return link.questions_to or link.owner


def visitor_settings(link) -> dict:
    """What the visitor's page needs to show the questions, once the person has entered."""
    return {
        "enabled": enabled(link),
        "nora": (link.questions_mode or MODE_NORA) == MODE_NORA and bool(_answerer()),
        "answeredBy": get_fullname(answers_for(link)),
        "slides": slide_titles(link) if enabled(link) else [],
    }


def ask(row, question: str, slide) -> dict:
    """Records the question of the visit `row` (a running visit, checked by the caller) and has it answered."""
    link = frappe.get_doc("Presentation Link", row.link)
    if not enabled(link):
        return {"ok": False, "reason": "closed", "message": _("Questions are not open on this presentation.")}
    question = re.sub(r"[ \t]+", " ", (question or "").strip())
    if len(question) < MIN_CHARS:
        return {"ok": False, "reason": "empty", "message": _("Write your question first.")}
    if len(question) > MAX_CHARS:
        return {
            "ok": False,
            "reason": "too_long",
            "message": _("A question of {0} characters at most, please.").format(MAX_CHARS),
        }
    if not (_count(f"person:{row.viewer}", PER_PERSON_A_DAY) and _count(f"link:{link.name}", PER_LINK_A_DAY)):
        return {
            "ok": False,
            "reason": "too_many",
            "message": _("You have asked many questions today: {0} will answer you by e-mail.").format(
                get_fullname(answers_for(link))
            ),
        }
    slide = min(max(cint(slide), 0), rules.MAX_SLIDES)
    titles = slide_titles(link)
    viewer = frappe.db.get_value("Presentation Viewer", row.viewer, ["email", "first_name"], as_dict=True)
    doc = frappe.get_doc(
        {
            "doctype": "Presentation Question",
            "link": link.name,
            "viewer": row.viewer,
            "visit": row.name,
            "email": viewer.email,
            "first_name": viewer.first_name,
            "slide": slide,
            "slide_title": titles[slide - 1] if 0 < slide <= len(titles) else "",
            "question": question,
            "status": "Asked",
            "asked_on": now_datetime(),
        }
    ).insert(ignore_permissions=True)
    _refresh_counts(link.name)
    frappe.enqueue(
        "suite.drive.presentation.questions.answer_question",
        queue="default",
        timeout=300,
        enqueue_after_commit=True,
        name=doc.name,
    )
    return {"ok": True, "question": doc.name}


def _count(key: str, limit: int) -> bool:
    """One more question under `key` today, when there is room."""
    cache_key = f"presentation_questions:{frappe.utils.today()}:{key}"
    used = cint(frappe.cache.get_value(cache_key))
    if used >= limit:
        return False
    frappe.cache.set_value(cache_key, used + 1, expires_in_sec=26 * 3600)
    return True


def _answerer():
    hooks = frappe.get_hooks("presentation_question_answerer")
    return frappe.get_attr(hooks[-1]) if hooks else None


def answer_question(name: str) -> None:
    """The job: the answerer answers from the link's passages, or the question waits for the person who answers."""
    doc = frappe.get_doc("Presentation Question", name)
    if doc.status != "Asked":
        return
    link = frappe.get_doc("Presentation Link", doc.link)
    answerer = _answerer()
    if (link.questions_mode or MODE_NORA) != MODE_NORA or not answerer:
        return forward(doc, link, "forward_every_question" if answerer else "no_answerer")
    started = now_datetime()
    lent: list[dict] = []
    try:
        lent = passages(link)
        result = answerer(
            question=doc.question,
            slide=doc.slide,
            slide_title=doc.slide_title,
            passages=lent,
            first_name=doc.first_name or "",
            title=link.title,
        )
    except Exception:
        frappe.log_error("Presentation question: the answerer failed", frappe.get_traceback())
        result = None
    seconds = (now_datetime() - started).total_seconds()
    known = {p["id"] for p in lent}
    sources = [s for s in (result or {}).get("sources") or [] if s in known]
    answer = ((result or {}).get("answer") or "").strip()
    if result and result.get("sure") and answer and sources:
        doc.db_set(
            {
                "status": "Answered by Nora",
                "nora_answer": answer[:2000],
                "nora_sources": json.dumps(sources),
                "nora_reason": "",
                "nora_seconds": round(seconds, 1),
            }
        )
        _refresh_counts(link.name)
        return
    doc.db_set(
        {
            "nora_answer": answer[:2000],
            "nora_sources": json.dumps(sources),
            "nora_seconds": round(seconds, 1),
        }
    )
    forward(doc, link, ((result or {}).get("reason") or "not_sure")[:140])


def forward(doc, link, reason: str) -> None:
    """The question waits for the person who answers for the link; she is told by e-mail and in her notifications."""
    doc.db_set({"status": "Waiting", "nora_reason": reason})
    _refresh_counts(link.name)
    user = answers_for(link)
    # Nora's job forwards the question, and a job of frappe writes in English whatever its user reads: the e-mail
    # and the notification are written in the language of the person who answers.
    with _language_of(user):
        _tell(doc, link, user, reason)


@contextmanager
def _language_of(user: str):
    before = frappe.local.lang
    frappe.local.lang = get_user_lang(user)
    try:
        yield
    finally:
        frappe.local.lang = before


def _tell(doc, link, user: str, reason: str) -> None:
    who = doc.first_name or doc.email
    subject = _("{0} asks a question on « {1} »").format(who, link.title)
    email = frappe.db.get_value("User", user, "email")
    if email:
        # the button opens the link's record on its Questions tab (presentation_link.js reads `tab`)
        url = frappe.utils.get_url(f"/app/presentation-link/{link.name}?tab=questions")
        person = f"{doc.first_name} ({doc.email})" if doc.first_name else doc.email
        if doc.slide and doc.slide_title:
            asks = _("{0} asks, on slide {1}, « {2} »:").format(person, doc.slide, doc.slide_title)
        elif doc.slide:
            asks = _("{0} asks, on slide {1}:").format(person, doc.slide)
        else:
            asks = _("{0} asks:").format(person)
        body = "".join(
            [
                f"<p>{escape_html(asks)}</p>",
                f'<blockquote style="margin:12px 0;padding:10px 14px;border-left:3px solid #f55d1a;'
                f'white-space:pre-line">{escape_html(doc.question)}</blockquote>',
                f"<p>{escape_html(_why(reason))}</p>",
                f'<p style="margin:22px 0"><a href="{escape_html(url)}" style="background:#141414;color:#ffffff;'
                f'padding:12px 20px;border-radius:10px;text-decoration:none;font-weight:600">'
                f"{escape_html(_('Reply'))}</a></p>",  # « Répondre », not « Réponse »
                f"<p>{escape_html(_('Your answer leaves by e-mail to {0}.').format(doc.email))}</p>",
            ]
        )
        frappe.sendmail(
            recipients=[email],
            subject=subject,
            message=body,
            # « Reply » in her mailbox writes to the person who asked, not to the site's sending address
            reply_to=doc.email,
            now=True,
            reference_doctype="Presentation Link",
            reference_name=link.name,
        )
    from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

    enqueue_create_notification(
        user,
        {
            "type": "Alert",
            "document_type": "Presentation Link",
            "document_name": link.name,
            "subject": escape_html(subject),
            "from_user": user,
        },
    )


def _why(reason: str) -> str:
    if reason == "forward_every_question":
        return _("The link sends every question to you.")
    if reason == "no_answerer":
        return _("Nora is not on this site: the question comes to you.")
    if reason == "price_or_commitment":
        return _("Nora does not answer a price or a commitment: that is for you.")
    return _(
        "Nora did not find a sure answer in the presentation: she told the person that you answer by e-mail."
    )


# ---------------------------------------------------------------------------------------------------------------------
# The visitor's thread
# ---------------------------------------------------------------------------------------------------------------------
def thread(row) -> dict:
    """The questions of the person of the visit `row` on its link, oldest first, as her page shows them."""
    link = frappe.get_doc("Presentation Link", row.link)
    rows = frappe.get_all(
        "Presentation Question",
        filters={"link": row.link, "viewer": row.viewer},
        fields=[
            "name",
            "slide",
            "slide_title",
            "question",
            "status",
            "nora_answer",
            "nora_sources",
            "answer",
            "answered_by",
        ],
        order_by="creation asc",
        limit=60,
    )
    lent = {}
    if any(r.status == "Answered by Nora" for r in rows):
        try:
            lent = {p["id"]: p for p in passages(link)}
        except Exception:
            lent = {}
    out = []
    for r in rows:
        item = {"name": r.name, "slide": r.slide, "question": r.question, "status": r.status}
        if r.status == "Answered by Nora":
            item["answer"] = r.nora_answer
            cited = _json_list(r.nora_sources)
            item["sources"] = [_source_label(lent.get(s), s) for s in cited]
            # the slide each source shows, for its chip to turn the deck there (none for a kept answer)
            item["slides"] = [
                (lent.get(s) or {}).get("slide") if (lent.get(s) or {}).get("kind") != "answer" else None
                for s in cited
            ]
        elif r.status == "Answered":
            item["answer"] = r.answer
            item["by"] = get_fullname(r.answered_by)
        out.append(item)
    return {"ok": True, "questions": out}


def _source_label(passage: dict | None, source: str) -> str:
    kind = (passage or {}).get("kind")
    if kind == "answer":
        return passage["title"]
    if passage and passage.get("slide"):
        return _("Slide {0}").format(passage["slide"])
    return source


def _json_list(value) -> list:
    try:
        data = json.loads(value or "[]")
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


# ---------------------------------------------------------------------------------------------------------------------
# The staff
# ---------------------------------------------------------------------------------------------------------------------
def staff_view(link) -> dict:
    """The questions of the link for its record: the counts, the waiting ones first, then the others."""
    rows = frappe.get_all(
        "Presentation Question",
        filters={"link": link.name},
        fields=[
            "name",
            "email",
            "first_name",
            "slide",
            "slide_title",
            "question",
            "status",
            "nora_answer",
            "nora_sources",
            "nora_reason",
            "answer",
            "answered_by",
            "answered_on",
            "retained",
            "asked_on",
        ],
        order_by="asked_on desc",
        limit=200,
    )
    try:
        lent = {p["id"]: p for p in passages(link)}
    except Exception:
        lent = {}
    for r in rows:
        r.who = r.first_name or r.email
        r.sources = [_source_label(lent.get(s), s) for s in _json_list(r.nora_sources)]
        r.answered_by_name = get_fullname(r.answered_by) if r.answered_by else ""
    order = {"Waiting": 0, "Asked": 1, "Answered by Nora": 2, "Answered": 3}
    rows.sort(key=lambda r: order.get(r.status, 9))
    return {
        "questions": rows,
        "count": len(rows),
        "by_nora": sum(1 for r in rows if r.status == "Answered by Nora"),
        "waiting": sum(1 for r in rows if r.status == "Waiting"),
        "answered_by": get_fullname(answers_for(link)),
        "mode": link.questions_mode or MODE_NORA,
        "nora": bool(_answerer()),
        "slides": sum(1 for p in lent.values() if p["kind"] == "slide"),
        "kept": sum(1 for p in lent.values() if p["kind"] == "answer"),
        "reference": reference_of(link),
    }


def reference_of(link) -> dict | None:
    """The client or the offer the link is attached to, by its title."""
    if not (link.reference_doctype and link.reference_name):
        return None
    title = link.reference_name
    try:
        field = frappe.get_meta(link.reference_doctype).get_title_field()
        if field and field != "name":
            title = frappe.db.get_value(link.reference_doctype, link.reference_name, field) or title
    except Exception:
        pass
    return {"doctype": link.reference_doctype, "name": link.reference_name, "title": title}


def trial(link, question: str, slide=None) -> dict:
    """What Nora would answer a person of the link, asked by the team on its record (« Try as a visitor »): the
    same passages, the same answerer and the same rule (a sure answer that cites a source the link lends), and
    nothing recorded, counted, forwarded or sent."""
    question = re.sub(r"[ \t]+", " ", (question or "").strip())
    if not MIN_CHARS <= len(question) <= MAX_CHARS:
        frappe.throw(_("A question of {0} to {1} characters, please.").format(MIN_CHARS, MAX_CHARS))
    if not enabled(link):
        return {"sure": False, "reason": "questions_closed"}
    answerer = _answerer()
    if (link.questions_mode or MODE_NORA) != MODE_NORA or not answerer:
        return {"sure": False, "reason": "forward_every_question" if answerer else "no_answerer"}
    # the model is called each time: a cap per person and per day, like a visitor's
    if not _count(f"trial:{frappe.session.user}", PER_PERSON_A_DAY * 2):
        frappe.throw(_("You have tried many questions today: try again tomorrow."))
    lent = passages(link)
    slide = min(max(cint(slide), 0), rules.MAX_SLIDES)
    titles = slide_titles(link)
    try:
        result = answerer(
            question=question,
            slide=slide,
            slide_title=titles[slide - 1] if 0 < slide <= len(titles) else "",
            passages=lent,
            first_name="",
            title=link.title,
        )
    except Exception:
        frappe.log_error("Presentation question: the answerer failed on a trial", frappe.get_traceback())
        result = None
    known = {p["id"]: p for p in lent}
    sources = [s for s in (result or {}).get("sources") or [] if s in known]
    answer = ((result or {}).get("answer") or "").strip()
    if result and result.get("sure") and answer and sources:
        return {
            "sure": True,
            "answer": answer,
            "sources": [_source_label(known[s], s) for s in sources],
            "slides": [known[s].get("slide") if known[s]["kind"] != "answer" else None for s in sources],
        }
    return {"sure": False, "reason": ((result or {}).get("reason") or "not_sure")[:140]}


def reply(doc, link, answer: str, retained: int, send: int) -> dict:
    """The answer of the person who answers for the link: kept for the next people when she wants, sent by e-mail."""
    answer = (answer or "").strip()
    if len(answer) < 2:
        frappe.throw(_("Write the answer first."))
    doc.db_set(
        {
            "status": "Answered",
            "answer": answer[:5000],
            "answered_by": frappe.session.user,
            "answered_on": now_datetime(),
            "retained": 1 if cint(retained) else 0,
        }
    )
    if cint(send) and doc.email:
        _send_answer(doc, link, answer)
        doc.db_set("sent_to_visitor", 1)
    _refresh_counts(link.name)
    return {"ok": True}


def _send_answer(doc, link, answer: str) -> None:
    sender = get_fullname(frappe.session.user)
    asked = (
        _("You asked, on slide {0} of « {1} »:").format(doc.slide, link.title)
        if doc.slide
        else _("You asked, about « {0} »:").format(link.title)
    )
    question = [
        f"<p>{escape_html(asked)}</p>",
        f'<blockquote style="margin:12px 0;padding:10px 14px;border-left:3px solid #e8e1d6;color:#4a4541;'
        f'white-space:pre-line">{escape_html(doc.question)}</blockquote>',
    ]
    words = [f'<p style="white-space:pre-line">{escape_html(answer)}</p>', f"<p>{escape_html(sender)}</p>"]
    # the person who answers often opens with « Bonjour Marc, » herself: her words then come first, the question
    # quoted under them, and the mail does not greet twice
    if _GREETING.match(answer):
        parts = words + question
    else:
        greeting = _("Hello {0},").format(doc.first_name) if doc.first_name else _("Hello,")
        parts = [f"<p>{escape_html(greeting)}</p>", *question, *words]
    parts.append(
        f'<p style="margin:22px 0"><a href="{escape_html(link.url)}" style="background:#141414;color:#ffffff;'
        f'padding:12px 20px;border-radius:10px;text-decoration:none;font-weight:600">'
        f"{escape_html(_('See the presentation again'))}</a></p>"
    )
    body = "".join(parts)
    frappe.sendmail(
        recipients=[doc.email],
        subject=_("Your question on « {0} »").format(link.title),
        message=body,
        reply_to=frappe.db.get_value("User", frappe.session.user, "email"),
        now=True,
        reference_doctype="Presentation Link",
        reference_name=link.name,
    )


def _refresh_counts(link: str) -> None:
    frappe.db.set_value(
        "Presentation Link",
        link,
        {
            "question_count": frappe.db.count("Presentation Question", {"link": link}),
            "waiting_count": frappe.db.count("Presentation Question", {"link": link, "status": "Waiting"}),
        },
        update_modified=False,
    )


def reading(link) -> str:
    """What the questions say, in two sentences, for the person who answers (the hook
    `presentation_questions_reader`); empty under two questions or without a reader."""
    rows = frappe.get_all(
        "Presentation Question",
        filters={"link": link.name},
        fields=["slide", "slide_title", "question", "status"],
        order_by="asked_on asc",
        limit=80,
    )
    hooks = frappe.get_hooks("presentation_questions_reader")
    if len(rows) < 2 or not hooks:
        return ""
    key = f"presentation_questions_reading:{link.name}:{len(rows)}:{sum(r.status == 'Waiting' for r in rows)}"
    cached = frappe.cache.get_value(key)
    if cached is not None:
        return cached
    try:
        text = frappe.get_attr(hooks[-1])(title=link.title, questions=[dict(r) for r in rows]) or ""
    except Exception:
        frappe.log_error("Presentation questions: the reader failed", frappe.get_traceback())
        text = ""
    frappe.cache.set_value(key, text, expires_in_sec=DECK_CACHE_SECONDS)
    return text

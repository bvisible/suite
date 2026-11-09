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
from suite.drive.presentation import sources as site_sources

MODE_NORA = "Nora Answers, Else Forwards"
MODE_FORWARD = "Forward Every Question"
MODE_NONE = "No Questions"

MIN_CHARS = 3
MAX_CHARS = 500
# A person asks at most this many questions a day on a link, and a link takes this many a day from everyone.
PER_PERSON_A_DAY = 30
PER_LINK_A_DAY = 200
# A dictated question: a minute of speech is a few hundred kilobytes; the request is refused above this.
DICTATION_BYTES = 4 * 1024 * 1024
DICTATION_TIMEOUT_S = 60
SLIDE_CHARS = 2500
NOTES_CHARS = 1500
DECK_CACHE_SECONDS = 24 * 3600
ANSWERS_LENT = 40
# The e-mail of a forwarded question carries what the same person asked before it on the link, the last ones at most.
CONVERSATION_IN_MAIL = 12
# An answer that greets the person itself (French, German, Italian, English: the languages of the fleet's clients).
_GREETING = re.compile(
    r"\s*(bonjour|bonsoir|salut|cher|chère|madame|monsieur|grüezi|guten (tag|morgen|abend)|hallo|liebe|lieber|"
    r"sehr geehrte|buongiorno|buonasera|ciao|gentile|caro|cara|hello|hi|dear)\b",
    re.I,
)

# What a person writes or says that is not a question (Jérémy, 09.11: « salut » went to the presenter): a greeting, a
# thank-you, a goodbye, an « ok », or who Nora is. Nora answers it herself and nothing is recorded or forwarded. A
# message is small talk only when every one of its words is one of these (« Bonjour, est-ce que… » is a question).
_SMALL_TALK_WORDS = {
    "greeting": {
        "bonjour",
        "bonsoir",
        "salut",
        "coucou",
        "hello",
        "hi",
        "hey",
        "grüezi",
        "gruezi",
        "hallo",
        "servus",
        "guten",
        "tag",
        "morgen",
        "abend",
        "buongiorno",
        "buonasera",
        "ciao",
        "allo",
        "allô",
    },
    "thanks": {"merci", "thanks", "thank", "danke", "grazie", "vielen", "dank", "mille", "infiniment"},
    "goodbye": {
        "revoir",
        "bientôt",
        "bientot",
        "bye",
        "tschüss",
        "tschuss",
        "arrivederci",
        "ciao",
        "adieu",
        "journée",
        "journee",
        "soirée",
        "soiree",
        "week-end",
        "weekend",
    },
    "ok": {
        "ok",
        "okay",
        "oki",
        "accord",
        "parfait",
        "super",
        "top",
        "génial",
        "genial",
        "cool",
        "test",
        "testing",
        "noted",
        "compris",
        "entendu",
        "nickel",
        "bravo",
    },
}
_SMALL_TALK_FILLER = {
    "nora",
    "à",
    "a",
    "au",
    "vous",
    "toi",
    "beaucoup",
    "bien",
    "très",
    "tres",
    "trop",
    "bonne",
    "bon",
    "d",
    "de",
    "et",
    "you",
    "much",
    "so",
    "madame",
    "monsieur",
    "encore",
    "mille",
    "fois",
    "tout",
    "le",
    "monde",
    "lot",
    "es",
    "est",
    "c",
    "ça",
    "ca",
    "un",
    "une",
}
_WHO_IS_NORA = re.compile(
    r"^(qui (es[- ]tu|êtes[- ]vous|etes[- ]vous|est nora|parle|me répond|me repond)|tu es qui|vous êtes qui|"
    r"c'?est qui( nora)?|tu es (un robot|une ia|une intelligence artificielle|humaine?)|"
    r"es[- ]tu (un robot|une ia|humaine?)|who are you|are you (a bot|a robot|human|an ai)|wer bist du|chi sei)$"
)


def small_talk(text: str) -> str | None:
    """The kind of a message that is not a question (« greeting », « thanks », « goodbye », « ok », « who »), or None."""
    plain = re.sub(r"[^\w\s'-]", " ", (text or "").lower().replace("\u2019", "'"))
    plain = re.sub(r"\s+", " ", plain).strip()
    if not plain or len(plain) > 80:
        return None
    if _WHO_IS_NORA.match(plain):
        return "who"
    words = [w for w in re.split(r"[\s'-]+", plain) if w]
    if not words or len(words) > 6:
        return None
    kinds = [kind for kind, vocabulary in _SMALL_TALK_WORDS.items() if any(w in vocabulary for w in words)]
    every = set().union(*_SMALL_TALK_WORDS.values()) | _SMALL_TALK_FILLER
    if not kinds or not all(w in every for w in words):
        return None
    for kind in ("thanks", "goodbye", "greeting", "ok"):
        if kind in kinds:
            return kind
    return None


def small_talk_reply(link, kind: str) -> str:
    """What Nora answers to a message that is not a question, in the visitor's language."""
    person = get_fullname(answers_for(link))
    nora = (link.questions_mode or MODE_NORA) == MODE_NORA
    if kind == "greeting":
        if nora:
            return _(
                "Hello! I am Nora. Ask me your question about this presentation: I answer from what it says, and what "
                "I do not know, {0} answers by e-mail."
            ).format(person)
        return _("Hello! Ask your question about this presentation: {0} answers you by e-mail.").format(
            person
        )
    if kind == "thanks":
        return _("You are welcome. Another question? I am here.")
    if kind == "goodbye":
        return _(
            "Thank you for your visit. The same link brings you back to the presentation whenever you like."
        )
    if kind == "who":
        return _(
            "I am Nora, an assistant. I answer your questions about this presentation from what it says, and I pass "
            "what I do not know to {0}, who answers you by e-mail."
        ).format(person)
    return _(
        "Very well. Ask me a question whenever you like, about the slide on screen or the whole presentation."
    )


# ---------------------------------------------------------------------------------------------------------------------
# What a presentation says, slide by slide
# ---------------------------------------------------------------------------------------------------------------------
def extract_slides(html: str) -> list[dict]:
    """The slides of a web presentation, in the order the bridge counts them (bridge.js): the top sections of a
    reveal.js deck, else the elements marked `.slide`. Each: its `index` (from 1), `title` (`data-title`, else its
    first heading), `text` (images' alternative texts included, and kept apart in `alts`), the speaker's `notes`
    (`aside.notes`) and the `part` it belongs to (`data-part`, 0 when the deck has no parts)."""
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
        alts = []
        for image in node.select("img[alt]"):
            alt = (image.get("alt") or "").strip()
            if alt:
                alts.append(alt)
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
                "alts": alts[:40],
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
    # v3: each slide carries its part and, apart, its images' texts
    key = f"presentation_slides:v3:{entry.name}:{modified}"
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


def names_of(link) -> tuple[list[str], set[str]]:
    """The names the link's presentation uses and the words it writes in small letters (names_in), read from its
    slides and its title."""
    try:
        slides = deck_slides(link)
    except Exception:
        slides = []
    pieces = []
    for slide in slides:
        body = slide.get("text") or ""
        # an image's text is not prose: a logo writes its brand small (« neoffice ») on every slide
        for alt in slide.get("alts") or []:
            body = body.replace(alt, " ", 1)
        pieces.append(f"{slide.get('title') or ''}. {body}.")
    return names_in(f"{link.title or ''}. {' '.join(pieces)}")


def names_in(text: str) -> tuple[list[str], set[str]]:
    """The names of `text` and its words in small letters (folded). A name is written with a capital where a
    sentence does not begin (« Neoffice », « WinBiz », « FIDAG »), at least twice, and never in small letters; a word
    that opens a heading is not one, nor a verb or a participle of a title (« Reprendre », « Hébergé »)."""
    lower, capital, seen = set(), [], {}
    for match in re.finditer(r"[^\W\d_][\w'\u2019-]*", text or ""):
        word = re.split(r"['\u2019]", match.group(0))[-1].strip("-")
        if len(word) < 3 or _in_address(text, match):
            # a site or an address (« neoffice.ch ») does not make its name a common word
            continue
        if word.islower():
            lower.add(word)
            continue
        seen[word] = seen.get(word, 0) + 1
        before = (text[: match.start()].rstrip() or ".")[-1]
        inner_capital = any(c.isupper() for c in word[1:])
        if (before in '.!?:;«»\u00b7\u2022|()\u2013\u2014"' and not inner_capital) or word in capital:
            continue
        if not inner_capital and re.search(r"(er|ir|re|é|ée|és|ées)$", word.lower()):
            continue
        capital.append(word)
    names = [word for word in capital if seen[word] >= 2 and word.lower() not in lower]
    return names, {_fold(word) for word in lower}


NAME_LIKENESS = 0.7


def fix_names(text: str, names: list[str], known: set[str] | None = None) -> str:
    """`text` with a word that sounds like one of `names`, or a short piece run with the next word (« Neo office »),
    written as that name. A transcription does not know a product's name and writes the nearest words it knows
    (« NeoFix », « Neo office » for « Neoffice », 09.11), and Nora, asked about a « NeoFix » the slides never name,
    sent a plain question to the presenter. Only a long name (6 letters or more) is guessed this way, from a word
    with its first four letters, never a word the presentation itself writes in small letters (`known`) nor a word
    the name begins (« exporter » stays): « Nord » never becomes « Nora », « répondre » never « Reprendre »."""
    if not text or not names:
        return text
    known = known or set()
    keys: dict[str, str] = {}
    for name in names:
        if len(_fold(name)) >= 6:
            keys.setdefault(_squash(_fold(name)), name)
    if not keys:
        return text
    words = list(re.finditer(r"[\w'\u2019-]+", text))
    out, cursor, index = [], 0, 0
    while index < len(words):
        word = words[index]
        # an address or a site (« neoffice.ch », « jeremy@… ») is written as it is
        if _in_address(text, word):
            index += 1
            continue
        prefix, core = _elided(word.group(0))
        span, name = 1, keys.get(_squash(_fold(core)))
        if name == core:
            name = None
        elif not name and _fold(core) not in known:
            following = words[index + 1] if index + 1 < len(words) else None
            if following and len(_fold(core)) <= 4 and not text[word.end() : following.start()].strip():
                name = _closest(_squash(_fold(core + following.group(0))), keys)
                span = 2 if name else 1
            name = name or _closest(_squash(_fold(core)), keys)
        if name:
            out.append(text[cursor : word.start()] + prefix + name)
            cursor = words[index + span - 1].end()
        index += span
    out.append(text[cursor:])
    return "".join(out)


def _in_address(text: str, word) -> bool:
    """Whether the matched `word` is a piece of a site, an address or a path (« neoffice.ch », « info@… »)."""
    return bool(re.match(r"[./@]\w", text[word.end() : word.end() + 2])) or bool(
        word.start() and text[word.start() - 1] in "@/."
    )


def _elided(word: str) -> tuple[str, str]:
    """« l'office » is « l' » and « office »."""
    match = re.match(r"^(\w{1,2}['\u2019])(.+)$", word)
    return (match.group(1), match.group(2)) if match else ("", word)


def _fold(word: str) -> str:
    import unicodedata

    plain = unicodedata.normalize("NFKD", word or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", plain.lower())


def _squash(word: str) -> str:
    """« neooffice » and « neoffice » are said the same: a doubled letter counts once."""
    return re.sub(r"(.)\1+", r"\1", word)


def _closest(candidate: str, keys: dict[str, str]) -> str | None:
    from difflib import SequenceMatcher

    if len(candidate) < 5:
        return None
    best, score = None, NAME_LIKENESS
    for key, name in keys.items():
        if candidate == key:
            return name
        if candidate[:4] != key[:4] or candidate.startswith(key) or key.startswith(candidate):
            continue
        if abs(len(candidate) - len(key)) > 3:
            continue
        ratio = SequenceMatcher(None, candidate, key).ratio()
        if ratio >= score:
            best, score = name, ratio
    return best


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
        "dictation": bool(enabled(link) and transcriber()),
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
    kind = small_talk(question)
    if kind:
        # not a question: Nora answers it here, and nothing is recorded, counted or forwarded
        return {"ok": True, "reply": small_talk_reply(link, kind)}
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


def transcriber():
    """How the visitor's page writes down a dictated question: the site's transcription service (Nora's whisper, in
    Switzerland, with the address and key of Nora's settings and its conversion to wav), or None when the site has
    none, and the page then shows no microphone. Nora's own endpoint is for the staff (`staff_only`, #1925); here the
    proof is the visit's secret, checked by the caller, and a ceiling per address (api.transcribe)."""
    if "nora" not in frappe.get_installed_apps():
        return None
    try:
        settings = frappe.get_attr("nora.api.stt._get_stt_config")
        to_wav = frappe.get_attr("nora.api.stt._maybe_transcode_to_wav")
    except Exception:
        return None

    def listen(upload, language: str = "fr") -> dict:
        import requests

        audio = upload.read()
        if not audio or len(audio) < 256:
            return {"success": False}
        audio, filename, content_type = to_wav(
            audio, upload.filename or "question.webm", upload.content_type or ""
        )
        url, key = settings()
        try:
            reply = requests.post(
                f"{url}/v1/audio/transcriptions",
                files={"file": (filename, audio, content_type)},
                data={"model": "whisper-1", "language": language},
                headers={"Authorization": f"Bearer {key}"} if key else {},
                timeout=DICTATION_TIMEOUT_S,
            )
        except Exception:
            frappe.log_error("Presentation question: the transcription failed", frappe.get_traceback())
            return {"success": False}
        if reply.status_code != 200:
            frappe.log_error("Presentation question: the transcription failed", reply.text[:500])
            return {"success": False}
        return {"success": True, "text": ((reply.json() or {}).get("text") or "").strip()}

    return listen


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
        question = site_sources.glossed(fix_names(doc.question, *names_of(link)))
        lent = passages(link) + site_passages(link, question)
        result = answerer(
            question=question,
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
    known = {p["id"]: p for p in lent}
    sources = [s for s in (result or {}).get("sources") or [] if s in known]
    answer = ((result or {}).get("answer") or "").strip()
    if result and result.get("sure") and answer and sources:
        doc.db_set(
            {
                "status": "Answered by Nora",
                "nora_answer": answer[:2000],
                "nora_sources": json.dumps(kept_sources(sources, known)),
                "nora_reason": "",
                "nora_seconds": round(seconds, 1),
            }
        )
        _refresh_counts(link.name)
        return
    doc.db_set(
        {
            "nora_answer": answer[:2000],
            "nora_sources": json.dumps(kept_sources(sources, known)),
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
                _conversation_html(doc, link, person),
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


def _conversation_html(doc, link, person: str) -> str:
    """What `person` asked on the link before the question `doc`, and what was answered, oldest first: the chat the
    person sees on her page, so that the question forwarded is read with what Nora already said. "" when nothing."""
    rows = frappe.get_all(
        "Presentation Question",
        filters={
            "link": link.name,
            "viewer": doc.viewer,
            "name": ["!=", doc.name],
            "creation": ["<", doc.creation],
        },
        fields=["slide", "question", "status", "nora_answer", "nora_sources", "answer", "answered_by"],
        order_by="creation desc",
        limit=CONVERSATION_IN_MAIL + 1,
    )
    if not rows:
        return ""
    more = len(rows) > CONVERSATION_IN_MAIL
    rows = list(reversed(rows[:CONVERSATION_IN_MAIL]))
    lent = {}
    if any(r.status == "Answered by Nora" for r in rows):
        try:
            lent = {p["id"]: p for p in passages(link)}
        except Exception:
            lent = {}
    quiet = "color:#6b6b6b;font-size:13px"
    before = _("Before this question, {0} asked:").format(person)
    parts = [
        '<hr style="border:none;border-top:1px solid #e5e2dc;margin:26px 0 18px">',
        f"<p><strong>{escape_html(before)}</strong></p>",
    ]
    if more:
        earlier = _("The earlier questions are on the Questions tab.")
        parts.append(f'<p style="{quiet}">{escape_html(earlier)}</p>')
    for r in rows:
        where = _("Slide {0}").format(r.slide) + " · " if r.slide else ""
        parts.append(
            f'<p style="margin:16px 0 4px"><span style="{quiet}">{escape_html(where)}</span>'
            f"<strong>{escape_html(r.question)}</strong></p>"
        )
        if r.status == "Answered by Nora":
            cited = [
                _source_label(lent.get(s) if isinstance(s, str) else s, s) for s in _json_list(r.nora_sources)
            ]
            said, answer = _("Nora answered:"), r.nora_answer
        elif r.status == "Answered":
            cited, said, answer = [], _("{0} answered:").format(get_fullname(r.answered_by)), r.answer
        else:
            cited, said, answer = [], "", ""
        if answer:
            parts.append(
                f'<p style="margin:0 0 2px;white-space:pre-line"><span style="{quiet}">{escape_html(said)}</span> '
                f"{escape_html(answer)}</p>"
            )
            if cited:
                listed = _("Sources: {0}").format(", ".join(cited))
                parts.append(f'<p style="margin:0;{quiet}">{escape_html(listed)}</p>')
        else:
            waiting = _("Waiting for your answer.") if r.status == "Waiting" else _("Not answered yet.")
            parts.append(f'<p style="margin:0;{quiet}">{escape_html(waiting)}</p>')
    return "".join(parts)


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
            item["sources"] = [_source_label(lent.get(s) if isinstance(s, str) else s, s) for s in cited]
            # the slide each source shows, for its chip to turn the deck there (none for a kept answer), and the page
            # of a site, for its chip to open it
            item["slides"] = [_slide_of(lent.get(s)) if isinstance(s, str) else None for s in cited]
            item["links"] = [s.get("url") if isinstance(s, dict) else None for s in cited]
        elif r.status == "Answered":
            item["answer"] = r.answer
            item["by"] = get_fullname(r.answered_by)
        out.append(item)
    return {"ok": True, "questions": out}


def _slide_of(passage: dict | None):
    passage = passage or {}
    return passage.get("slide") if passage.get("kind") not in ("answer", "site") else None


def kept_sources(cited: list[str], known: dict) -> list:
    """What a question keeps of the sources its answer cites: a slide's or a kept answer's id (read again from the
    link), and a site's page as itself (its label and address), since a site's passages change with the question."""
    out, pages = [], set()
    for source in cited:
        passage = known.get(source) or {}
        if passage.get("kind") == "site":
            # two passages of one page are one source
            if passage.get("url") in pages:
                continue
            pages.add(passage.get("url"))
            out.append({"id": source, "label": site_sources.label(passage), "url": passage.get("url")})
        else:
            out.append(source)
    return out


def site_passages(link, question: str) -> list[dict]:
    """The passages of the link's sites that speak of the question (sources.py); none when it names no site."""
    if not (link.get("nora_sites") or "").strip():
        return []
    try:
        return site_sources.search(link, question)
    except Exception:
        frappe.log_error("Presentation question: the sites could not be searched", frappe.get_traceback())
        return []


def _source_label(passage: dict | None, source) -> str:
    if isinstance(source, dict):
        return source.get("label") or source.get("id") or ""
    kind = (passage or {}).get("kind")
    if kind == "site":
        return site_sources.label(passage)
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
        r.sources = [
            _source_label(lent.get(s) if isinstance(s, str) else s, s) for s in _json_list(r.nora_sources)
        ]
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
        "sites": site_sources.describe(link),
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


def trial(link, question: str, slide=None, who: str | None = None) -> dict:
    """What Nora would answer a person of the link, asked by the team on its record (« Try as a visitor ») or in the
    link's preview: the same passages, the same answerer and the same rule (a sure answer that cites a source the
    link lends), and nothing recorded, counted, forwarded or sent. `who` names the daily cap (the user by default;
    the preview has no user of its own)."""
    question = re.sub(r"[ \t]+", " ", (question or "").strip())
    if not MIN_CHARS <= len(question) <= MAX_CHARS:
        frappe.throw(_("A question of {0} to {1} characters, please.").format(MIN_CHARS, MAX_CHARS))
    if not enabled(link):
        return {"sure": False, "reason": "questions_closed"}
    kind = small_talk(question)
    if kind:
        return {
            "sure": True,
            "answer": small_talk_reply(link, kind),
            "sources": [],
            "slides": [],
            "links": [],
            "small_talk": kind,
        }
    answerer = _answerer()
    if (link.questions_mode or MODE_NORA) != MODE_NORA or not answerer:
        return {"sure": False, "reason": "forward_every_question" if answerer else "no_answerer"}
    # the model is called each time: a cap per person and per day, like a visitor's
    if not _count(f"trial:{who or frappe.session.user}", PER_PERSON_A_DAY * 2):
        frappe.throw(_("You have tried many questions today: try again tomorrow."))
    asked = site_sources.glossed(fix_names(question, *names_of(link)))
    lent = passages(link) + site_passages(link, asked)
    slide = min(max(cint(slide), 0), rules.MAX_SLIDES)
    titles = slide_titles(link)
    try:
        result = answerer(
            question=asked,
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
        cited = kept_sources(sources, known)
        return {
            "sure": True,
            "answer": answer,
            "sources": [_source_label(known.get(c) if isinstance(c, str) else c, c) for c in cited],
            "slides": [_slide_of(known.get(c)) if isinstance(c, str) else None for c in cited],
            "links": [c.get("url") if isinstance(c, dict) else None for c in cited],
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

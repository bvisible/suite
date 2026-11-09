# //// Neoffice — added file (no upstream equivalent): the sites Nora also reads to answer a question asked on a shared
# //// presentation (maintenance#2337; Jérémy, 09.11: « toutes les informations du wiki et aussi du site internet »).
# //// A link names them in `nora_sites`, one address per line: the company's website, its public manual. Each is read
# //// from its sitemap — the pages under the address, in the link's language — and kept in a small full-text index on
# //// the site's disk (private/presentation-sources/<hash>.sqlite), read again every day. A question takes the few
# //// passages that speak of it; Nora cites them like a slide, and the visitor's chip opens the page.
# //// A page of prices is never read: a price stays with the person who answers for the link.
from __future__ import annotations

import hashlib
import os
import re
import sqlite3
from urllib.parse import urlparse
from xml.etree import ElementTree

import frappe
from frappe.utils import now_datetime

MAX_PAGES = 600
PAGE_CHARS = 20000
CHUNK_CHARS = 1400
MIN_PAGE_CHARS = 200
FETCH_TIMEOUT_S = 20
PER_SITE = 3
TOP = 6
# The rows of each site the index gives before they are ranked by how much of the question they hold (rank_key).
CANDIDATES = 60
# The pieces of each site closest in meaning to the question (vectors of nora's small embedding model), beside them:
# « travailler avec une monnaie étrangère » finds the manual's page « Multidevises », which no word of it names.
SEMANTIC = 30
# The two rankings (the words, the meaning) are fused by their ranks: 1 / (FUSE_K + rank) each, the meaning weighing
# MEANING_WEIGHT times more (three benches, 64 questions written as clients write them: the right page among the
# passages 59 times at 1.5, 57 at 1, 58 at 2).
FUSE_K = 20
MEANING_WEIGHT = 1.5
EMBED_BATCH = 64
# A first reading of a manual gives its two thousand pieces to the model (about forty minutes): the job that reads a
# link's sites is given the time; a job cut short keeps what it did, the next one goes on.
READ_JOB_TIMEOUT_S = 2 * 3600
# A passage begins with the end of the piece before it on its page: steps that the cut into pieces split (« cliquez sur
# Annuler, puis Oui » in one piece, « Passer à brouillon » in the next) reach the answer whole.
LEAD_CHARS = 600
LANG_PATH = re.compile(r"^/(fr|de|en|it)(/|$)")
PRICE_PAGE = re.compile(r"tarif|prix|pricing|price|preise|prezzi|cout|cost|kosten", re.I)
# A sentence that states an amount of money: the site's pages, a blog article, speak of prices anywhere; the bench of
# 09.11 found « dès 149 francs par mois » in an article on what an ERP costs. Such a sentence never reaches Nora.
PRICE_SENTENCE = re.compile(
    r"(\d[\d'\u2019\u202f .,]*\s*(chf|francs?|fr\.|eur|euros?|€|\$)(?![a-z]))|((chf|fr\.|€|\$)\s*\d)", re.I
)
SKIP_TAGS = (
    "script",
    "style",
    "noscript",
    "nav",
    "header",
    "footer",
    "form",
    "svg",
    "button",
    "template",
    "aside",
)
STOPWORDS = set(
    """
    les des une un le la de du et en est pour que qui dans par sur avec pas plus mais ou ce cette ces son sa ses leur
    leurs vous nous ils elles on il elle je tu se sont aux au comme tout tous toute toutes être avoir fait faire peut
    peuvent quoi quel quelle quels quelles comment combien est-ce estce votre vos notre nos mon ma mes ton ta tes
    dont donc alors aussi bien très sans sous entre chez y a ont été the and for with what how can does depuis
    déjà deja seulement encore nouveau nouvelle nouveaux il elle peut-il peut-on
    """.split()
)


# ---------------------------------------------------------------------------------------------------------------------
# What a link reads
# ---------------------------------------------------------------------------------------------------------------------
def roots_of(link) -> list[str]:
    """The addresses `nora_sites` names, one per line, as https addresses without a trailing slash."""
    out = []
    for line in (link.get("nora_sites") or "").splitlines():
        url = line.strip().rstrip("/")
        if not url:
            continue
        if not re.match(r"^https?://", url, re.I):
            url = "https://" + url
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https") and parsed.netloc and url not in out:
            out.append(url)
    return out[:5]


def language_of(link) -> str:
    return (frappe.db.get_single_value("System Settings", "language") or "fr")[:2]


def state(root: str) -> dict | None:
    """How many pages of `root` are read, and when: None while it was never read."""
    path = index_path(root)
    if not os.path.exists(path):
        return None
    with sqlite3.connect(path) as db:
        pages = db.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
        read_on = db.execute("SELECT value FROM meta WHERE key = 'read_on'").fetchone()
    return {"pages": pages, "read_on": read_on[0] if read_on else None}


def index_path(root: str) -> str:
    folder = frappe.get_site_path("private", "presentation-sources")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, hashlib.sha256(root.encode()).hexdigest()[:24] + ".sqlite")


# ---------------------------------------------------------------------------------------------------------------------
# Reading a site
# ---------------------------------------------------------------------------------------------------------------------
def refresh_link(name: str) -> None:
    """The job: read again the sites a link names (when they change, and from the record's « Read again »)."""
    link = frappe.get_doc("Presentation Link", name)
    for root in roots_of(link):
        refresh(root, language_of(link))


def refresh_all() -> None:
    """Every day: the sites of the links that still open, each read once."""
    seen = set()
    for name in frappe.get_all(
        "Presentation Link",
        filters={"status": ["!=", "Withdrawn"], "nora_sites": ["is", "set"]},
        pluck="name",
    ):
        link = frappe.get_doc("Presentation Link", name)
        for root in roots_of(link):
            if root in seen:
                continue
            seen.add(root)
            try:
                refresh(root, language_of(link))
            except Exception:
                frappe.log_error(f"Presentation sources: {root} could not be read", frappe.get_traceback())


def refresh(root: str, language: str = "fr") -> dict:
    """Reads the pages of `root` from its site's sitemap; a page whose `lastmod` did not move is kept as it was."""
    pages = site_pages(root, language)
    path = index_path(root)
    db = sqlite3.connect(path)
    try:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS pages (url TEXT PRIMARY KEY, lastmod TEXT, title TEXT, text TEXT);
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
                title, body, url UNINDEXED, tokenize = 'unicode61 remove_diacritics 2'
            );
            CREATE TABLE IF NOT EXISTS vectors (id INTEGER PRIMARY KEY, url TEXT, vec BLOB);
            CREATE INDEX IF NOT EXISTS vectors_url ON vectors (url);
            """
        )
        known = {row[0]: row[1] for row in db.execute("SELECT url, lastmod FROM pages")}
        wanted = {url for url, _ in pages}
        for url in set(known) - wanted:
            db.execute("DELETE FROM pages WHERE url = ?", (url,))
            db.execute("DELETE FROM chunks WHERE url = ?", (url,))
            db.execute("DELETE FROM vectors WHERE url = ?", (url,))
        for url, lastmod in pages:
            if url in known and lastmod and known[url] == lastmod:
                continue
            page = read_page(url)
            # most sitemaps date few pages, so a page is read again every day: a piece whose text did not change
            # keeps its vector, only a new piece goes to the model
            kept = {
                (title, body): vec
                for title, body, vec in db.execute(
                    "SELECT chunks.title, chunks.body, vectors.vec FROM vectors "
                    "JOIN chunks ON chunks.rowid = vectors.id WHERE vectors.url = ?",
                    (url,),
                )
            }
            db.execute("DELETE FROM chunks WHERE url = ?", (url,))
            db.execute("DELETE FROM vectors WHERE url = ?", (url,))
            if not page:
                db.execute("DELETE FROM pages WHERE url = ?", (url,))
                continue
            db.execute(
                "INSERT OR REPLACE INTO pages (url, lastmod, title, text) VALUES (?, ?, ?, ?)",
                (url, lastmod or "", page["title"], page["text"]),
            )
            for body in chunks(page["text"]):
                cursor = db.execute(
                    "INSERT INTO chunks (title, body, url) VALUES (?, ?, ?)", (page["title"], body, url)
                )
                if (page["title"], body) in kept:
                    db.execute(
                        "INSERT OR REPLACE INTO vectors (id, url, vec) VALUES (?, ?, ?)",
                        (cursor.lastrowid, url, kept[(page["title"], body)]),
                    )
        db.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('read_on', ?)", (str(now_datetime())[:16],)
        )
        db.commit()
        embed_missing(db)
    finally:
        db.close()
    return state(root) or {}


def _embedder():
    """The function that turns texts into vectors of meaning (nora's hook `presentation_embedder`), or None."""
    hooks = frappe.get_hooks("presentation_embedder")
    return frappe.get_attr(hooks[-1]) if hooks else None


def _pack(vector) -> bytes:
    import numpy

    array = numpy.asarray(vector, dtype=numpy.float32)
    norm = float(numpy.linalg.norm(array)) or 1.0
    return (array / norm).astype(numpy.float32).tobytes()


def embed_missing(db) -> int:
    """Gives each piece of the site that has none its vector of meaning; a piece gone takes its vector with it. 0 when
    there is no embedder, when it declines (a counted plan) or does not answer: the search keeps its words."""
    db.execute("DELETE FROM vectors WHERE id NOT IN (SELECT rowid FROM chunks)")
    db.commit()
    embedder = _embedder()
    if not embedder:
        return 0
    rows = db.execute(
        "SELECT rowid, url, title, body FROM chunks WHERE rowid NOT IN (SELECT id FROM vectors)"
    ).fetchall()
    done = 0
    for start in range(0, len(rows), EMBED_BATCH):
        batch = rows[start : start + EMBED_BATCH]
        try:
            vectors = embedder([f"{title}\n{body}" for _rowid, _url, title, body in batch])
        except Exception:
            frappe.log_error("Presentation sites: the vectors of meaning failed", frappe.get_traceback())
            break
        if not vectors or len(vectors) != len(batch):
            break
        for (rowid, url, _title, _body), vector in zip(batch, vectors, strict=True):
            db.execute(
                "INSERT OR REPLACE INTO vectors (id, url, vec) VALUES (?, ?, ?)", (rowid, url, _pack(vector))
            )
        db.commit()
        done += len(batch)
    return done


def site_pages(root: str, language: str = "fr") -> list[tuple[str, str]]:
    """(url, lastmod) of the pages of the sitemap under `root`, in `language` when the site has one per language, no
    page of prices, `MAX_PAGES` at most."""
    parsed = urlparse(root)
    base = f"{parsed.scheme}://{parsed.netloc}"
    prefix = parsed.path.rstrip("/")
    found = _sitemap(f"{base}/sitemap.xml", depth=0)
    by_language = any(LANG_PATH.match(urlparse(url).path) for url, _ in found)
    out, seen = [], set()
    for url, lastmod in found:
        path = urlparse(url).path.rstrip("/")
        if _host(url) != _host(root) or not (path == prefix or path.startswith(prefix + "/")):
            continue
        language_part = LANG_PATH.match(path or "/")
        if by_language and not prefix and (not language_part or language_part.group(1) != language):
            continue
        if PRICE_PAGE.search(path) or url in seen:
            continue
        seen.add(url)
        out.append((url, lastmod))
    return out[:MAX_PAGES]


def _sitemap(url: str, depth: int) -> list[tuple[str, str]]:
    try:
        reply = _get(url)
        tree = ElementTree.fromstring(reply.content)
    except Exception:
        return []
    out = []
    for node in tree:
        tag = node.tag.rsplit("}", 1)[-1]
        loc = next((child.text for child in node if child.tag.endswith("loc")), None)
        lastmod = next((child.text for child in node if child.tag.endswith("lastmod")), None) or ""
        if not loc:
            continue
        if tag == "sitemap" and depth < 2:
            out.extend(_sitemap(loc.strip(), depth + 1))
        elif tag == "url":
            out.append((loc.strip(), lastmod.strip()))
    return out


def read_page(url: str) -> dict | None:
    """The title and the readable text of a page: its article (a wiki page's `#wiki-content`, else `main`), without
    its menus, headers and footers."""
    from bs4 import BeautifulSoup

    try:
        reply = _get(url)
    except Exception:
        return None
    if reply.status_code != 200 or "html" not in reply.headers.get("Content-Type", ""):
        return None
    soup = BeautifulSoup(reply.text, "html.parser")
    title = ""
    meta = soup.find("meta", attrs={"property": "og:title"})
    if meta and meta.get("content"):
        title = meta["content"]
    elif soup.title and soup.title.string:
        title = soup.title.string
    title = re.split(r"\s+[\u2014|\u2013-]\s+", title.strip())[0][:140]
    body = soup.select_one("#wiki-content") or soup.find("main") or soup.find("article") or soup.body
    if not body:
        return None
    for tag in body.find_all(SKIP_TAGS):
        tag.decompose()
    text = re.sub(r"\s+", " ", body.get_text(" ")).strip()
    if len(text) < MIN_PAGE_CHARS:
        return None
    return {"title": title or url, "text": text[:PAGE_CHARS]}


def chunks(text: str) -> list[str]:
    """Pieces of about `CHUNK_CHARS`, cut at a sentence."""
    out, current = [], ""
    for sentence in re.split(r"(?<=[.!?:;])\s+", text):
        if current and len(current) + len(sentence) > CHUNK_CHARS:
            out.append(current.strip())
            current = ""
        current += sentence + " "
    if current.strip():
        out.append(current.strip())
    return out


def _host(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _get(url: str):
    import requests

    return requests.get(
        url,
        timeout=FETCH_TIMEOUT_S,
        headers={"User-Agent": "Neoffice presentation reader (+https://neoffice.ch)"},
    )


# ---------------------------------------------------------------------------------------------------------------------
# What a question takes
# ---------------------------------------------------------------------------------------------------------------------
def search(link, question: str) -> list[dict]:
    """The passages of the link's sites that speak of `question` (`W<n>`), each with its page's address: the pieces
    whose words hold the question (rank_key) and the pieces closest to it in meaning, fused by their ranks; a page
    takes one place, a site `PER_SITE`, all of them `TOP`."""
    query = fts_query(question)
    if not query:
        return []
    terms = question_terms(question)
    paths = [(root, index_path(root)) for root in roots_of(link)]
    paths = [(root, path) for root, path in paths if os.path.exists(path)]
    vector = _question_vector(question) if any(_has_vectors(path) for _root, path in paths) else None
    candidates = []
    for root, path in paths:
        try:
            with sqlite3.connect(path) as db:
                rows = db.execute(
                    "SELECT rowid, url, title, body, bm25(chunks, 4.0, 1.0) AS score FROM chunks "
                    "WHERE chunks MATCH ? ORDER BY score LIMIT ?",
                    (query, CANDIDATES),
                ).fetchall()
                weights = term_weights(db, terms)
                closeness = _closeness(db, vector)
                close = sorted(closeness, key=closeness.get, reverse=True)[:SEMANTIC]
                have = {row[0] for row in rows}
                extra = [rowid for rowid in close if rowid not in have]
                if extra:
                    marks = ",".join("?" * len(extra))
                    rows += db.execute(
                        f"SELECT rowid, url, title, body, 0.0 FROM chunks WHERE rowid IN ({marks})", extra
                    ).fetchall()
        except sqlite3.Error:
            continue
        for rowid, url, title, body, score in rows:
            candidates.append(
                {
                    "root": root,
                    "path": path,
                    "rowid": rowid,
                    "url": url,
                    "title": title,
                    "body": body,
                    "key": rank_key(terms, weights, title, body, score),
                    "close": closeness.get(rowid),
                }
            )
    by_words = sorted(range(len(candidates)), key=lambda i: candidates[i]["key"])
    by_meaning = sorted(
        (i for i, c in enumerate(candidates) if c["close"] is not None), key=lambda i: -candidates[i]["close"]
    )
    fused = {i: 1 / (FUSE_K + rank) for rank, i in enumerate(by_words)}
    for rank, i in enumerate(by_meaning):
        fused[i] += MEANING_WEIGHT / (FUSE_K + rank)
    out, seen, per_site = [], set(), {}
    for i in sorted(fused, key=fused.get, reverse=True):
        c = candidates[i]
        body = without_prices(c["body"])
        if c["url"] in seen or per_site.get(c["root"], 0) >= PER_SITE or len(body) < MIN_PAGE_CHARS / 2:
            continue
        seen.add(c["url"])
        per_site[c["root"]] = per_site.get(c["root"], 0) + 1
        lead = _lead(c["path"], c["url"], c["rowid"])
        site = urlparse(c["root"]).netloc.removeprefix("www.")
        out.append(
            {
                "id": f"W{len(out) + 1}",
                "kind": "site",
                "url": c["url"],
                "site": site,
                "page": c["title"],
                "title": f"page of the website {site}: {c['title']}",
                "text": f"… {without_prices(lead)} {body}" if lead else body,
            }
        )
        if len(out) >= TOP:
            break
    return out


def _lead(path: str, url: str, rowid: int) -> str:
    """The end of the piece before `rowid` on its page, from a sentence (`LEAD_CHARS` at most), or ""."""
    try:
        with sqlite3.connect(path) as db:
            row = db.execute(
                "SELECT body FROM chunks WHERE url = ? AND rowid < ? ORDER BY rowid DESC LIMIT 1",
                (url, rowid),
            ).fetchone()
    except sqlite3.Error:
        return ""
    if not row:
        return ""
    tail = row[0][-LEAD_CHARS:]
    if len(row[0]) > LEAD_CHARS:
        cut = re.search(r"(?<=[.!?:;])\s+", tail)
        tail = tail[cut.end() :] if cut else ""
    return tail.strip()


def _has_vectors(path: str) -> bool:
    try:
        with sqlite3.connect(path) as db:
            return bool(db.execute("SELECT 1 FROM vectors LIMIT 1").fetchone())
    except sqlite3.Error:
        return False


def _question_vector(question: str):
    """The question's vector of meaning, or None (no embedder, or no answer in time: the search keeps its words)."""
    import numpy

    embedder = _embedder()
    if not embedder:
        return None
    try:
        vectors = embedder([question], query=True)
    except Exception:
        frappe.log_error("Presentation sites: the question's vector failed", frappe.get_traceback())
        return None
    if not vectors:
        return None
    return numpy.frombuffer(_pack(vectors[0]), dtype=numpy.float32)


def _closeness(db, vector) -> dict[int, float]:
    """The cosine of each piece of a site with the question's vector (both are kept normalized)."""
    import numpy

    if vector is None:
        return {}
    try:
        rows = db.execute("SELECT id, vec FROM vectors").fetchall()
    except sqlite3.Error:
        return {}
    rows = [row for row in rows if len(row[1]) == vector.nbytes]
    if not rows:
        return {}
    matrix = numpy.frombuffer(b"".join(row[1] for row in rows), dtype=numpy.float32).reshape(len(rows), -1)
    scores = matrix @ vector
    return {rows[i][0]: float(scores[i]) for i in range(len(rows))}


def without_prices(text: str) -> str:
    """The passage without its sentences that state an amount: a price stays with the person who answers."""
    return " ".join(
        s for s in re.split(r"(?<=[.!?:;])\s+", text or "") if not PRICE_SENTENCE.search(s)
    ).strip()


def fts_query(question: str) -> str:
    """The words of the question that carry its meaning, any of them, each by its stem (« écritures » finds
    « écriture », « valide » finds « valider » and « validation »), with the word the manual uses for a word the
    client says (EQUIVALENTS)."""
    tokens = []
    for group in question_terms(question):
        for stem in group:
            token = '"' + stem.replace('"', "") + '"' + ("*" if len(stem) >= 4 else "")
            if token not in tokens:
                tokens.append(token)
    return " OR ".join(tokens[:16])


# The word a client says, and the word the manual and the sites use for it (by their stems). Only true equivalents of
# the trade: a quotation is « devis » in the software and « offre » in a client's mouth.
EQUIVALENTS = {
    "offre": ["devis"],
    "produit": ["article"],
    "ajouter": ["creer"],
    "rappel": ["relance"],
    "rappeler": ["relance"],
    "manuel": ["journal"],
    "manuelle": ["journal"],
    "fournisseur": ["achat"],
    "euro": ["devise"],
    "amortir": ["immobilisation"],
    "amortissement": ["immobilisation"],
}
# A phrase of the client that the software names in a word.
PHRASES = {"mise en page": ["impression"]}


def glossed(question: str) -> str:
    """The question with the software's word beside a client's word, for the answerer, which reads words literally:
    « Comment faire une offre ? » found the page « Créer un devis » and still said it did not know (09.11)."""
    pairs = []
    lower = (question or "").lower()
    for word in re.findall(r"[\w'-]+", lower):
        word = word.split("'")[-1].strip("-")
        for target in EQUIVALENTS.get(_plain(word), []):
            pair = f"{word} = {target}"
            if pair not in pairs:
                pairs.append(pair)
    for phrase, words in PHRASES.items():
        if phrase in _plain(lower):
            pairs.append(f"{phrase} = {', '.join(words)}")
    return f"{question} ({'; '.join(pairs)})" if pairs else question


def question_terms(question: str) -> list[list[str]]:
    """The meaningful words of the question, each as the stems that may stand for it (its own, then its equivalents)."""
    text = (question or "").lower()
    groups: list[list[str]] = []
    for word in re.findall(r"[\w'-]+", text):
        word = word.split("'")[-1].strip("-")
        if len(word) < 3 or word in STOPWORDS or word.isdigit():
            continue
        stem = stem_of(word)
        group = [stem, *(stem_of(w) for w in EQUIVALENTS.get(_plain(word), EQUIVALENTS.get(stem, [])))]
        if not any(stem in g for g in groups):
            groups.append(list(dict.fromkeys(group)))
    for phrase, words in PHRASES.items():
        if phrase in _plain(text):
            groups.append([stem_of(w) for w in words])
    return groups


def covers(terms: list[list[str]], text: str, weights: list[float] | None = None) -> float:
    """How much of the question `text` holds: its words found (by any of their stems), each by its weight."""
    words = set(re.findall(r"[a-z0-9]+", _plain((text or "").lower())))
    held = 0.0
    for number, group in enumerate(terms):
        if any(any(w.startswith(stem) if len(stem) >= 4 else w == stem for w in words) for stem in group):
            held += weights[number] if weights else 1
    return held


def term_weights(db, terms: list[list[str]]) -> list[float]:
    """How rare each word of the question is in a site (log N/df): « relancer » says more than « facture », which
    nearly every page of a manual holds."""
    import math

    total = db.execute("SELECT count(*) FROM chunks").fetchone()[0] or 1
    weights = []
    for group in terms:
        rarest = 0.0
        for stem in group:
            token = '"' + stem.replace('"', "") + '"' + ("*" if len(stem) >= 4 else "")
            try:
                df = db.execute("SELECT count(*) FROM chunks WHERE chunks MATCH ?", (token,)).fetchone()[0]
            except sqlite3.Error:
                df = total
            rarest = max(rarest, math.log((total + 1) / (df + 1)))
        weights.append(rarest)
    return weights


def rank_key(terms: list[list[str]], weights: list[float], title: str, body: str, score: float) -> tuple:
    """First the pages whose title holds the most of the question (its rare words weigh more), then whose text does,
    then the index's own score: « Valider, imprimer (QR) et envoyer une facture » comes before the many pages that
    only say « facture »."""
    return (-round(covers(terms, title, weights), 3), -round(covers(terms, body, weights), 3), score)


# The endings a French word takes, longest first: what is left is the stem the index is searched by. The index forgets
# the accents (unicode61 remove_diacritics), so the stem does too. A question said « valide une facture » missed
# « Valider, imprimer (QR) et envoyer une facture » of the manual: « valide » was searched as a whole word (09.11).
_ENDINGS = tuple(
    sorted(
        """issements issement ations ation ements ement ateurs atrices ateur atrice ances ance ences ence ables able
        ibles ible eurs euses euse eur ions ees ee es e s x er ir re ez ent ons ais ait""".split(),
        key=len,
        reverse=True,
    )
)


def _plain(word: str) -> str:
    import unicodedata

    return unicodedata.normalize("NFKD", word).encode("ascii", "ignore").decode()


def stem_of(word: str) -> str:
    """The stem of a word of five letters or more, never shorter than four letters; a shorter word as it is."""
    plain = _plain(word.lower())
    if len(plain) < 5:
        return plain
    for ending in _ENDINGS:
        if plain.endswith(ending) and len(plain) - len(ending) >= 4:
            return plain[: -len(ending)]
    return plain


def label(passage: dict) -> str:
    """The chip of a site's passage on the visitor's page: the site and the page."""
    page = passage.get("page") or ""
    return f"{passage.get('site')} · {page[:48]}{'…' if len(page) > 48 else ''}"


def describe(link) -> list[dict]:
    """For the record: each site, its pages read and when."""
    return [{"url": root, **(state(root) or {"pages": 0, "read_on": None})} for root in roots_of(link)]

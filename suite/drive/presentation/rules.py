# //// Neoffice — added file (no upstream equivalent): the rules of a shared presentation, kept apart from the web
# //// methods so they can be tested without a request: who may enter, the code sent by e-mail, the files a link
# //// may serve, and how a visit's heartbeat adds up.
from __future__ import annotations

import hashlib
import re
import secrets

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime

from suite.drive.utils import STATUS_ACTIVE

TOKEN_RE = re.compile(r"[A-Za-z0-9_-]{16,64}")
DOMAIN_RE = re.compile(r"(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}")
ENTRY_NAMES = ("index.html", "index.htm")

CODE_SECONDS = 600
CODE_ATTEMPTS = 5
VISIT_HOURS = 12
REMEMBER_DAYS = 30
# A heartbeat comes every 15 s; anything above this per beat is not time a person spent looking.
MAX_BEAT_SECONDS = 30
MAX_SLIDES = 500
MAX_VIDEOS = 20
# A slide counts as seen past this many seconds: a slide skipped through with the arrow key is not.
SEEN_SECONDS = 2


def new_secret(nbytes: int = 24) -> str:
    return secrets.token_urlsafe(nbytes)


def hash_secret(secret: str) -> str:
    """What is stored of a secret handed to a browser: its SHA-256 (the secret is random, a fast hash is enough)."""
    return hashlib.sha256((secret or "").encode()).hexdigest()


def _lines(text: str | None) -> list[str]:
    return [line.strip() for line in re.split(r"[\n,;]+", text or "") if line.strip()]


def normalize_email(email: str | None) -> str:
    """The address in lower case, or "" when it is not an address."""
    email = (email or "").strip().lower()
    if not email or len(email) > 254 or not frappe.utils.validate_email_address(email):
        return ""
    return email


def normalize_domains(text: str | None) -> list[str]:
    """`example.com` from `example.com`, `@example.com` or `someone@example.com`; anything else is dropped."""
    domains = []
    for line in _lines(text):
        domain = line.lower().rsplit("@", 1)[-1].strip(". ")
        if DOMAIN_RE.fullmatch(domain) and domain not in domains:
            domains.append(domain)
    return domains


def normalize_emails(text: str | None) -> list[str]:
    emails = []
    for line in _lines(text):
        email = normalize_email(line)
        if email and email not in emails:
            emails.append(email)
    return emails


def is_open(link) -> bool:
    """A link opens unless it was withdrawn or its date has passed."""
    if link.status == "Withdrawn":
        return False
    return not (link.expires_on and get_datetime(link.expires_on) < now_datetime())


def email_accepted(link, email: str) -> bool:
    """Whether `email` may ask for a code: its domain is accepted, the address is, the link was sent to it, or a
    person who had entered forwarded the presentation to it."""
    email = normalize_email(email)
    if not email:
        return False
    if email.rsplit("@", 1)[-1] in normalize_domains(link.allowed_domains):
        return True
    if email in normalize_emails(link.allowed_emails) or email in normalize_emails(link.recipients):
        return True
    return bool(frappe.db.exists("Presentation Viewer", {"link": link.name, "email": email}))


def entry_file(presentation: str) -> tuple[str, dict]:
    """The folder a presentation is served from and its entry file: the `index.html` of a Drive folder, or an HTML file
    and the folder it sits in."""
    file = frappe.db.get_value(
        "File", presentation, ["name", "file_name", "is_folder", "folder", "status"], as_dict=True
    )
    if not file or file.get("status", STATUS_ACTIVE) != STATUS_ACTIVE:
        frappe.throw(frappe._("This presentation is not in the Drive any more."), frappe.DoesNotExistError)
    if file.is_folder:
        for name in ENTRY_NAMES:
            entry = _child(file.name, name, is_folder=False)
            if entry:
                return file.name, entry
        frappe.throw(frappe._("The folder has no index.html: it is not a web presentation."))
    if not (file.file_name or "").lower().endswith((".html", ".htm")):
        frappe.throw(frappe._("Choose a folder that holds an index.html, or an HTML file."))
    return file.folder, file


def _child(parent: str, name: str, is_folder: bool) -> dict | None:
    """The live file or folder called `name` in the folder `parent`."""
    rows = frappe.get_all(
        "File",
        filters={"folder": parent, "file_name": name},
        fields=["name", "file_name", "file_url", "is_folder", "is_private", "file_size", "status"],
        limit=5,
    )
    for row in rows:
        if row.get("status", STATUS_ACTIVE) == STATUS_ACTIVE and bool(row.is_folder) == is_folder:
            return row
    return None


def resolve(folder: str, path: str) -> dict | None:
    """The file at `path` (`img/cover.png`) under `folder`, or None. A path never climbs out of the folder: an empty
    segment, `.` or `..` resolves to nothing."""
    segments = (path or "").split("/")
    if not segments or any(seg in ("", ".", "..") or "\\" in seg for seg in segments):
        return None
    current = folder
    for seg in segments[:-1]:
        row = _child(current, seg, is_folder=True)
        if not row:
            return None
        current = row.name
    return _child(current, segments[-1], is_folder=False)


def _code_key(link_name: str, email: str) -> str:
    return f"presentation_code:{link_name}:{hash_secret(email)}"


def issue_code(link_name: str, email: str, first_name: str | None = None) -> str:
    """A six-digit code for `email` on this link, valid ten minutes; the first name waits with it."""
    code = f"{secrets.randbelow(10**6):06d}"
    frappe.cache.set_value(
        _code_key(link_name, email),
        {"hash": hash_secret(f"{link_name}:{email}:{code}"), "attempts": 0, "first_name": first_name or ""},
        expires_in_sec=CODE_SECONDS,
    )
    return code


def take_code(link_name: str, email: str, code: str) -> dict | None:
    """The waiting request when `code` is right (it is then used up), else None. Five wrong codes use it up too."""
    key = _code_key(link_name, email)
    data = frappe.cache.get_value(key)
    if not data:
        return None
    if secrets.compare_digest(data["hash"], hash_secret(f"{link_name}:{email}:{(code or '').strip()}")):
        frappe.cache.delete_value(key)
        return data
    data["attempts"] += 1
    if data["attempts"] >= CODE_ATTEMPTS:
        frappe.cache.delete_value(key)
    else:
        frappe.cache.set_value(key, data, expires_in_sec=CODE_SECONDS)
    return None


def visit_expiry():
    return add_to_date(now_datetime(), hours=-VISIT_HOURS)


def remember_until():
    return add_to_date(now_datetime(), days=REMEMBER_DAYS)


def device_of(user_agent: str | None) -> str:
    agent = (user_agent or "").lower()
    if "ipad" in agent or "tablet" in agent or ("android" in agent and "mobile" not in agent):
        return "Tablet"
    if "mobi" in agent or "iphone" in agent or "android" in agent:
        return "Phone"
    return "Computer"


def merge_beat(slides: dict | None, videos: dict | None, beat: dict | None) -> dict:
    """A heartbeat added to a visit. `beat` is what the page sends: `seconds` per slide number since the last beat,
    the `slide` on screen, the `total` number of slides, and how far each video went (`videos`, in percent).
    Returns the new `slides` and `videos`, the `added` seconds, the `furthest` slide and the `total`."""
    slides = {str(k): float(v) for k, v in (slides or {}).items()}
    videos = {str(k): int(v) for k, v in (videos or {}).items()}
    beat = beat if isinstance(beat, dict) else {}

    added = 0.0
    seconds = beat.get("seconds") if isinstance(beat.get("seconds"), dict) else {}
    for key, value in seconds.items():
        index = _int(key)
        spent = _float(value)
        if not (1 <= index <= MAX_SLIDES) or spent <= 0:
            continue
        spent = min(spent, MAX_BEAT_SECONDS - added)
        if spent <= 0:
            break
        slides[str(index)] = round(slides.get(str(index), 0.0) + spent, 1)
        added += spent

    reported = beat.get("videos") if isinstance(beat.get("videos"), dict) else {}
    for source, percent in reported.items():
        source = str(source)[:200]
        if source not in videos and len(videos) >= MAX_VIDEOS:
            continue
        videos[source] = max(videos.get(source, 0), min(max(_int(percent), 0), 100))

    total = min(max(_int(beat.get("total")), 0), MAX_SLIDES)
    on_screen = min(max(_int(beat.get("slide")), 0), MAX_SLIDES)
    furthest = max([on_screen, *(int(k) for k, v in slides.items() if v > 0)], default=0)
    return {
        "slides": slides,
        "videos": videos,
        "added": round(added, 1),
        "furthest": furthest,
        "total": total,
    }


def slides_seen(slides: dict | None) -> int:
    return sum(1 for value in (slides or {}).values() if float(value) >= SEEN_SECONDS)


def _int(value) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _float(value) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if number == number else 0.0  # NaN is not a time

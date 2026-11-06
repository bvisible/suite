"""Request logging for the WebDAV dispatcher.

On by default at "info" — one line per request in logs/suite.drive.webdav.log
at both the bench and site level. drive_webdav_log_level in site_config.json
tunes it: "error" (5xx only), "warning" (adds 4xx), "debug" (adds the protocol
headers that matter when reproducing client behavior) or "off". Unrecognized
values keep the default rather than silently going dark. Credentials are never
logged: the Authorization header is deliberately excluded, and lock tokens are
capabilities only in the hands of their owner.
"""

# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations

import logging
import time

import frappe
from werkzeug.wrappers import Request, Response

LOGGER_MODULE = "suite.drive.webdav"
DEFAULT_LEVEL = logging.INFO

LEVELS = {
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}

# headers worth having when debugging a client; Authorization deliberately absent
DEBUG_HEADERS = (
    "User-Agent",
    "Depth",
    "Destination",
    "Overwrite",
    "If",
    "If-Match",
    "If-None-Match",
    "Lock-Token",
    "Timeout",
    "Range",
    "Content-Type",
    "Content-Length",
    "X-OC-Mtime",
    "Expect",
)


# //// Neoffice — added (neoffice-maintenance#2296): the path, the client name, the note and the headers come from
# //// the request, and a line break in them wrote a line of the caller's choosing into the log. Every character
# //// that is not printable is written as its escape (a newline as \n), so one request stays one line.
def _one_line(value) -> str:
    text = str(value)
    if text.isprintable():
        return text
    return "".join(ch if ch.isprintable() else ch.encode("unicode_escape").decode("ascii") for ch in text)


def configured_level() -> int | None:
    raw = str(frappe.conf.get("drive_webdav_log_level") or "").strip().lower()
    if raw == "off":
        return None
    return LEVELS.get(raw, DEFAULT_LEVEL)


def start_request(request: Request) -> None:
    level = configured_level()
    frappe.local._webdav_log = (
        None if level is None else {"level": level, "start": time.monotonic(), "user": None, "note": None}
    )


def note_user(user: str) -> None:
    if context := getattr(frappe.local, "_webdav_log", None):
        context["user"] = user


def note(reason: str) -> None:
    if context := getattr(frappe.local, "_webdav_log", None):
        context["note"] = reason


def log_response(request: Request, response: Response) -> None:
    context = getattr(frappe.local, "_webdav_log", None)
    if not context:
        return

    logger = frappe.logger(LOGGER_MODULE, file_count=10)
    logger.setLevel(context["level"])

    status = response.status_code
    duration_ms = (time.monotonic() - context["start"]) * 1000
    client = _one_line((request.user_agent.string or "-")[:120])  # //// Neoffice — see _one_line
    ip = getattr(frappe.local, "request_ip", None) or request.remote_addr or "-"

    # //// Neoffice — see _one_line
    line = (
        f"{_one_line(request.method)} {_one_line(request.path)} -> {status} {duration_ms:.1f}ms "
        f'user={_one_line(context["user"] or "-")} ip={_one_line(ip)} client="{client}"'
    )
    if context["note"]:
        line += f' note="{_one_line(context["note"])}"'  # //// Neoffice — see _one_line

    level = logging.ERROR if status >= 500 else logging.WARNING if status >= 400 else logging.INFO
    logger.log(level, line)

    if context["level"] <= logging.DEBUG:
        # //// Neoffice — see _one_line
        headers = "; ".join(
            f"{name}: {_one_line(value)}" for name in DEBUG_HEADERS if (value := request.headers.get(name))
        )
        if headers:
            # //// Neoffice — see _one_line
            logger.debug(f"{_one_line(request.method)} {_one_line(request.path)} headers: {headers}")

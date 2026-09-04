# //// Neoffice: new file — Collabora/WOPI port (from drive_wopi), maintained by Neoffice ////
"""Collabora discovery client.

Fetches editor URLs from Collabora's discovery endpoint and builds the
editor configuration for a native File document. Ported from the Neoffice
`drive_wopi` app.
"""

from __future__ import annotations

import urllib.parse
from xml.etree import ElementTree

import frappe
import requests
from frappe import _
from frappe.rate_limiter import rate_limit

from .lifecycle import (
    _can_connect_socket,
    _record_activity,
    ensure_running as ensure_collabora_running,
)
from .token import generate_wopi_token, get_wopi_settings

# Cache discovery XML (revalidated against the live socket on every hit)
DISCOVERY_CACHE_KEY = "collabora_discovery_xml"

#//// Neoffice — budget for the endpoints that may run `systemctl start coolwsd`.
#//// One editor open costs one call to get_editor_config and, while the daemon is
#//// cold, up to MAX_PROBES (6) calls to can_edit_file — MSOfficePreview.vue polls
#//// every 2.5 s and the user can press "Try again" once more. EDITOR_PROBE_RATE is
#//// sized for that budget; EDITOR_OPEN_RATE is the one-call-per-document path.
EDITOR_OPEN_RATE = {"limit": 10, "seconds": 60}
EDITOR_PROBE_RATE = {"limit": 20, "seconds": 60}

EXTENSION_MIME_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "ppt": "application/vnd.ms-powerpoint",
    "odt": "application/vnd.oasis.opendocument.text",
    "ods": "application/vnd.oasis.opendocument.spreadsheet",
    "odp": "application/vnd.oasis.opendocument.presentation",
    "txt": "text/plain",
    "csv": "text/csv",
}


def get_collabora_url() -> str:
    """Get the Collabora server URL.

    If collabora_server_url is not set in WOPI Settings, returns the current
    site URL (assumes Collabora is proxied via nginx on the same domain).
    """
    settings = get_wopi_settings()
    custom_url = settings.get("collabora_server_url")

    if custom_url:
        return custom_url.rstrip("/")

    return frappe.utils.get_url().rstrip("/")


def is_wopi_enabled() -> bool:
    """Check if WOPI is enabled in settings."""
    settings = get_wopi_settings()
    return bool(settings.get("enabled", False))


#//// Neoffice — `start_if_down` gates the side effect; it used to be unconditional.
#//// Every caller of this function, including the status probe that was reachable
#//// WITHOUT A SESSION, ran `sudo -n systemctl start coolwsd` and then blocked in a
#//// web worker for up to COLLABORA_START_TIMEOUT_SECONDS (20 s) waiting for the
#//// daemon: a handful of parallel requests was enough to hold every worker of the
#//// site. Waking the daemon now belongs to the paths that carry real editing intent
#//// (editor.can_edit_file, get_editor_config), and those are rate limited. Default
#//// False so a new caller has to ASK for the side effect instead of inheriting it.
def get_discovery_xml(start_if_down: bool = False) -> ElementTree.Element | None:
    """Fetch and parse Collabora discovery XML (endpoint: /hosting/discovery).

    Lazy-start contract: this function is the only entry point for the
    discovery XML, so the on-demand lifecycle of coolwsd hangs on it. Even on
    a cache hit we verify the TCP socket — the cached URLs point at
    /browser/<id>/cool.html which 404s the second the daemon is down.

    With ``start_if_down`` false the call is read-only: it reports the daemon as
    unavailable rather than starting it, and does not stamp the activity key that
    keeps the idle watchdog off.
    """
    if not is_wopi_enabled():
        return None

    cached = frappe.cache().get_value(DISCOVERY_CACHE_KEY)
    if cached and _can_connect_socket():
        # Hot path: stamp activity so the idle watchdog backs off.
        try:
            xml = ElementTree.fromstring(cached)
        except ElementTree.ParseError:
            xml = None
        if xml is not None:
            #//// Neoffice — only a caller that would have STARTED the daemon may keep
            #//// it alive. A read-only status probe must not extend the idle window of
            #//// a ~400 MB daemon nobody is editing with.
            if start_if_down:
                _record_activity()
            return xml

    # Cold path: either no cache or coolwsd is down.
    #//// Neoffice — what a read-only caller may NOT do is `systemctl start coolwsd`.
    #//// Fetching the discovery XML from a daemon that is already listening is fine,
    #//// and it has to stay allowed: the cache is a Redis key, so it is empty after
    #//// every flush and every deploy, and refusing to read a running daemon would
    #//// report "Collabora unreachable" on an instance where it is plainly up.
    if start_if_down:
        if not ensure_collabora_running():
            return None
    elif not _can_connect_socket():
        return None

    url = f"{get_collabora_url()}/hosting/discovery"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        frappe.cache().set_value(DISCOVERY_CACHE_KEY, response.content)
        return ElementTree.fromstring(response.content)
    except requests.RequestException as e:
        frappe.log_error("Collabora Discovery Error", f"Failed to fetch discovery from {url}: {e}")
        return None
    except ElementTree.ParseError as e:
        frappe.log_error("Collabora Discovery Parse Error", f"Failed to parse discovery XML: {e}")
        return None


#//// Neoffice — `start_if_down` threaded through: see get_discovery_xml above.
def get_editor_url_for_extension(extension: str, start_if_down: bool = False) -> str | None:
    """Get the Collabora editor URL template for a file extension."""
    discovery = get_discovery_xml(start_if_down=start_if_down)
    if discovery is None:
        return None

    ext = extension.lower().lstrip(".")
    mime_type = EXTENSION_MIME_TYPES.get(ext)
    if not mime_type:
        return None

    for app in discovery.findall(".//app"):
        if app.get("name", "") == mime_type:
            for action in app.findall("action"):
                if action.get("name") == "edit":
                    return action.get("urlsrc")

    # Fallback: search by extension directly
    for app in discovery.findall(".//app"):
        for action in app.findall("action"):
            if action.get("ext") == ext and action.get("name") == "edit":
                return action.get("urlsrc")

    return None


#//// Neoffice — `start_if_down` threaded through: see get_discovery_xml above.
def is_file_supported(filename: str, start_if_down: bool = False) -> bool:
    """Check if a file type is supported by Collabora."""
    if not filename or "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[-1].lower()
    return get_editor_url_for_extension(extension, start_if_down=start_if_down) is not None


#//// Neoffice — rate limited: this is the editor-open path, so it is one of the two
#//// endpoints allowed to run `systemctl start coolwsd`. One call per document open,
#//// so EDITOR_OPEN_RATE (10/min) leaves ample headroom for a human and none for a
#//// loop. `allow_guest` is kept — a publicly shared Drive document opens without a
#//// session — and the read/write permission check below is what gates it.
@frappe.whitelist(allow_guest=True)
@rate_limit(limit=EDITOR_OPEN_RATE["limit"], seconds=EDITOR_OPEN_RATE["seconds"])
def get_editor_config(file_id: str) -> dict:
    """Build the editor configuration (URL + WOPI token) for a File."""
    if not is_wopi_enabled():
        frappe.throw(_("WOPI/Collabora is not enabled"))

    if not frappe.db.exists("File", file_id):
        frappe.throw(_("File not found"), frappe.DoesNotExistError)

    file = frappe.get_doc("File", file_id)

    from suite.drive.api.permissions import user_has_permission

    if not user_has_permission(file, "read"):
        frappe.throw(_("You don't have permission to access this file"), frappe.PermissionError)

    can_write = bool(user_has_permission(file, "write"))

    file_name = file.file_name or ""
    if "." not in file_name:
        frappe.throw(_("Cannot determine file type"))

    extension = file_name.rsplit(".", 1)[-1]

    #//// Neoffice — the one call that may wake coolwsd: the user has asked for the
    #//// editor and holds read access on the document.
    editor_url = get_editor_url_for_extension(extension, start_if_down=True)
    if not editor_url:
        frappe.throw(_("File type not supported: {0}").format(extension))

    token_data = generate_wopi_token(file_id, can_write=can_write)

    # WOPI source URL Collabora will call back on (path-based, no query params)
    site_url = frappe.utils.get_url()
    wopi_src = f"{site_url}/wopi/files/{file_id}"

    # Strip placeholder parameters from the discovery URL template
    clean_url = editor_url.replace("<", "").replace(">", "")
    if "?" in clean_url:
        clean_url = clean_url.split("?")[0]

    user_lang = frappe.local.lang or "en"
    full_url = f"{clean_url}?WOPISrc={urllib.parse.quote(wopi_src, safe='')}&lang={user_lang}"

    return {
        "editor_url": full_url,
        "access_token": token_data["access_token"],
        "access_token_ttl": token_data["access_token_ttl"],
        "file_name": file_name,
        "can_write": can_write,
    }


#//// Neoffice — split in two. `collabora_status()` is the callable; the whitelisted
#//// wrapper below is READ-ONLY and no longer answers guests. What it was: an
#//// `allow_guest=True` endpoint whose documented side effect was to wake coolwsd,
#//// with no rate limit — i.e. anyone on the internet could hold a web worker for
#//// 20 s per request and keep a ~400 MB daemon running for free on every instance
#//// of the fleet. It also handed back `server_url`, which is infrastructure detail
#//// an anonymous caller has no business reading.
def collabora_status(start_if_down: bool = False) -> dict:
    """Report whether the Collabora server is reachable and configured.

    ``start_if_down`` is for the editor-open path only (see get_discovery_xml).
    """
    settings = get_wopi_settings()

    if not settings.get("enabled"):
        return {
            "available": False,
            "status": "disabled",
            "message": _("WOPI/Collabora is disabled"),
        }

    collabora_url = get_collabora_url()
    discovery = get_discovery_xml(start_if_down=start_if_down)

    if discovery is None:
        return {
            "available": False,
            "status": "error",
            "message": _("Cannot reach Collabora server at {0}").format(collabora_url),
            "server_url": collabora_url,
        }

    formats = set()
    for app in discovery.findall(".//app"):
        for action in app.findall("action"):
            ext = action.get("ext")
            if ext and action.get("name") == "edit":
                formats.add(ext)

    return {
        "available": True,
        "status": "ok",
        "message": _("Collabora server is reachable"),
        "server_url": collabora_url,
        "supported_formats": sorted(formats),
    }


#//// Neoffice — see collabora_status above: signed-in only, and read-only. Starting
#//// the daemon belongs to the editor-open path, never to a status check.
@frappe.whitelist()
def check_collabora_status() -> dict:
    """Report the Collabora server status without touching the daemon."""
    return collabora_status(start_if_down=False)

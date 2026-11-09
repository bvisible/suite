# //// Neoffice — added file (no upstream equivalent): the visitor's side of a shared presentation, served by a page
# //// renderer (hooks.py `page_renderer`) so that one route answers HTML and the presentation's files:
# ////   /p/<token>                     the page: the e-mail, the code, the logo, then the presentation in a frame
# ////   /p/<token>/brand               the logo at the top of the page (a still one)
# ////   /p/<token>/logo                the logo of the opening (animated or not)
# ////   /p/<token>/preview/<secret>    the preview, ours only: the same page without the e-mail and the code, and
# ////                                   nothing counted (the secret is the link's preview token, shown on its record)
# ////   /p/<token>/c/<visit>/start     the presentation's entry file (`index.html`: frappe redirects any route that ends
# ////                                   with `.html`, `index` or `/`, so the entry has a name of its own, one level down,
# ////                                   and the presentation's relative paths still resolve beside it)
# ////   /p/<token>/c/<visit>/<path>    a file of the presentation, for a running visit only (or the preview's secret)
# //// The presentation runs in a frame sandboxed without its origin: its scripts never see a session of the site. Its
# //// entry file gets a small bridge (public/presentation/bridge.js) that tells the page which slide is on screen
# //// and how far each video went. The route stays open while the website is in maintenance (hooks.py).
from __future__ import annotations

import json
import mimetypes
from urllib.parse import unquote

import frappe
from frappe import _
from frappe.website.page_renderers.base_renderer import BaseRenderer
from werkzeug.utils import send_file
from werkzeug.wrappers import Response

from suite.drive.presentation import rules
from suite.drive.utils.files import FileManager, storage_key, stored_on_disk

BRIDGE = '<script src="/assets/suite/presentation/bridge.js?v=4"></script>'
ENTRY_ALIAS = "start"
CONTENT_SANDBOX = "sandbox allow-scripts allow-popups allow-popups-to-escape-sandbox"
PRIVATE_HEADERS = {
    "Cache-Control": "no-store",
    "X-Robots-Tag": "noindex, nofollow",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
}


class PresentationLinkPage(BaseRenderer):
    def __init__(self, path=None, http_status_code=None):
        super().__init__(path, http_status_code)
        # The route rule (hooks.py) hands every /p/… request over as the endpoint `p`: the path is the request's.
        request = getattr(frappe.local, "request", None)
        if self.path == "p" and request:
            self.path = request.path.strip("/ ")

    def can_render(self):
        parts = self.path.split("/")
        if len(parts) < 2 or parts[0] != "p" or not rules.TOKEN_RE.fullmatch(parts[1]):
            return False
        return (
            len(parts) == 2
            or (len(parts) == 3 and parts[2] in ("logo", "brand"))
            or (len(parts) == 4 and parts[2] == "preview")
            or (len(parts) >= 5 and parts[2] == "c")
        )

    def render(self):
        parts = self.path.split("/")
        token = parts[1]
        if len(parts) == 2:
            return self._page(token)
        if parts[2] in ("logo", "brand"):
            return self._logo(token, "intro_logo" if parts[2] == "logo" else "brand_logo")
        if parts[2] == "preview":
            return self._page(token, preview=parts[3])
        return self._content(token, parts[3], unquote("/".join(parts[4:])))

    # The page ------------------------------------------------------------------------------------------------------
    def _page(self, token: str, preview: str | None = None) -> Response:
        from suite.drive.presentation.api import preview_link

        link = preview_link(token, preview) if preview else _link(token)
        context = {
            "title": link.title if link else _("Presentation"),
            "is_open": bool(link),
            "config": json.dumps(
                {
                    "token": token,
                    "title": link.title if link else "",
                    "isOpen": bool(link),
                    "hasLogo": bool(link and link.intro_logo),
                    "hasBrand": bool(link and link.brand_logo),
                    "introSeconds": float(link.intro_seconds or 1.2) if link else 0,
                    # the preview opens at once: what the code would have given, without a visit
                    "preview": _preview_start(link, preview) if link and preview else None,
                    "csrfToken": frappe.session.data.csrf_token if frappe.session.user != "Guest" else "",
                    "strings": viewer_strings(),
                }
            ).replace("<", "\\u003c"),
            "strings": viewer_strings(),
            "lang": frappe.local.lang or "fr",
            "preview": bool(link and preview),
        }
        html = frappe.render_template("suite/templates/presentation/viewer.html", context)
        response = Response(html, status=200 if link else 404, mimetype="text/html")
        response.headers.update(PRIVATE_HEADERS)
        return response

    # The logo of the opening ---------------------------------------------------------------------------------------
    def _logo(self, token: str, field: str) -> Response:
        from suite.drive.presentation.api import preview_link

        # the preview shows the logos of a link in any state: it names its secret
        link = _link(token) or preview_link(token, frappe.form_dict.get("preview"))
        file_name = link and link.get(field) and frappe.db.get_value("File", {"file_url": link.get(field)})
        if not file_name:
            return _not_found()
        file = frappe.get_doc("File", file_name)
        return _send(file, cache=True)

    # A file of the presentation ------------------------------------------------------------------------------------
    def _content(self, token: str, secret: str, path: str) -> Response:
        from suite.drive.presentation.api import preview_link, visit_for_content

        visit = visit_for_content(token, secret)
        link = frappe.get_doc("Presentation Link", visit.link) if visit else preview_link(token, secret)
        if not link:
            return _not_found()
        folder, entry = rules.entry_file(link.presentation)
        if path == ENTRY_ALIAS:
            return _entry(entry)
        file = rules.resolve(folder, path)
        if not file and "." not in path.rsplit("/", 1)[-1]:
            # another page of the presentation, whose `.html` frappe's redirect took away
            file = rules.resolve(folder, path + ".html")
        if not file:
            return _not_found()
        if file.name == entry.name:
            return _entry(file)
        response = _send(frappe.get_doc("File", file.name), cache=True)
        # The frame has no origin ("null"): its fonts and its fetches are cross-origin requests. The path carries the
        # visit's secret and no cookie is ever read, so any origin may read the file. A site that sets `allow_cors`
        # gets frappe's own header for the request's origin: a second one made the browser refuse both (the hub's
        # `allow_cors: "*"`, every font of the presentation blocked).
        if not frappe_answers_cors():
            response.headers["Access-Control-Allow-Origin"] = "*"
        return response


def frappe_answers_cors() -> bool:
    """Whether frappe itself allows the request's origin on its response (frappe/app.py, set_cors_headers)."""
    allowed = frappe.conf.allow_cors
    request = getattr(frappe.local, "request", None)
    origin = request.headers.get("Origin") if request else None
    if not (allowed and origin):
        return False
    if allowed == "*":
        return True
    return origin in (allowed if isinstance(allowed, list) else [allowed])


def viewer_strings() -> dict:
    """Every word of the visitor's page (the page script reads them; the extractor sees each literal)."""
    return {
        "privatePresentation": _("Private presentation"),
        "preparedFor": _("Prepared for you"),
        "email": _("Your e-mail address"),
        "emailHint": _("We send a six-digit code to it."),
        "firstName": _("First name (optional)"),
        "getCode": _("Get my code"),
        "measured": _(
            "To prepare what comes next with you, we see the time spent on each slide and whether the videos "
            "were watched. This stays with us, in Switzerland, with our exchange."
        ),
        "codeSent": _("Your code is on its way"),
        "lookInbox": _("Look in your inbox"),
        "sentTo": _("We sent it to {0}. It is valid for 10 minutes."),
        "codeLegend": _("The six-digit code"),
        "opensAtSixth": _("The presentation opens at the sixth digit."),
        "resend": _("Send the code again"),
        "notMyAddress": _("This is not my address"),
        "haveCode": _("I have an access code"),
        "accessCode": _("Your access code"),
        "accessHint": _("The code given to you with the link, eight signs."),
        # not the bare « Enter », which the desk translates as the keyboard's key
        "enter": _("Open the presentation"),
        "codeByEmail": _("Receive a code by e-mail instead"),
        "rememberNote": _("On this browser you will not need a code for 30 days."),
        "closedTitle": _("This presentation is not shared any more"),
        "closedText": _("Write to the person who sent it to you: a new link leaves in one click."),
        "slideOf": _("{0} / {1}"),
        "previous": _("Previous slide"),
        "slideN": _("Slide {0}"),
        "slidesBar": _("The slides"),
        "next": _("Next slide"),
        "fullScreen": _("Full screen"),
        # its own context: the hub's Translation table says « Vers l'avant » for a bare « Forward » (a calendar's arrow)
        "forward": _("Forward", context="Send the presentation to a colleague"),
        "forwardTitle": _("Forward to a colleague"),
        "forwardText": _(
            "Your colleague receives the presentation in their name. Their code arrives by itself."
        ),
        "colleagueEmail": _("Their e-mail address"),
        "colleagueName": _("Their first name (optional)"),
        "aNote": _("A note for them, if you like"),
        "send": _("Send"),
        "cancel": _("Cancel"),
        "sent": _("Sent. They will receive it in a moment."),
        "error": _("Something went wrong. Try again in a moment."),
        "keys": _("Arrow keys, or swipe on a phone"),
        "ask": _("A question?"),
        "askSubNora": _("Nora answers from this presentation. Otherwise, she passes it on to {0}."),
        "askSubPerson": _("{0} answers you by e-mail."),
        "onSlide": _("On slide {0}"),
        "onSlideTitled": _("On slide {0} · {1}"),
        "askPlaceholder": _("Your question on this slide…"),
        "askSend": _("Send the question"),
        "askNote": _("Your questions are read by the person who sent you this presentation."),
        "askHint": _(
            "Ask about what you see: Nora answers from the presentation, or passes your question on."
        ),
        "askHintPerson": _("Ask about what you see: your question goes to {0}, who answers by e-mail."),
        "askThinking": _("Nora reads the presentation…"),
        "askForwarded": _("I passed your question on to {0}: the answer comes by e-mail, to {1}."),
        "askForwardedPerson": _("{0} has your question: the answer comes by e-mail, to {1}."),
        "forwardedPill": _("Passed on to {0} · answer by e-mail"),
        "answerOf": _("Answer of {0}"),
        "close": _("Close"),
        "soundOn": _("Turn the sound on"),
        "soundOff": _("Turn the sound off"),
        "dictate": _("Dictate your question"),
        "stopDictation": _("Stop and write it"),
        "listening": _("Listening… {0} s"),
        "writing": _("Writing it down…"),
        "noMicrophone": _("The microphone is not available."),
        "heardNothing": _("Nothing was heard. Try again, a little closer."),
        "endTitle": _("You reached the end"),
        "endText": _("Thank you for watching it to the end."),
        "previewBadge": _("Preview · nothing is counted"),
        "previewShort": _("Preview"),
        "previewNotSent": _("Preview: nothing is sent."),
        "previewWouldForward": _("In the preview, this question would go to {0}, who answers by e-mail."),
    }


def _link(token: str):
    """The link of `token` when it opens, else None (a closed link and a missing one look the same)."""
    name = frappe.db.get_value("Presentation Link", {"token": token})
    if not name:
        return None
    link = frappe.get_doc("Presentation Link", name)
    return link if rules.is_open(link) else None


def _preview_start(link, secret: str) -> dict:
    """What the visitor's page receives after the code, for the preview: the presentation's entry under the preview's
    secret, and the link's settings; no visit, so nothing is counted."""
    from suite.drive.presentation import questions as asking

    return {
        "secret": secret,
        "content": f"/p/{link.token}/c/{secret}/start",
        "can_forward": bool(link.allow_forward),
        "questions": asking.visitor_settings(link),
    }


def _entry(file) -> Response:
    """The entry file of the presentation, with the bridge, under a sandbox without the site's origin."""
    html = _read(frappe.get_doc("File", file.name)).decode("utf-8", errors="replace")
    lower = html.lower()
    at = lower.rfind("</body>")
    html = html[:at] + BRIDGE + html[at:] if at >= 0 else html + BRIDGE
    response = Response(html, mimetype="text/html")
    response.headers.update(PRIVATE_HEADERS)
    response.headers["Content-Security-Policy"] = CONTENT_SANDBOX
    return response


def _read(file) -> bytes:
    manager = FileManager()
    if manager.s3_enabled and not stored_on_disk(file.file_url):
        return manager.get_file(file).read()
    with open(manager.get_local_path(file.file_url), "rb") as handle:
        return handle.read()


def _send(file, cache: bool = False) -> Response:
    """A file of the presentation, range-capable (Safari plays a video only by ranges). Anything a browser could run
    on its own (an HTML page other than the entry, an SVG opened alone) keeps a sandbox."""
    mime = mimetypes.guess_type(file.file_name or "")[0] or "application/octet-stream"
    manager = FileManager()
    if manager.s3_enabled and not stored_on_disk(file.file_url):
        response = Response(status=302)
        response.headers["Location"] = manager.presigned_url(storage_key(file.file_url), file.file_name, mime)
        return response
    response = send_file(
        str(manager.get_local_path(file.file_url)),
        mimetype=mime,
        conditional=True,
        max_age=3600 if cache else 0,
        environ=frappe.request.environ,
    )
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    if mime in ("text/html", "image/svg+xml", "application/xhtml+xml", "text/xml", "application/xml"):
        response.headers["Content-Security-Policy"] = CONTENT_SANDBOX
    if cache:
        response.headers["Cache-Control"] = "private, max-age=3600"
    return response


def _not_found() -> Response:
    response = Response(_("Not found"), status=404, mimetype="text/plain")
    response.headers.update(PRIVATE_HEADERS)
    return response

# //// Neoffice — added file (no upstream equivalent): the methods of a shared presentation. The visitor's page calls
# //// the guest ones (a code, the visit, its heartbeat, a forward); the staff call send_link and get_stats, which check
# //// the right on the link. A guest method answers the same way for a link that does not exist and one that is closed.
from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import escape_html, get_datetime, now_datetime

from suite.drive.presentation import rules


# ---------------------------------------------------------------------------------------------------------------------
# The visitor
# ---------------------------------------------------------------------------------------------------------------------
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=12, seconds=600)
def request_code(
    token: str, email: str, first_name: str | None = None
):  # permission-check: ok the visitor has no account: the link token and the accepted domains decide
    """Sends a code to `email` when the link accepts it."""
    link = _open_link(token)
    email = rules.normalize_email(email)
    if not email:
        return {"ok": False, "reason": "invalid_email", "message": _("This is not an e-mail address.")}
    if not rules.email_accepted(link, email):
        return {
            "ok": False,
            "reason": "not_accepted",
            "message": _("This address cannot open the presentation. Ask the person who sent it to you."),
        }
    code = rules.issue_code(link.name, email, _clean_name(first_name))
    _send_code(link, email, code)
    return {"ok": True, "email": email}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=600)
def verify_code(
    token: str, email: str, code: str, browser_id: str | None = None
):  # permission-check: ok the visitor has no account: the code sent to the e-mail is the proof
    """Opens a visit when the code is right."""
    link = _open_link(token)
    email = rules.normalize_email(email)
    waiting = rules.take_code(link.name, email, code) if email else None
    if not waiting:
        return {
            "ok": False,
            "reason": "wrong_code",
            "message": _("This code is not the right one, or it has expired."),
        }
    viewer, is_new = _viewer(link, email, waiting.get("first_name"))
    remember = rules.new_secret()
    frappe.db.set_value(
        "Presentation Viewer",
        viewer.name,
        {"remember_hash": rules.hash_secret(remember), "remember_until": rules.remember_until()},
    )
    visit = _start_visit(link, viewer, browser_id)
    if is_new:
        _notify_owner(link, viewer)
    return {"ok": True, "remember": remember, **visit}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=30, seconds=600)
def resume(
    token: str, email: str, remember: str, browser_id: str | None = None
):  # permission-check: ok the visitor has no account: the remembered secret of the browser is the proof
    """Opens a visit without a code on a browser where the code was given in the last 30 days."""
    link = _open_link(token)
    email = rules.normalize_email(email)
    viewer = frappe.db.get_value(
        "Presentation Viewer",
        {"link": link.name, "email": email, "remember_hash": rules.hash_secret(remember)},
        ["name", "email", "first_name", "remember_until"],
        as_dict=True,
    )
    if not (email and remember and viewer and viewer.remember_until):
        return {"ok": False}
    if get_datetime(viewer.remember_until) < now_datetime():
        return {"ok": False}
    return {"ok": True, **_start_visit(link, viewer, browser_id)}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=120, seconds=600)
def track(
    visit: str, beat: str | dict | None = None
):  # permission-check: ok the visit's secret, given after the code, is the proof
    """A heartbeat of a visit: the seconds watched per slide since the last one and how far each video went."""
    row = _visit(visit)
    if not row:
        return {"ok": False}
    if isinstance(beat, str):
        try:
            beat = json.loads(beat)
        except ValueError:
            beat = {}
    merged = rules.merge_beat(_json(row.slides), _json(row.videos), beat)
    now = now_datetime()
    frappe.db.set_value(
        "Presentation Visit",
        row.name,
        {
            "slides": json.dumps(merged["slides"]),
            "videos": json.dumps(merged["videos"]),
            "active_seconds": round(sum(merged["slides"].values())),
            "furthest_slide": max(row.furthest_slide or 0, merged["furthest"]),
            "slide_count": merged["total"] or row.slide_count,
            "last_seen_on": now,
        },
        update_modified=False,
    )
    _refresh_viewer(row.viewer, now)
    _refresh_link(row.link, now)
    return {"ok": True}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=600)
def forward(
    visit: str, email: str, first_name: str | None = None, message: str | None = None
):  # permission-check: ok the visit's secret is the proof; the link decides who may receive it
    """Sends the presentation to a colleague of the person watching it, when the link allows it."""
    row = _visit(visit)
    if not row:
        return {"ok": False, "reason": "closed", "message": _("This presentation is not shared any more.")}
    link = frappe.get_doc("Presentation Link", row.link)
    if not (rules.is_open(link) and link.allow_forward):
        return {"ok": False, "reason": "not_allowed", "message": _("This presentation cannot be forwarded.")}
    email = rules.normalize_email(email)
    if not email:
        return {"ok": False, "reason": "invalid_email", "message": _("This is not an e-mail address.")}
    if not (link.forward_outside or rules.email_accepted(link, email)):
        return {
            "ok": False,
            "reason": "not_accepted",
            "message": _("This address cannot open the presentation. Ask the person who sent it to you."),
        }
    sender = frappe.db.get_value(
        "Presentation Viewer", row.viewer, ["name", "email", "first_name"], as_dict=True
    )
    if not frappe.db.exists("Presentation Viewer", {"link": link.name, "email": email}):
        frappe.get_doc(
            {
                "doctype": "Presentation Viewer",
                "link": link.name,
                "email": email,
                "first_name": _clean_name(first_name),
                "entered_via": "Forwarded",
                "invited_by": sender.name,
            }
        ).insert(ignore_permissions=True)
    _send_link_mail(link, email, _clean_name(first_name), _clean_message(message), sender=_who(sender))
    _notify(
        link,
        _("{0} forwarded « {1} » to {2}").format(_who(sender), link.title, email),
    )
    return {"ok": True}


# ---------------------------------------------------------------------------------------------------------------------
# The staff
# ---------------------------------------------------------------------------------------------------------------------
@frappe.whitelist(methods=["POST"])
def send_link(name: str, email: str, first_name: str | None = None, message: str | None = None):
    """Sends the link from the ERP to `email`; an address outside the accepted domains is accepted with it."""
    link = frappe.get_doc("Presentation Link", name)
    link.check_permission("write")
    if not rules.is_open(link):
        frappe.throw(_("This link is withdrawn or has expired."))
    email = rules.normalize_email(email)
    if not email:
        frappe.throw(_("This is not an e-mail address."))
    recipients = rules.normalize_emails(link.recipients)
    if email not in recipients:
        recipients.append(email)
    link.recipients = "\n".join(recipients)
    if link.status == "Draft":
        link.status = "Sent"
    link.save()
    _send_link_mail(
        link, email, _clean_name(first_name), _clean_message(message), sender=frappe.utils.get_fullname()
    )
    return {"ok": True, "status": link.status}


@frappe.whitelist()
def get_stats(name: str):
    """What the people who entered saw: per person, per slide, and what happened when."""
    link = frappe.get_doc("Presentation Link", name)
    link.check_permission("read")
    viewers = frappe.get_all(
        "Presentation Viewer",
        filters={"link": name},
        fields=[
            "name",
            "email",
            "first_name",
            "entered_via",
            "invited_by",
            "first_seen_on",
            "last_seen_on",
            "total_seconds",
            "slides_seen",
            "furthest_slide",
            "video_percent",
            "devices",
            "creation",
        ],
        order_by="first_seen_on asc",
    )
    visits = frappe.get_all(
        "Presentation Visit",
        filters={"link": name},
        fields=["viewer", "started_on", "device", "active_seconds", "slides", "videos", "slide_count"],
        order_by="started_on asc",
    )
    names = {v.name: v for v in viewers}
    per_slide: dict[str, float] = {}
    slide_count = 0
    events = []
    for visit in visits:
        slide_count = max(slide_count, visit.slide_count or 0)
        for key, seconds in _json(visit.slides).items():
            per_slide[key] = round(per_slide.get(key, 0) + float(seconds), 1)
        person = names.get(visit.viewer)
        events.append({"on": visit.started_on, "kind": "visit", "who": _who(person), "device": visit.device})
        for source, percent in _json(visit.videos).items():
            if int(percent) >= 95:
                events.append({"on": visit.started_on, "kind": "video", "who": _who(person), "video": source})
    for viewer in viewers:
        if viewer.invited_by and viewer.invited_by in names:
            events.append(
                {
                    "on": viewer.creation,
                    "kind": "forwarded",
                    "who": _who(names[viewer.invited_by]),
                    "to": viewer.email,
                }
            )
        viewer.who = _who(viewer)
        viewer.forwarded_by = _who(names.get(viewer.invited_by)) if viewer.invited_by else None
    events = sorted((e for e in events if e["on"]), key=lambda e: get_datetime(e["on"]))
    return {
        "title": link.title,
        "status": link.status,
        "url": link.url,
        "slide_count": slide_count,
        "per_slide": per_slide,
        "viewers": [v for v in viewers if v.first_seen_on],
        "invited": [v.email for v in viewers if not v.first_seen_on],
        "events": events[-40:],
        "total_seconds": sum(v.total_seconds or 0 for v in viewers),
    }


# ---------------------------------------------------------------------------------------------------------------------
# Inside
# ---------------------------------------------------------------------------------------------------------------------
def _open_link(token: str):
    """The link of `token` when it opens; otherwise the same refusal whether it exists or not."""
    name = (
        frappe.db.get_value("Presentation Link", {"token": token})
        if rules.TOKEN_RE.fullmatch(token or "")
        else None
    )
    link = frappe.get_doc("Presentation Link", name) if name else None
    if not (link and rules.is_open(link)):
        frappe.throw(_("This presentation is not shared any more."), frappe.PermissionError)
    return link


def _visit(secret: str):
    if not secret or len(secret) > 100:
        return None
    row = frappe.db.get_value(
        "Presentation Visit",
        {"secret_hash": rules.hash_secret(secret)},
        ["name", "link", "viewer", "started_on", "slides", "videos", "furthest_slide", "slide_count"],
        as_dict=True,
    )
    if not row or get_datetime(row.started_on) < rules.visit_expiry():
        return None
    status, expires_on = frappe.db.get_value("Presentation Link", row.link, ["status", "expires_on"])
    if status == "Withdrawn" or (expires_on and get_datetime(expires_on) < now_datetime()):
        return None
    return row


def visit_for_content(token: str, secret: str):
    """The visit of `secret` when it belongs to the link of `token` and is still running (the content route)."""
    row = _visit(secret)
    if not row or frappe.db.get_value("Presentation Link", row.link, "token") != token:
        return None
    return row


def _viewer(link, email: str, first_name: str | None):
    """The person of `email` on this link, created at her first entry; True when she enters for the first time."""
    name = frappe.db.get_value("Presentation Viewer", {"link": link.name, "email": email})
    now = now_datetime()
    if name:
        viewer = frappe.get_doc("Presentation Viewer", name)
        first = not viewer.first_seen_on
        values = {"last_seen_on": now}
        if first:
            values["first_seen_on"] = now
        if first_name and not viewer.first_name:
            values["first_name"] = first_name
        frappe.db.set_value("Presentation Viewer", name, values)
        viewer.update(values)
        return viewer, first
    sent = email in rules.normalize_emails(link.recipients)
    viewer = frappe.get_doc(
        {
            "doctype": "Presentation Viewer",
            "link": link.name,
            "email": email,
            "first_name": first_name,
            "entered_via": "Link Sent" if sent else "Copied Link",
            "first_seen_on": now,
            "last_seen_on": now,
        }
    ).insert(ignore_permissions=True)
    return viewer, True


def _start_visit(link, viewer, browser_id: str | None) -> dict:
    secret = rules.new_secret()
    request = getattr(frappe.local, "request", None)
    agent = ((request.headers.get("User-Agent") if request else "") or "")[:500]
    now = now_datetime()
    frappe.get_doc(
        {
            "doctype": "Presentation Visit",
            "link": link.name,
            "viewer": viewer.name,
            "browser_id": (browser_id or "")[:64],
            "device": rules.device_of(agent),
            "user_agent": agent,
            "started_on": now,
            "last_seen_on": now,
            "secret_hash": rules.hash_secret(secret),
        }
    ).insert(ignore_permissions=True)
    values = {"last_seen_on": now}
    if link.status != "Opened":
        values["status"] = "Opened"
    if not link.first_opened_on:
        values["first_opened_on"] = now
    frappe.db.set_value("Presentation Link", link.name, values, update_modified=False)
    _refresh_viewer(viewer.name, now)
    _refresh_link(link.name, now)
    return {
        "visit": secret,
        "content": f"/p/{link.token}/c/{secret}/start",
        "first_name": viewer.first_name or "",
        "can_forward": bool(link.allow_forward),
    }


def _refresh_viewer(viewer: str, now) -> None:
    visits = frappe.get_all(
        "Presentation Visit",
        filters={"viewer": viewer},
        fields=["slides", "videos", "furthest_slide", "browser_id", "device"],
    )
    slides: dict[str, float] = {}
    video = 0
    for visit in visits:
        for key, seconds in _json(visit.slides).items():
            slides[key] = slides.get(key, 0) + float(seconds)
        video = max([video, *(int(p) for p in _json(visit.videos).values())])
    browsers = {visit.browser_id or visit.device for visit in visits}
    frappe.db.set_value(
        "Presentation Viewer",
        viewer,
        {
            "total_seconds": round(sum(slides.values())),
            "slides_seen": rules.slides_seen(slides),
            "furthest_slide": max((v.furthest_slide or 0 for v in visits), default=0),
            "video_percent": video,
            "devices": len(browsers),
            "last_seen_on": now,
        },
        update_modified=False,
    )


def _refresh_link(link: str, now) -> None:
    rows = frappe.get_all(
        "Presentation Viewer",
        filters={"link": link, "first_seen_on": ["is", "set"]},
        fields=["total_seconds"],
    )
    frappe.db.set_value(
        "Presentation Link",
        link,
        {
            "viewer_count": len(rows),
            "total_seconds": sum(r.total_seconds or 0 for r in rows),
            "last_seen_on": now,
        },
        update_modified=False,
    )


def _notify_owner(link, viewer) -> None:
    if link.notify_owner:
        _notify(link, _("{0} opened « {1} »").format(_who(viewer), link.title))


def _notify(link, subject: str) -> None:
    from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

    enqueue_create_notification(
        link.owner,
        {
            "type": "Alert",
            "document_type": "Presentation Link",
            "document_name": link.name,
            "subject": escape_html(subject),
            "from_user": link.owner,
        },
    )


def _send_code(link, email: str, code: str) -> None:
    body = "".join(
        [
            f"<p>{escape_html(_('Your code to open « {0} »:').format(link.title))}</p>",
            f'<p style="font-size:30px;letter-spacing:6px;font-weight:700;margin:16px 0">{code}</p>',
            f"<p>{escape_html(_('It is valid for 10 minutes. If you did not ask for it, ignore this e-mail.'))}</p>",
        ]
    )
    frappe.sendmail(
        recipients=[email],
        subject=_("Your code for « {0} »").format(link.title),
        message=body,
        now=True,
        reference_doctype="Presentation Link",
        reference_name=link.name,
    )


def _send_link_mail(link, email: str, first_name: str, message: str, sender: str) -> None:
    greeting = _("Hello {0},").format(first_name) if first_name else _("Hello,")
    lines = [f"<p>{escape_html(greeting)}</p>"]
    lines.append(
        f"<p>{escape_html(_('{0} shares a presentation with you: « {1} ».').format(sender, link.title))}</p>"
    )
    if message:
        lines.append(f'<p style="white-space:pre-line">{escape_html(message)}</p>')
    lines.append(
        f'<p style="margin:24px 0"><a href="{escape_html(link.url)}" style="background:#141414;color:#ffffff;'
        f'padding:12px 20px;border-radius:10px;text-decoration:none;font-weight:600">'
        f"{escape_html(_('Open the presentation'))}</a></p>"
    )
    lines.append(f"<p>{escape_html(_('A code will be sent to this address to open it.'))}</p>")
    frappe.sendmail(
        recipients=[email],
        subject=_("{0} shares « {1} » with you").format(sender, link.title),
        message="".join(lines),
        now=True,
        reference_doctype="Presentation Link",
        reference_name=link.name,
    )


def _who(viewer) -> str:
    if not viewer:
        return ""
    return viewer.get("first_name") or viewer.get("email") or ""


def _clean_name(name: str | None) -> str:
    return (name or "").strip()[:80]


def _clean_message(message: str | None) -> str:
    return (message or "").strip()[:1000]


def _json(value) -> dict:
    if isinstance(value, dict):
        return value
    try:
        data = json.loads(value or "{}")
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}

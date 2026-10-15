# //// Neoffice — added file (no upstream equivalent): pairing the computers that keep a folder in step with the Drive.
"""Devices of the Drive's synchronisation.

A computer that synchronises a folder with the Drive (Neodesk, through rclone first) must not hold the password of
the account, nor its API key (a key gives the whole account to whoever has it, and generating a new one revokes
every computer at once). It holds a token of its own: `register_device` is called from the signed-in app, hands the
token over **once**, and stores only its SHA-256. The Drive's WebDAV accepts it as `Authorization: Bearer <token>`
(suite.drive.webdav.auth), and nothing else does: it opens /dav and no other door of the site.

Revoking a device stops that computer at its next request and leaves the others as they are.
"""

from __future__ import annotations

import secrets

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, now_datetime

from suite.drive.doctype.drive_sync_device.drive_sync_device import TOKEN_PREFIX, hash_token

# a person with more computers than this has something to tidy up; the limit also bounds what a stolen session
# could pair
MAX_DEVICES_PER_USER = 25
NAME_LENGTH = 140
# folders are walked upwards one by one: a loop in the adjacency list must end somewhere
MAX_FOLDER_DEPTH = 64


def _text(value, limit: int = NAME_LENGTH) -> str:
    return " ".join(str(value or "").split())[:limit]


def _signed_in_user() -> str:
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Sign in to pair a computer."), frappe.PermissionError)
    return user


def _enable_webdav_for(user: str) -> None:
    """Pairing a computer is the person asking for the synchronisation: the account's own switch follows (the
    site-wide one is the administrator's, and stays as it is)."""
    if not frappe.db.exists("Drive Settings", user):
        frappe.get_doc({"doctype": "Drive Settings", "user": user}).insert(ignore_permissions=True)
    frappe.db.set_value("Drive Settings", user, "webdav_enabled", 1, update_modified=False)


def _describe(row) -> dict:
    return {
        "id": row.name,
        "device_name": row.device_name,
        "platform": row.platform or "",
        "app": row.app or "",
        "token_hint": row.token_hint or "",
        "created": row.creation,
        "last_seen": row.last_seen,
        "revoked": bool(row.revoked),
    }


@frappe.whitelist(methods=["POST"])
def register_device(device_name: str, platform: str | None = None, app: str | None = None) -> dict:
    """Pair the computer of the signed-in user. Answers the token — **this once** — with the address of the
    Drive's WebDAV for the client to use."""
    from suite.drive.webdav import settings

    user = _signed_in_user()
    if not settings.global_webdav_enabled():
        frappe.throw(_("File synchronisation is not enabled on this site."), frappe.PermissionError)

    name = _text(device_name)
    if not name:
        frappe.throw(_("Name the computer."))

    active = frappe.db.count("Drive Sync Device", {"user": user, "revoked": 0})
    if active >= MAX_DEVICES_PER_USER:
        frappe.throw(
            _("{0} computers are already paired: remove one you no longer use first.").format(active)
        )

    token = TOKEN_PREFIX + secrets.token_urlsafe(32)
    device = frappe.get_doc(
        {
            "doctype": "Drive Sync Device",
            "user": user,
            "device_name": name,
            "platform": _text(platform),
            "app": _text(app),
            "token_hash": hash_token(token),
            "token_hint": token[-4:],
        }
    ).insert(ignore_permissions=True)
    _enable_webdav_for(user)

    return {
        "id": device.name,
        "token": token,
        "device_name": device.device_name,
        "dav_url": frappe.utils.get_url().rstrip("/") + "/dav/",
    }


@frappe.whitelist()
def list_devices() -> list[dict]:
    """The computers paired by the signed-in user, newest first. Never the token (only its last characters)."""
    user = _signed_in_user()
    rows = frappe.get_all(
        "Drive Sync Device",
        filters={"user": user},
        fields=[
            "name",
            "device_name",
            "platform",
            "app",
            "token_hint",
            "creation",
            "last_seen",
            "revoked",
        ],
        order_by="creation desc",
        limit_page_length=MAX_DEVICES_PER_USER * 4,
    )
    return [_describe(row) for row in rows]


@frappe.whitelist(methods=["POST"])
def revoke_device(device: str) -> dict:
    """Stop a paired computer. Its owner may, and so may a System Manager (a computer that was lost)."""
    user = _signed_in_user()
    row = frappe.db.get_value("Drive Sync Device", device, ["name", "user", "revoked"], as_dict=True)
    # an unknown device and another person's are not told apart
    if not row or (row.user != user and "System Manager" not in frappe.get_roles(user)):
        frappe.throw(_("This computer is not paired."), frappe.DoesNotExistError)
    if not cint(row.revoked):
        frappe.db.set_value(
            "Drive Sync Device",
            row.name,
            {"revoked": 1, "revoked_at": now_datetime()},
            update_modified=True,
        )
    return {"id": row.name, "revoked": True}


@frappe.whitelist()
def dav_path(entity: str) -> dict:
    """The path of a folder of the Drive as a synchronising client names it: `Home/...` below the person's own folder,
    `Everyone/...` below the shared root (the two mounts of the WebDAV namespace, suite.drive.webdav.pathmap).

    A folder under neither (another person's folder that was shared with this one) is not reachable through WebDAV:
    `path` is then None. A folder the person cannot read is not told apart from one that does not exist."""
    from suite.drive.api.permissions import user_has_permission
    from suite.drive.utils import get_root_folder, get_user_folder
    from suite.drive.webdav import pathmap
    from suite.drive.webdav.context import validate_segments
    from suite.drive.webdav.errors import BadRequest

    user = _signed_in_user()
    fields = ["name", "file_name", "folder", "is_folder"]
    row = frappe.db.get_value("File", entity, fields, as_dict=True)
    if not row or not user_has_permission(entity, "read"):
        frappe.throw(_("This folder does not exist."), frappe.DoesNotExistError)
    if not row.is_folder:
        frappe.throw(_("Only a folder can be synchronised."))

    mounts = {get_user_folder(user).name: pathmap.HOME_ALIAS, get_root_folder().name: pathmap.EVERYONE_ALIAS}
    segments: list[str] = []
    current = row
    for _depth in range(MAX_FOLDER_DEPTH):
        if current.name in mounts:
            parts = list(reversed(segments))
            try:
                validate_segments(parts)
            except BadRequest:
                break
            return {"path": "/".join([mounts[current.name], *parts]), "mount": mounts[current.name]}
        if not current.folder:
            break
        segments.append(current.file_name)
        current = frappe.db.get_value("File", current.folder, fields, as_dict=True)
        if not current:
            break
    return {"path": None, "mount": None}


def touch_device(name: str, ip: str | None) -> None:
    """Note that a device was seen, at most once a minute: a sync pass is many requests, and none of them needs a
    write to say so."""
    key = f"drive_sync_device_seen:{name}"
    if frappe.cache.get_value(key):
        return
    frappe.cache.set_value(key, 1, expires_in_sec=60)
    frappe.db.set_value(
        "Drive Sync Device",
        name,
        {"last_seen": get_datetime(now_datetime()), "last_ip": _text(ip, 45)},
        update_modified=False,
    )

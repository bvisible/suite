# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import os

import frappe
import requests
from frappe.rate_limiter import rate_limit
from frappe.utils import now


def mark_as_viewed(entity):
    if (
        frappe.session.user == "Guest"
        or not frappe.has_permission(doctype="Drive Entity Log", ptype="create", user=frappe.session.user)
        or entity.is_folder
    ):
        return

    entity_log = frappe.db.get_value(
        "Drive Entity Log", {"entity_name": entity.name, "user": frappe.session.user}
    )
    if entity_log:
        frappe.db.set_value(
            "Drive Entity Log",
            entity_log,
            "last_interaction",
            now(),
            update_modified=False,
        )
        return
    doc = frappe.new_doc("Drive Entity Log")
    doc.entity_name = entity.name
    doc.user = frappe.session.user
    doc.last_interaction = now()
    doc.insert()
    return doc


def get_country_info():
    ip = frappe.local.request_ip

    def _get_country_info():
        fields = [
            "status",
            "message",
            "continent",
            "continentCode",
            "country",
            "countryCode",
            "region",
            "regionName",
            "city",
            "district",
            "zip",
            "lat",
            "lon",
            "timezone",
            "offset",
            "currency",
            "isp",
            "org",
            "as",
            "asname",
            "reverse",
            "mobile",
            "proxy",
            "hosting",
            "query",
        ]

        try:
            res = requests.get(f"https://pro.ip-api.com/json/{ip}?fields={','.join(fields)}")
            data = res.json()
            if data.get("status") != "fail":
                return data
        except Exception:
            pass

        return {}

    return frappe.cache().hget("ip_country_map", ip, generator=_get_country_info)


def create_drive_settings(user, method: str | None = None) -> None:
    """Create Drive Settings and the private user folder for a newly created User."""
    from suite.drive.utils import get_user_folder

    if user.flags.get("skip_drive_setup"):
        return

    if not user.name or user.name in ("Guest", "Administrator"):
        return

    get_user_folder(user.name)


# //// Neoffice — added function (no upstream equivalent).
# //// on_trash(User) -> drop the Drive Settings that create_drive_settings made.
# ////
# //// Upstream provisions Drive Settings for every new user and never removes it,
# //// and the doctype autonames `field:user` — the row's primary key IS the e-mail.
# //// The row a deleted user leaves behind is therefore picked up by the NEXT
# //// account created with the same address, from anywhere: the desk, a signup, or
# //// the fiduciary portal re-inviting a colleague who had been removed.
# ////
# //// The consequence got worse with the de-teaming (4df6ee65a): Drive Settings now
# //// carries `user_folder`, and get_user_folder() returns that folder as soon as
# //// the row exists. Where the stale row used to fail loudly on a duplicate primary
# //// key, it now silently hands the new account the previous owner's private
# //// folder. Mail cleans up after itself in on_trash; Drive does not.
# ////
# //// The File tree is deliberately left alone: those are the user's documents, and
# //// reaping them behind a user deletion is not this hook's call.
def delete_drive_settings(doc, method: str | None = None) -> None:
    """Remove the deleted user's Drive Settings so the address can be reused."""
    if frappe.db.exists("Drive Settings", doc.name):
        frappe.delete_doc("Drive Settings", doc.name, force=1, ignore_permissions=True)

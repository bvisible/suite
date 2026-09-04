#//// Neoffice — added file (no upstream equivalent).
"""Decisions this fork re-asserts at every install and every migrate.

A fixture states a value; it does not keep it, and neither does a patch (it runs
once). Everything here was lost at least once — to an upstream merge, or to a
request that could not write — so it lives as idempotent functions called from
``suite_core.boot``: the one place that runs on every site, on every migrate,
after the fixtures have synced.

Each function returns True when it actually changed something, so a caller (or a
test) can tell "already right" from "just repaired".
"""
from __future__ import annotations

import frappe


def ensure_wopi_secret() -> bool:
    """Provision the WOPI JWT signing secret once, so no request has to invent one.

    ``suite.drive.wopi.token`` signs and verifies Collabora's access tokens with
    this value. It used to be generated on the fly by the first call that found it
    missing, inside a ``try/except: pass`` that silently failed on the read-only
    transaction of a GET — so each request signed with a different random secret
    and Collabora answered "Invalid WOPI token" forever.

    ``save()`` rather than ``db_set()``: WOPISettings.validate() mints the secret
    and Frappe's ``_save_passwords`` then encrypts it into ``__Auth``, which is
    what ``get_password()`` reads back. ``db_set`` skips both and would leave the
    secret in clear in ``tabSingles``.
    """
    if not frappe.db.exists("DocType", "WOPI Settings"):
        return False

    settings = frappe.get_single("WOPI Settings")
    if settings.jwt_secret:
        try:
            if settings.get_password("jwt_secret"):
                return False
        except Exception:
            # Sealed with another site's encryption key (restored backup): unusable.
            # Clearing it makes validate() mint a readable replacement below.
            settings.jwt_secret = None

    settings.save(ignore_permissions=True)
    frappe.db.commit()
    frappe.log_error(
        "WOPI: JWT signing secret provisioned",
        "WOPI Settings had no usable JWT secret; one was generated at migrate time. "
        "Collabora sessions opened before this point are invalid and must be reopened.",
    )
    return True


def run() -> dict:
    """Re-assert every fork decision above. Safe to call repeatedly."""
    return {"wopi_secret": ensure_wopi_secret()}

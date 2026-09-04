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

# The role a frontend signup receives. It must NOT carry desk access: Frappe
# promotes any holder of a desk-access role to System User, which puts a shop
# customer on the desk and on the licence count.
PORTAL_ROLE = "Suite User"


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


def drop_orphan_role_assignments(role_name: str) -> int:
    """Delete this role's ``Has Role`` rows whose User no longer exists.

    Frappe's ``Role.update_user_type_on_change()`` — the half that actually
    demotes the accounts a desk role already promoted — loops over the holders and
    calls ``frappe.get_doc("User", name)`` on each. One row pointing at a deleted
    account raises DoesNotExistError there and takes the whole migration down with
    it; osiris carried two on 04.09.2026 ("reg-comptable@yopmail.com",
    "qa-debug@yopmail.com"), enough to abort `bench migrate` on that instance.

    The rows are unreachable by construction: ``Has Role`` is a child table of
    User, so a row whose parent is gone can never be read through its parent
    again. Scoped to this one role on purpose — cleaning "every orphan child row"
    is a different, much larger decision.
    """
    holders = set(
        frappe.get_all("Has Role", filters={"parenttype": "User", "role": role_name}, pluck="parent")
    )
    orphans = sorted(user for user in holders if not frappe.db.exists("User", user))
    if not orphans:
        return 0

    frappe.db.delete("Has Role", {"parenttype": "User", "role": role_name, "parent": ("in", orphans)})
    frappe.log_error(
        f"Suite: removed {len(orphans)} orphan {role_name} assignment(s)",
        "These `Has Role` rows named users that no longer exist, which makes "
        "Frappe's own user_type re-evaluation raise DoesNotExistError:\n" + "\n".join(orphans),
    )
    return len(orphans)


def ensure_portal_role_has_no_desk_access(role_name: str = PORTAL_ROLE) -> bool:
    """Hold "Suite User" at ``desk_access = 0``, whatever the last merge left.

    ``suite/fixtures/role.json`` carries the value (our e20b2ac06), but a fixture
    is a file: every upstream merge that touches it can put back upstream's 1, and
    ``sync_fixtures()`` then dutifully promotes every holder to System User —
    including the shop customers who received the role at signup. The fixture stays
    (it is what a fresh install reads); this is what survives the next merge.

    ``save()`` rather than ``db_set()``: Role.on_update() re-evaluates the
    ``user_type`` of every holder when ``desk_access`` changes, which is the half
    that actually demotes the accounts already promoted.

    ``role_name`` is a parameter so the test can prove the repair on a throwaway
    role instead of running the real one's holder re-evaluation on a live site.
    """
    if not frappe.db.exists("Role", role_name):
        return False
    if not frappe.db.get_value("Role", role_name, "desk_access"):
        return False

    drop_orphan_role_assignments(role_name)

    role = frappe.get_doc("Role", role_name)
    role.desk_access = 0
    try:
        role.save(ignore_permissions=True)
    except Exception:
        # The value matters more than the cascade, and this runs inside a migration:
        # write it directly so the role is right even when Frappe's own holder
        # re-evaluation cannot run, and say loudly what did not happen.
        frappe.db.set_value("Role", role_name, "desk_access", 0, update_modified=False)
        frappe.log_error(
            f"Suite: could not re-evaluate the holders of {role_name}",
            f"desk_access was written directly, so {role_name} is correct, but "
            "Role.on_update() failed. Accounts this role already promoted to System "
            "User keep that type until something saves them.\n\n" + frappe.get_traceback(),
        )
    frappe.db.commit()
    frappe.log_error(
        f"Suite: reset desk_access on role {role_name}",
        f"The {role_name} role was found with desk access (usual cause: an upstream "
        "merge restored the upstream fixture). It was set back to 0 and Frappe "
        "re-evaluated the user type of its holders. "
        "See suite/suite_core/neoffice.py.",
    )
    return True


def run() -> dict:
    """Re-assert every fork decision above. Safe to call repeatedly."""
    return {
        "wopi_secret": ensure_wopi_secret(),
        "portal_role_desk_access": ensure_portal_role_has_no_desk_access(),
    }

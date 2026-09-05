# //// Neoffice — added file (no upstream equivalent).
"""Backstop the role consolidation so portal accounts keep out of the desk.

Upstream's 8b911806e consolidated Drive's "Drive User"/"Drive Admin" onto the
suite-wide "Suite User"/"Suite Admin", and made both carry desk access on the
grounds that "both Drive roles carried desk access". That holds upstream. It does
not hold here: this fleet deliberately ships "Drive User", "Meet User" and
"Mail Admin" with ``desk_access = 0`` so that a visitor who signs up on the shop
stays a Website User (fixed once already in e20b2ac06).

Three upstream patches therefore migrate role assignments onto roles that, left
alone, would carry desk access:

* ``switch_drive_roles_to_suite_roles``  — "Drive User"  -> "Suite User"
* ``switch_meet_user_to_suite_user``     — "Meet User"   -> "Suite User"
* ``rename_mail_admin_to_suite_admin``   — "Mail Admin"  -> "Suite Admin"

None of them recomputes ``user_type``: they write ``Has Role`` rows in bulk (or
rename the Role outright), because upstream can assume every holder is already a
System User. Here they are not, so the damage is invisible at migrate time and
lands later — the account is promoted by the first ``User.save()`` that happens
to touch it, weeks after the fact.

We already hold the role to ``desk_access = 0`` in three places (the fixture, the
``assign_suite_role`` hook, and the three patches themselves). This patch is the
proof, run last: it re-asserts the fixture value and strips "Suite Admin" from
any account that was still a Website User when the migration ended — which, since
nothing above recomputes ``user_type``, is exactly the set of accidental
promotions.

Measured on osiris, 31.08.2026, before the merge: 216 Website Users held
"Drive User", 277 held "Meet User", and 1 held "Mail Admin".
"""

from __future__ import annotations

import frappe


def execute() -> None:
    # //// Neoffice — see the block marker above: added file, backstop patch (470740fd7 "style(fork): ruff format")
    _enforce_role_desk_access()
    _strip_admin_role_from_portal_accounts()
    _report_inconsistent_accounts()


def _enforce_role_desk_access() -> None:
    # //// Neoffice — see the block marker above: added file, backstop patch (470740fd7 "style(fork): ruff format")
    """Re-assert desk access on the two Suite roles, whatever the patches left.

    ``sync_fixtures()`` runs after post_model_sync patches and would do this
    anyway, but only for a site whose fixtures actually sync. Writing it here
    closes the window in which an upstream patch created the role at 1 and
    something saved a User before the fixtures caught up.
    """

    for role, desk_access in (("Suite User", 0), ("Suite Admin", 1)):
        if not frappe.db.exists("Role", role):
            continue
        if frappe.db.get_value("Role", role, "desk_access") != desk_access:
            frappe.db.set_value("Role", role, "desk_access", desk_access, update_modified=False)
            frappe.log_error(
                f"Suite: forced desk_access={desk_access} on role {role}",
                f"A migration left the {role} role with the wrong desk access. "
                f"See suite/suite_core/patches/keep_portal_accounts_off_the_desk.py.",
            )


def _strip_admin_role_from_portal_accounts() -> None:
    # //// Neoffice — see the block marker above: added file, backstop patch (470740fd7 "style(fork): ruff format")
    """Drop "Suite Admin" from accounts that are still Website Users.

    ``rename_mail_admin_to_suite_admin`` renames the Role, which cascades to every
    ``Has Role`` row. On a fleet where "Mail Admin" carried no desk access, its
    holders may be portal accounts — and they would inherit an administrator role
    with desk access. Nobody hands out "Suite Admin" to a Website User on purpose.
    """

    promoted = frappe.get_all(
        "Has Role",
        filters={"parenttype": "User", "role": "Suite Admin"},
        pluck="parent",
    )
    portal = [
        user for user in set(promoted) if frappe.db.get_value("User", user, "user_type") == "Website User"
    ]
    if not portal:
        return

    frappe.db.delete("Has Role", {"parenttype": "User", "role": "Suite Admin", "parent": ("in", portal)})
    frappe.log_error(
        f"Suite: removed Suite Admin from {len(portal)} portal account(s)",
        "The Mail Admin -> Suite Admin rename would have given these Website Users "
        "an administrator role with desk access:\n" + "\n".join(sorted(portal)),
    )


def _report_inconsistent_accounts() -> None:
    # //// Neoffice — see the block marker above: added file, backstop patch (470740fd7 "style(fork): ruff format")
    """Log any account left holding a desk role while typed as a Website User.

    Such an account is a promotion waiting to happen: ``set_system_user`` recomputes
    ``user_type`` from its roles on the next save. We only report — deciding which
    of the two is wrong (the role or the type) needs a human, and silently changing
    either could as easily lock a colleague out of the desk as keep a customer off it.
    """

    desk_roles = set(frappe.get_all("Role", filters={"desk_access": 1}, pluck="name"))
    if not desk_roles:
        return

    rows = frappe.get_all(
        "Has Role",
        filters={"parenttype": "User", "role": ("in", list(desk_roles))},
        fields=["parent", "role"],
    )
    offenders = {
        f"{row.parent} ({row.role})"
        for row in rows
        if frappe.db.get_value("User", row.parent, "user_type") == "Website User"
    }
    if not offenders:
        return

    frappe.log_error(
        f"Suite: {len(offenders)} Website User(s) hold a desk-access role",
        "These accounts are typed as Website Users but carry a role with desk access. "
        "The next User.save() will promote them to System User:\n" + "\n".join(sorted(offenders)),
    )

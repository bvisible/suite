# Copyright (c) 2026, Neoffice and contributors
# For license information, please see license.txt

"""Give back a root folder to any Drive Team that lost one.

A Drive Team gets its root folder from ``after_insert``. Rows that arrive by
any other route never run that hook — and a database restore is exactly such a
route. The team is then present but unopenable: ``get_home_folder`` finds
nothing and Drive answers "This team doesn't exist", which sends you looking
for a missing team rather than a missing folder.

Seen for real on the Lite tenants (2026-08-04). Every tenant cloned from the
2026-07-31 golden had all three of its teams broken, because that golden was
captured while the source instance still ran the legacy `drive` app: the roots
were rows in ``tabDrive File``, provisioning then dropped `drive` from the
installed apps (it is folded into `suite` now), and the drive -> suite data
migration could no longer run — it needs the DocType that had just been
removed. The rows survived in an orphan table nothing reads.

Repairing here rather than in ``get_home_folder`` is deliberate: a read path
that silently creates storage hides the problem instead of fixing it, and it
would fire on every request. A patch runs once, at migrate, where the fleet
already expects schema repairs to happen.

Idempotent and safe to re-run: teams that already have a root are untouched.
"""

import frappe


def execute():
    if not frappe.db.table_exists("Drive Team"):
        return

    # `team` is a custom field on File. Without it there is nothing to query
    # and nothing this patch can do — a later migrate will have installed the
    # fixture and repair the teams then.
    if not frappe.db.has_column("File", "team"):
        frappe.log_error(
            "Drive: File.team column missing",
            "ensure_team_root_folders skipped — the `team` custom field is not on File yet",
        )
        return

    repaired, failed = [], []
    for name in frappe.get_all("Drive Team", pluck="name"):
        if frappe.db.get_value("File", {"team": name, "folder": ["in", ["", None]]}, "name"):
            continue
        try:
            team = frappe.get_doc("Drive Team", name)
            team.ensure_root_folder()
            repaired.append(name)
        except Exception as exc:  # noqa: BLE001 — one bad team must not stop the migrate
            failed.append(f"{name}: {exc}")

    if repaired:
        frappe.db.commit()
        print(f"Drive: created a root folder for {len(repaired)} team(s): {', '.join(repaired)}")
    if failed:
        frappe.log_error(
            "Drive: could not repair some teams"[:140],
            "ensure_team_root_folders failed on:\n" + "\n".join(failed),
        )

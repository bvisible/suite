# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from frappe.model.utils.rename_field import rename_field


def execute() -> None:
    """Rename User Settings.skip_schedule_fetch_changes to disable_push_subscriptions.

    Scheduled change fetching (schedule_fetch_changes) is gone — changes are now fetched
    only on received JMAP push notifications — so the flag's meaning shifts from opting
    out of the scheduler to blocking push subscription creation and renewal entirely.
    """

    rename_field("User Settings", "skip_schedule_fetch_changes", "disable_push_subscriptions")

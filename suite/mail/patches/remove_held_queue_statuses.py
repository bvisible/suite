# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe
from frappe.query_builder.functions import Coalesce


def execute() -> None:
    """Flip Mail Queue rows from the removed Scheduled/Cancelled statuses to Submitted.

    Scheduled sends are now read straight from the server's EmailSubmission objects; the
    queue row only logs that the email was handed over (Submitted), with send_at recording
    the hold and cancelled_at a cancelled one. submitted_at backfills from creation — the
    submission was created then.
    """

    MQ = frappe.qb.DocType("Mail Queue")
    (
        frappe.qb.update(MQ)
        .set(MQ.status, "Submitted")
        .set(MQ.submitted_at, Coalesce(MQ.submitted_at, MQ.creation))
        .where(MQ.status.isin(["Scheduled", "Cancelled"]))
    ).run()

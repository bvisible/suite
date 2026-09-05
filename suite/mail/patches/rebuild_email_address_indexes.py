# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from suite.mail.store import rebuild_all_email_address_indexes


def execute() -> None:
    """Build the email-address search index from data already cached for each JMAP account.

    Re-run whenever the index's schema changes: a changed schema wipes each account's index the next
    time it is opened, leaving suggestions empty until something re-indexes. This fans the accounts
    out into long-queue background jobs (rather than indexing inline during migrate), each
    rebuilding from the cache.
    """

    rebuild_all_email_address_indexes()

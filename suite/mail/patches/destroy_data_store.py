# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from suite.mail.store import destroy_data_store


def execute() -> None:
    """Destroy the on-disk data store so it is rebuilt lazily from JMAP on next access."""

    destroy_data_store()

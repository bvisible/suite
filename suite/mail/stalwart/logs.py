# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from suite.mail.stalwart.service import ManagementService


class LogService(ManagementService):
    """Read access to server log entries (``x:Log``)."""

    type = "Log"
    default_properties = ["id", "timestamp", "level", "event", "details"]
    # The log store rejects offset paging ("Pagination is only possible using anchors for logs").
    cursor_paginated = True

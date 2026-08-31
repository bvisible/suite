from __future__ import annotations
from suite.mail.stalwart.service import ManagementService


class LogService(ManagementService):
    """Read access to server log entries (``x:Log``)."""

    type = "Log"
    default_properties = ["id", "timestamp", "level", "event", "details"]
    # The log store rejects offset paging ("Pagination is only possible using anchors for logs").
    cursor_paginated = True

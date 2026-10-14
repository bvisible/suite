# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from suite.meet.install import add_rate_limits


def execute():
    """Execute patch to add dynamic rate limits for Meet endpoints."""
    add_rate_limits()

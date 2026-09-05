# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from urllib.parse import quote

from suite.mail.utils import get_config


def get_avatar_url(email: str) -> str | None:
    """Returns the Gravatar avatar URL for the given email, or None if Gravatar is disabled.

    Gravatar is a third-party service, so the lookup is opt-in via the "Enable Gravatar" Mail
    Setting. When disabled, callers fall back to showing initials instead.
    """

    if not get_config("enable_gravatar"):
        return None

    return f"/api/method/suite.mail.api.mail.get_avatar?email={quote(email, safe='')}"

from __future__ import annotations
from suite.mail.stalwart.service import ManagementService

# Setting ``nextRetry`` to a time in the past tells Stalwart to attempt delivery immediately.
RETRY_NOW = "2000-01-01T00:00:00Z"


class QueuedMessageService(ManagementService):
    """Read + retry/cancel access to messages pending outbound delivery (``x:QueuedMessage``)."""

    type = "QueuedMessage"
    default_properties = [
        "id",
        "returnPath",
        "recipients",
        "size",
        "priority",
        "envId",
        "flags",
        "nextRetry",
        "nextNotify",
        "receivedFromIp",
        "receivedViaPort",
        "createdAt",
        "blobId",
    ]

    def retry(self, ids: list[str]) -> None:
        """Schedules the given messages for immediate delivery."""

        self.update_many({id: {"nextRetry": RETRY_NOW} for id in ids})

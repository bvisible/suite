# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from suite.mail.stalwart.service import ManagementService, Serializable


class Action(Serializable):
    """A server management action, dispatched by its ``@type`` (see the ``ActionType`` schema enum).

    Most actions are parameterless (reloads, cache invalidation, queue pause/resume). A few carry
    extra input, e.g. ``TroubleshootDmarc`` and ``ClassifySpam``; those extra fields are passed
    through verbatim in ``params``.
    """

    def __init__(self, action_type: str, params: dict | None = None) -> None:
        self.action_type = action_type
        self.params = params or {}

    def to_dict(self) -> dict:
        """Serializes the action to the JMAP wire format (``@type`` plus any parameters)."""

        return {"@type": self.action_type, **self.params}


class ActionService(ManagementService):
    """Executes server management actions (``x:Action``).

    Actions are not queryable objects; running one is a ``set``/create whose created object carries
    any result (e.g. the DMARC troubleshooting outcome or the spam classification score).
    """

    type = "Action"

    def run(self, action_type: str, params: dict | None = None) -> dict:
        """Executes ``action_type`` and returns the created action object, including any result."""

        return self._create(Action(action_type, params))

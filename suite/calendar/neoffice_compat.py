# //// Neoffice — added file (no upstream equivalent): the calendar event service of the JMAP layer upstream replaced,
# //// for the apps of the bench that still ask for it.
# ////
# //// Until the merge of 14.10.2026 `suite.mail.jmap.get_calendar_event_service(account)` gave a service object, and
# //// neoffice_theme's calendar bridge (calendar_bridge.py: the Event <-> Suite sync) and its ICS subscriptions
# //// (calendar_connectors.py) are written against it: `get`, `get_master_ids`, `max_objects_in_set`, and the raw
# //// answers of `_create`, `_get` and `changes`. Upstream's jmaplib layer has none of them (typed calls on a client,
# //// suite/calendar/jmap_events.py). Rather than make every consumer follow in the same deployment, this keeps the
# //// old shape on top of the new client: the same requests, answered as raw JMAP dictionaries, and a refused
# //// request raising httpx's HTTPStatusError, whose `.response.status_code` the bridge reads to tell a mailbox the
# //// server will not authenticate (401). Retire it when the theme calls suite.calendar.jmap_events itself.
from __future__ import annotations

from suite.calendar import jmap_events
from suite.mail.jmap import get_account_client

CORE_URN = "urn:ietf:params:jmap:core"
CALENDARS_URN = "urn:ietf:params:jmap:calendars"


class CalendarEventServiceCompat:
    """The few calls of the old CalendarEventService that neoffice_theme makes."""

    def __init__(self, account: str, ignore_permissions: bool = False) -> None:
        self.account = account
        self.client = get_account_client(account, ignore_permissions=ignore_permissions)

    @property
    def max_objects_in_get(self) -> int:
        return self.client.capabilities.limits.max_objects_in_get

    @property
    def max_objects_in_set(self) -> int:
        return self.client.capabilities.limits.max_objects_in_set

    def _call(self, method: str, **arguments) -> dict:
        """One `CalendarEvent/<method>` call, answered as the raw JMAP response (`methodResponses`)."""

        body = {
            "using": [CORE_URN, CALENDARS_URN],
            "methodCalls": [
                [
                    f"CalendarEvent/{method}",
                    {"accountId": self.account, **{k: v for k, v in arguments.items() if v is not None}},
                    "0",
                ]
            ],
        }
        response = self.client.http.post(self.client.session.api_url, json=body)
        response.raise_for_status()
        return response.json()

    def _create(self, create: dict, **kwargs) -> dict:
        return self._call("set", create=create, **kwargs)

    def _get(self, ids: list[str] | None = None, properties: list[str] | None = None, **kwargs) -> dict:
        return self._call("get", ids=ids, properties=properties, **kwargs)

    def get(self, ids: list[str] | None = None) -> list[dict]:
        """The events (raw JMAP objects) of `ids`, or every event when none are named."""

        return jmap_events.get_events(self.client, ids)

    def get_master_ids(self, uids: list[str]) -> list[str]:
        return jmap_events.get_master_ids(self.client, uids)

    def changes(self, since_state: str) -> dict:
        """What changed since `since_state`: {created, updated, destroyed, newState, ...}. A refusal of the method
        (`cannotCalculateChanges`, `forbidden`) raises, as the old service did."""

        response = self._call("changes", sinceState=since_state)
        for name, body, _call_id in response.get("methodResponses") or []:
            if name == "error":
                raise RuntimeError(f"CalendarEvent/changes failed: {body}")
        if method_responses := response.get("methodResponses"):
            return method_responses[0][1]
        return {}

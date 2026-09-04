#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from dataclasses import dataclass

import frappe
from frappe import _

from suite.mail.stalwart.service import ManagementService


@dataclass
class OAuthClient:
    client_id: str
    description: str | None = None
    contacts: list[str] | None = None
    redirect_uris: list[str] | None = None
    secret: str | None = None
    logo: str | None = None
    expires_at: str | None = None

    def to_dict(self) -> dict:
        """Serializes the OAuth client to the JMAP wire format."""

        return {
            "clientId": self.client_id,
            "description": self.description,
            "contacts": {contact: True for contact in self.contacts} if self.contacts else {},
            "redirectUris": {uri: True for uri in self.redirect_uris} if self.redirect_uris else {},
            "secret": self.secret,
            "logo": self.logo,
            "expiresAt": self.expires_at,
        }


class OAuthClientService(ManagementService):
    type = "OAuthClient"
    default_properties = ["id", "clientId", "description", "contacts", "redirectUris", "expiresAt"]

    def get_by_client_id(
        self, client_id: str, properties: list[str] | None = None, raise_exception: bool = True
    ) -> dict | None:
        """Returns the OAuth client with the given clientId, or ``None`` (throws if ``raise_exception``)."""

        client = self.find({"text": client_id}, properties=properties)
        if client and client.get("clientId") == client_id:
            return client

        if raise_exception:
            frappe.throw(_("OAuth client {0} not found on the Stalwart server.").format(client_id))

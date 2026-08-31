from __future__ import annotations
from dataclasses import dataclass, field

import frappe
from frappe import _

from suite.mail.stalwart.account import Permissions
from suite.mail.stalwart.service import ManagementService


@dataclass
class AppPassword:
    description: str
    permissions: Permissions = field(default_factory=Permissions)
    allowed_ips: list[str] | None = None
    expires_at: str | None = None

    def to_dict(self) -> dict:
        """Serializes the app password to the JMAP wire format."""

        payload = {"description": self.description, "permissions": self.permissions.to_dict()}
        if self.allowed_ips:
            payload["allowedIps"] = list(self.allowed_ips)
        if self.expires_at:
            payload["expiresAt"] = self.expires_at

        return payload


class AppPasswordService(ManagementService):
    """App Passwords are account-scoped, so this service needs a connection authenticated as the
    target account (see ``get_app_password_service``)."""

    type = "AppPassword"

    def create(self, app_password: AppPassword) -> str:
        """Creates an app password and returns the generated secret.

        Returns the secret rather than the id because the server only exposes it at creation time.
        """

        secret = self._create(app_password).get("secret")
        if not secret:
            frappe.throw(_("The Stalwart server did not return a generated app password secret."))

        return secret

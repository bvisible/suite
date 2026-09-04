# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from uuid import uuid7

from frappe.model.document import Document


class MailClusterStoreHTTPAuth(Document):
    def autoname(self) -> None:
        self.name = str(uuid7())

    @property
    def config(self) -> dict:
        """Returns the configuration for the HTTP Auth cluster store."""

        config = {}

        if self.type == "Basic":
            config.update(
                {
                    "username": self.username,
                    "secret": self.get_password("secret") if self.secret else None,
                }
            )

        elif self.type == "Bearer":
            config["bearerToken"] = self.get_password("bearer_token") if self.bearer_token else None

        return config

    def validate(self) -> None:
        if not self.description:
            self.description = self.type

from __future__ import annotations
from dataclasses import dataclass, field

import frappe
from frappe import _

from suite.mail.stalwart.service import ManagementService


@dataclass
class Role:
    description: str
    role_ids: list[str] = field(default_factory=list)
    enabled_permissions: list[str] = field(default_factory=list)
    disabled_permissions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serializes the role to the JMAP wire format.

        ``roleIds`` and the permission sets are id-keyed maps on the wire, not arrays.
        """

        return {
            "description": self.description,
            "roleIds": {role_id: True for role_id in self.role_ids},
            "enabledPermissions": {perm: True for perm in self.enabled_permissions},
            "disabledPermissions": {perm: True for perm in self.disabled_permissions},
        }


class RoleService(ManagementService):
    type = "Role"
    default_properties = ["id", "description", "roleIds", "enabledPermissions", "disabledPermissions"]

    def get_by_description(
        self, description: str, properties: list[str] | None = None, raise_exception: bool = True
    ) -> dict | None:
        """Returns the role with the given description, or ``None`` (throws if ``raise_exception``)."""

        role = self.find({"description": description}, properties=properties or ["id", "description"])
        if not role and raise_exception:
            frappe.throw(_("Role {0} not found on the Stalwart server.").format(description))

        return role

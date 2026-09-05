# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from dataclasses import dataclass, field

from suite.mail.stalwart.account import (
    AccountService,
    CustomRoles,
    EmailAlias,
    Permissions,
    RoleType,
    StorageQuota,
    UserRoles,
)


@dataclass
class Group:
    """A group principal. Groups share the ``x:Account`` object with users but carry no
    credentials and are distinguished by the ``@type: "Group"`` discriminator."""

    name: str
    domain_id: str
    role_ids: list[str] | None = None
    permissions: Permissions = field(default_factory=Permissions)
    quotas: StorageQuota = field(default_factory=StorageQuota)
    aliases: list[EmailAlias] | None = None
    description: str | None = None

    def to_dict(self) -> dict:
        """Serializes the group to the JMAP wire format (an ``x:Account`` with ``@type: Group``).

        Groups carry no ``memberGroupIds`` — membership lives on each member account instead.
        """

        payload = {
            "@type": "Group",
            "name": self.name,
            "domainId": self.domain_id,
            "permissions": self.permissions.to_dict() if self.permissions else {},
            "quotas": self.quotas.to_dict() if self.quotas else {},
            "aliases": {f"{idx}": a.to_dict() for idx, a in enumerate(self.aliases)} if self.aliases else {},
            "description": self.description,
        }

        if self.role_ids:
            payload["roles"] = UserRoles(
                type=RoleType.CUSTOM, roles=CustomRoles(role_ids=self.role_ids)
            ).to_dict()

        return payload


class GroupService(AccountService):
    """Groups live in the same ``x:Account`` collection as users."""

    def get_all_groups(self, properties: list[str] | None = None) -> list[dict]:
        """Returns every group principal."""

        return self.get_all(filter={"@type": "Group"}, properties=properties)

    def get_members(self, group_id: str, properties: list[str] | None = None) -> list[dict]:
        """Returns the accounts that belong to the group.

        Membership lives on each member account's ``memberGroupIds``, not on the group itself.
        """

        return self.get_all(filter={"memberGroupIds": group_id}, properties=properties)

    def add_members(self, group_id: str, account_ids: list[str]) -> None:
        """Adds the given accounts to the group by patching each account's membership."""

        for account_id in account_ids:
            self.update(account_id, {f"memberGroupIds/{group_id}": True})

    def remove_members(self, group_id: str, account_ids: list[str]) -> None:
        """Removes the given accounts from the group by patching each account's membership."""

        for account_id in account_ids:
            self.update(account_id, {f"memberGroupIds/{group_id}": None})

    def set_members(self, group_id: str, account_ids: list[str]) -> None:
        """Reconciles the group's membership to exactly ``account_ids``."""

        current = {m["id"] for m in self.get_members(group_id, properties=["id"])}
        desired = set(account_ids)
        self.add_members(group_id, list(desired - current))
        self.remove_members(group_id, list(current - desired))

    def delete(self, ids: str | list[str]) -> None:
        """Deletes groups, first clearing membership so the server's link check passes.

        Stalwart refuses to destroy a group while accounts still reference it as a member.
        """

        ids = [ids] if isinstance(ids, str) else list(ids)
        for group_id in ids:
            if member_ids := [m["id"] for m in self.get_members(group_id, properties=["id"])]:
                self.remove_members(group_id, member_ids)

        super().delete(ids)

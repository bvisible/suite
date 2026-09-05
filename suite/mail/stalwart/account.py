# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

import frappe
from frappe import _
from frappe.utils import random_string

from suite.mail.stalwart.service import ManagementService
from suite.utils import snake_to_camel

# Stalwart requires every account to carry a locale, so one is picked when none was chosen.
DEFAULT_LOCALE = "en_US"


class CredentialType(Enum):
    PASSWORD = "Password"


@dataclass
class PasswordCredential:
    secret: str


def _default_password_credential() -> PasswordCredential:
    """Returns a password credential seeded with a random secret."""

    return PasswordCredential(secret=random_string(20))


def _default_credentials() -> list[Credential]:
    """Returns the default credential list (a single random password)."""

    return [Credential()]


@dataclass
class Credential:
    type: CredentialType = CredentialType.PASSWORD
    password: PasswordCredential = field(default_factory=_default_password_credential)

    def to_dict(self) -> dict:
        """Serializes the credential to the JMAP wire format."""

        if self.type == CredentialType.PASSWORD:
            return {"@type": self.type.value, "secret": self.password.secret}

        raise ValueError(f"Unsupported credential type: {self.type}")


class RoleType(Enum):
    USER = "User"
    ADMIN = "Admin"
    CUSTOM = "Custom"


@dataclass
class CustomRoles:
    role_ids: list[str] = field(default_factory=list)


@dataclass
class UserRoles:
    type: RoleType = RoleType.USER
    roles: CustomRoles | None = None

    def __post_init__(self) -> None:
        """Validates that role ids are present only for the custom role type."""

        if self.type == RoleType.CUSTOM and not self.roles:
            raise ValueError("Custom role type requires roles to be defined.")

        if self.type != RoleType.CUSTOM and self.roles:
            raise ValueError("Only custom role type can have roles defined.")

    def to_dict(self) -> dict:
        """Serializes the roles tagged union to the JMAP wire format."""

        if self.type == RoleType.CUSTOM:
            return {"@type": self.type.value, "roleIds": {role_id: True for role_id in self.roles.role_ids}}

        return {"@type": self.type.value}


class PermissionType(Enum):
    INHERIT = "Inherit"
    MERGE = "Merge"
    REPLACE = "Replace"


@dataclass
class PermissionsList:
    enabled_permissions: list[str] | None = None
    disabled_permissions: list[str] | None = None


@dataclass
class Permissions:
    type: PermissionType = PermissionType.INHERIT
    permissions: PermissionsList | None = None

    def __post_init__(self) -> None:
        """Validates that a permission list is present unless the type is Inherit."""

        has_permissions = self.permissions and (
            self.permissions.enabled_permissions or self.permissions.disabled_permissions
        )

        if self.type == PermissionType.INHERIT and has_permissions:
            raise ValueError("Inherit permission type cannot define enabled or disabled permissions.")

        if self.type != PermissionType.INHERIT and not has_permissions:
            raise ValueError("Merge or Replace permission type requires enabled or disabled permissions.")

    def to_dict(self) -> dict:
        """Serializes the permissions tagged union to the JMAP wire format."""

        if self.type == PermissionType.INHERIT:
            return {"@type": self.type.value}

        return {
            "@type": self.type.value,
            "enabledPermissions": {perm: True for perm in self.permissions.enabled_permissions}
            if self.permissions and self.permissions.enabled_permissions
            else {},
            "disabledPermissions": {perm: True for perm in self.permissions.disabled_permissions}
            if self.permissions and self.permissions.disabled_permissions
            else {},
        }


@dataclass
class StorageQuota:
    max_emails: int | None = None
    max_mailboxes: int | None = None
    max_email_submissions: int | None = None
    max_email_identities: int | None = None
    max_participant_identities: int | None = None
    max_sieve_scripts: int | None = None
    max_push_subscriptions: int | None = None
    max_calendars: int | None = None
    max_calendar_events: int | None = None
    max_calendar_event_notifications: int | None = None
    max_address_books: int | None = None
    max_contact_cards: int | None = None
    max_files: int | None = None
    max_folders: int | None = None
    max_masked_addresses: int | None = None
    max_app_passwords: int | None = None
    max_api_keys: int | None = None
    max_public_keys: int | None = None
    max_disk_quota: int | None = None

    def __post_init__(self) -> None:
        """Rejects any negative quota value."""

        for field_name, value in self.__dict__.items():
            if value is not None and value < 0:
                raise ValueError(f"{field_name} cannot be negative")

    def to_dict(self) -> dict:
        """Serializes the set quotas to a camelCase JMAP map, omitting unset limits."""

        return {snake_to_camel(name): value for name, value in self.__dict__.items() if value is not None}


@dataclass
class EmailAlias:
    name: str
    domain_id: str
    enabled: bool = True
    description: str | None = None

    def to_dict(self) -> dict:
        """Serializes the alias to the JMAP wire format."""

        return {
            "name": self.name,
            "domainId": self.domain_id,
            "enabled": self.enabled,
            "description": self.description,
        }


class EncryptionType(Enum):
    DISABLED = "Disabled"
    AES128 = "Aes128"
    AES256 = "Aes256"


@dataclass
class EncryptionSettings:
    public_key_id: str
    encrypt_on_append: bool = False
    allow_spam_training: bool = False

    def to_dict(self) -> dict:
        """Serializes the encryption settings to the JMAP wire format."""

        return {
            "publicKey": self.public_key_id,
            "encryptOnAppend": self.encrypt_on_append,
            "allowSpamTraining": self.allow_spam_training,
        }


@dataclass
class EncryptionAtRest:
    type: EncryptionType = EncryptionType.DISABLED
    settings: EncryptionSettings | None = None

    def __post_init__(self) -> None:
        """Validates that settings are present only when encryption is enabled."""

        if self.type != EncryptionType.DISABLED and not self.settings:
            raise ValueError("Encryption settings must be provided when encryption is enabled.")

        if self.type == EncryptionType.DISABLED and self.settings:
            raise ValueError("Encryption settings should not be provided when encryption is disabled.")

    def to_dict(self) -> dict:
        """Serializes the encryption-at-rest tagged union to the JMAP wire format."""

        if self.type == EncryptionType.DISABLED:
            return {"@type": self.type.value}

        return {"@type": self.type.value, "settings": self.settings.to_dict()}


@dataclass
class Account:
    name: str
    domain_id: str
    credentials: list[Credential] = field(default_factory=_default_credentials)
    member_group_ids: list[str] | None = None
    roles: UserRoles = field(default_factory=UserRoles)
    permissions: Permissions = field(default_factory=Permissions)
    quotas: StorageQuota = field(default_factory=StorageQuota)
    aliases: list[EmailAlias] | None = None
    description: str | None = None
    locale: str = DEFAULT_LOCALE
    timezone: str | None = None
    encryption_at_rest: EncryptionAtRest = field(default_factory=EncryptionAtRest)

    def to_dict(self) -> dict:
        """Serializes the account to the JMAP wire format."""

        return {
            "@type": "User",
            "name": self.name,
            "domainId": self.domain_id,
            # credentials, memberGroupIds and aliases are id-keyed maps on the wire, not arrays.
            "credentials": {f"{idx}": c.to_dict() for idx, c in enumerate(self.credentials)}
            if self.credentials
            else {},
            "memberGroupIds": {group_id: True for group_id in self.member_group_ids}
            if self.member_group_ids
            else {},
            "roles": self.roles.to_dict() if self.roles else {},
            "permissions": self.permissions.to_dict() if self.permissions else {},
            "quotas": self.quotas.to_dict() if self.quotas else {},
            "aliases": {f"{idx}": a.to_dict() for idx, a in enumerate(self.aliases)} if self.aliases else {},
            "description": self.description,
            "locale": self.locale,
            "timeZone": self.timezone,
            "encryptionAtRest": self.encryption_at_rest.to_dict(),
        }


class AccountService(ManagementService):
    type = "Account"
    default_properties = [
        "@type",
        "id",
        "name",
        "description",
        "emailAddress",
        "aliases",
        "domainId",
        "locale",
        "memberGroupIds",
        "quotas",
        "roles",
        "timeZone",
        "usedDiskQuota",
    ]

    def get_by_name(
        self, name: str, properties: list[str] | None = None, raise_exception: bool = True
    ) -> dict | None:
        """Returns the account with the given name, or ``None`` (throws if ``raise_exception``)."""

        account = self.find({"name": name}, properties=properties or ["id"])
        if not account and raise_exception:
            frappe.throw(_("Account {0} not found on the Stalwart server.").format(name))

        return account

    def _current_role_ids(self, account_id: str) -> list[str]:
        """Returns the account's currently assigned custom role ids."""

        roles = (self.get(account_id, properties=["roles"]) or {}).get("roles") or {}
        role_ids = roles.get("roleIds") or {}
        return list(role_ids.keys() if isinstance(role_ids, dict) else role_ids)

    def _set_roles(self, account_id: str, role_ids: list[str]) -> None:
        """Replaces the account's roles with the given ids (empty reverts to the default user role)."""

        # roles is a tagged union; its @type discriminator can't be patched via a sub-path, so the
        # whole field is replaced.
        if role_ids:
            roles = UserRoles(type=RoleType.CUSTOM, roles=CustomRoles(role_ids=list(dict.fromkeys(role_ids))))
        else:
            roles = UserRoles(type=RoleType.USER)

        self.update(account_id, {"roles": roles.to_dict()})

    def add_roles(self, account_id: str, role_ids: list[str]) -> None:
        """Adds role ids to the account, keeping any it already has."""

        if role_ids:
            self._set_roles(account_id, [*self._current_role_ids(account_id), *role_ids])

    def remove_roles(self, account_id: str, role_ids: list[str]) -> None:
        """Removes the given role ids from the account."""

        if role_ids:
            remove = set(role_ids)
            self._set_roles(account_id, [r for r in self._current_role_ids(account_id) if r not in remove])

    def set_password(self, account_id: str, new_password: str) -> None:
        """Sets the account's primary password credential, leaving other credentials intact."""

        if not new_password:
            frappe.throw(_("New password cannot be empty."))

        credentials = (self.get(account_id, properties=["credentials"]) or {}).get("credentials") or {}
        row_id = next(
            (idx for idx, c in credentials.items() if c.get("@type") == CredentialType.PASSWORD.value), "0"
        )

        self.update(account_id, {f"credentials/{row_id}/secret": new_password})

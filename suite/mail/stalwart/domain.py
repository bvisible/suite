#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

import frappe
from frappe import _

from suite.mail.stalwart.service import ManagementService


class CertificateManagementType(Enum):
    MANUAL = "Manual"
    AUTOMATIC = "Automatic"


@dataclass
class CertificateManagementProperties:
    acme_provider_id: str
    subject_alternative_names: list[str] | None = None


@dataclass
class CertificateManagement:
    type: CertificateManagementType = CertificateManagementType.MANUAL
    properties: CertificateManagementProperties | None = None

    def __post_init__(self) -> None:
        """Validates that properties are present only for automatic management."""

        if self.type == CertificateManagementType.AUTOMATIC and not self.properties:
            raise ValueError("Properties must be provided for automatic certificate management.")
        if self.type == CertificateManagementType.MANUAL and self.properties:
            raise ValueError("Properties should not be provided for manual certificate management.")

    def to_dict(self) -> dict:
        """Serializes the certificate management tagged union to the JMAP wire format."""

        if self.type == CertificateManagementType.MANUAL:
            return {"@type": self.type.value}

        return {
            "@type": self.type.value,
            "acmeProviderId": self.properties.acme_provider_id,
            "subjectAlternativeNames": self.properties.subject_alternative_names,
        }


class DkimManagementType(Enum):
    MANUAL = "Manual"
    AUTOMATIC = "Automatic"


class DkimSignatureType(Enum):
    DKIM1_ED25519_SHA256 = "Dkim1Ed25519Sha256"
    DKIM_RSA_SHA256 = "Dkim1RsaSha256"


@dataclass
class DkimManagementProperties:
    algorithms: list[DkimSignatureType] = field(
        default_factory=lambda: [
            DkimSignatureType.DKIM1_ED25519_SHA256,
            DkimSignatureType.DKIM_RSA_SHA256,
        ]
    )
    selector_template: str = "v{version}-{algorithm}-{date-%Y%m%d}"
    rotate_after: int = 90 * 24 * 60 * 60 * 1000
    retire_after: int = 7 * 24 * 60 * 60 * 1000
    delete_after: int = 30 * 24 * 60 * 60 * 1000


@dataclass
class DkimManagement:
    type: DkimManagementType = DkimManagementType.AUTOMATIC
    properties: DkimManagementProperties = field(default_factory=DkimManagementProperties)

    def __post_init__(self) -> None:
        """Validates that properties are present only for automatic management."""

        if self.type == DkimManagementType.AUTOMATIC and not self.properties:
            raise ValueError("Properties must be provided for automatic DKIM management.")
        if self.type == DkimManagementType.MANUAL and self.properties:
            raise ValueError("Properties should not be provided for manual DKIM management.")

    def to_dict(self) -> dict:
        """Serializes the DKIM management tagged union to the JMAP wire format."""

        if self.type == DkimManagementType.MANUAL:
            return {"@type": self.type.value}

        return {
            "@type": self.type.value,
            "algorithms": {algorithm.value: True for algorithm in self.properties.algorithms}
            if self.properties.algorithms
            else {},
            "selectorTemplate": self.properties.selector_template,
            "rotateAfter": self.properties.rotate_after,
            "retireAfter": self.properties.retire_after,
            "deleteAfter": self.properties.delete_after,
        }


class DnsManagementType(Enum):
    MANUAL = "Manual"
    AUTOMATIC = "Automatic"


class DnsRecordType(Enum):
    DKIM = "dkim"
    TLSA = "tlsa"
    SPF = "spf"
    MX = "mx"
    DMARC = "dmarc"
    SRV = "srv"
    MTA_STS = "mtaSts"
    TLS_RPT = "tlsRpt"
    CAA = "caa"
    AUTO_CONFIG = "autoConfig"
    AUTO_CONFIG_LEGACY = "autoConfigLegacy"
    AUTO_DISCOVER = "autoDiscover"


@dataclass
class DnsManagementProperties:
    dns_server_id: str
    origin: str | None = None
    publish_records: list[DnsRecordType] = field(
        default_factory=lambda: [
            DnsRecordType.DKIM,
            DnsRecordType.SPF,
            DnsRecordType.MX,
            DnsRecordType.DMARC,
            DnsRecordType.SRV,
            DnsRecordType.MTA_STS,
            DnsRecordType.TLS_RPT,
            DnsRecordType.CAA,
            DnsRecordType.AUTO_CONFIG,
            DnsRecordType.AUTO_CONFIG_LEGACY,
            DnsRecordType.AUTO_DISCOVER,
        ]
    )


@dataclass
class DnsManagement:
    type: DnsManagementType = DnsManagementType.MANUAL
    properties: DnsManagementProperties | None = None

    def __post_init__(self) -> None:
        """Validates that properties are present only for automatic management."""

        if self.type == DnsManagementType.AUTOMATIC and not self.properties:
            raise ValueError("Properties must be provided for automatic DNS management.")
        if self.type == DnsManagementType.MANUAL and self.properties:
            raise ValueError("Properties should not be provided for manual DNS management.")

    def to_dict(self) -> dict:
        """Serializes the DNS management tagged union to the JMAP wire format."""

        if self.type == DnsManagementType.MANUAL:
            return {"@type": self.type.value}

        return {
            "@type": self.type.value,
            "dnsServerId": self.properties.dns_server_id,
            "origin": self.properties.origin,
            "publishRecords": [record.value for record in self.properties.publish_records],
        }


class SubAddressingType(Enum):
    DISABLED = "Disabled"
    ENABLED = "Enabled"
    CUSTOM = "Custom"


@dataclass
class SubAddressingCustom:
    custom_rule: str


@dataclass
class SubAddressing:
    type: SubAddressingType = SubAddressingType.ENABLED
    properties: SubAddressingCustom | None = None

    def __post_init__(self) -> None:
        """Validates that a custom rule is present only for custom sub-addressing."""

        if self.type == SubAddressingType.CUSTOM and not self.properties:
            raise ValueError("Properties must be provided for custom sub-addressing.")
        if self.type != SubAddressingType.CUSTOM and self.properties:
            raise ValueError("Properties should not be provided for non-custom sub-addressing.")

    def to_dict(self) -> dict:
        """Serializes the sub-addressing tagged union to the JMAP wire format."""

        if self.type != SubAddressingType.CUSTOM:
            return {"@type": self.type.value}

        return {"@type": self.type.value, "customRule": self.properties.custom_rule}


@dataclass
class Domain:
    name: str
    aliases: list[str] | None = None
    is_enabled: bool = True
    description: str | None = None
    certificate_management: CertificateManagement = field(default_factory=CertificateManagement)
    dkim_management: DkimManagement = field(default_factory=DkimManagement)
    dns_management: DnsManagement = field(default_factory=DnsManagement)
    catch_all_address: str | None = None
    sub_addressing: SubAddressing = field(default_factory=SubAddressing)
    allow_relaying: bool = False
    report_address_uri: str | None = "mailto:postmaster"

    def to_dict(self) -> dict:
        """Serializes the domain to the JMAP wire format."""

        return {
            "name": self.name,
            "aliases": {alias: True for alias in self.aliases} if self.aliases else {},
            "isEnabled": self.is_enabled,
            "description": self.description,
            "certificateManagement": self.certificate_management.to_dict(),
            "dkimManagement": self.dkim_management.to_dict(),
            "dnsManagement": self.dns_management.to_dict(),
            "catchAllAddress": self.catch_all_address,
            "subAddressing": self.sub_addressing.to_dict(),
            "allowRelaying": self.allow_relaying,
            "reportAddressUri": self.report_address_uri,
        }


class DomainService(ManagementService):
    type = "Domain"
    default_properties = ["id", "name", "description", "isEnabled", "createdAt"]

    def get_by_name(
        self, name: str, properties: list[str] | None = None, raise_exception: bool = True
    ) -> dict | None:
        """Returns the domain with the given name, or ``None`` (throws if ``raise_exception``)."""

        domain = self.find({"name": name}, properties=properties or ["id"])
        if not domain and raise_exception:
            frappe.throw(_("Domain {0} not found on the Stalwart server.").format(name))

        return domain

    def delete(self, ids: str | list[str]) -> None:
        """Deletes domains, first removing DKIM signatures that would block the delete."""

        # Stalwart refuses to delete a domain while DKIM signatures still reference it.
        ids = [ids] if isinstance(ids, str) else list(ids)
        dkim_service = DkimSignatureService(self.connection)
        for domain_id in ids:
            if signature_ids := [s["id"] for s in dkim_service.get_all_by_domain(domain_id)]:
                dkim_service.delete(signature_ids)

        super().delete(ids)


class DkimSignatureService(ManagementService):
    type = "DkimSignature"
    default_properties = ["id", "selector", "domainId", "stage"]

    def get_all_by_domain(self, domain_id: str, properties: list[str] | None = None) -> list[dict]:
        """Returns every DKIM signature linked to the given domain."""

        return self.get_all(filter={"domainId": domain_id}, properties=properties)

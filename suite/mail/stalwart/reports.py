from __future__ import annotations
from suite.mail.stalwart.service import ManagementService

# Common metadata carried by every received (external) report.
_EXTERNAL_PROPERTIES = ["id", "from", "subject", "to", "receivedAt", "expiresAt", "memberTenantId", "report"]
# Common metadata carried by every generated (internal / outbound) report.
_INTERNAL_PROPERTIES = ["id", "domain", "createdAt", "deliverAt", "report"]


class DmarcExternalReportService(ManagementService):
    """Received DMARC aggregate reports (``x:DmarcExternalReport``)."""

    type = "DmarcExternalReport"
    default_properties = _EXTERNAL_PROPERTIES


class DmarcInternalReportService(ManagementService):
    """Outbound DMARC aggregate reports Stalwart generates (``x:DmarcInternalReport``)."""

    type = "DmarcInternalReport"
    default_properties = [*_INTERNAL_PROPERTIES, "rua", "policyIdentifier"]


class TlsExternalReportService(ManagementService):
    """Received TLS reports (``x:TlsExternalReport``)."""

    type = "TlsExternalReport"
    default_properties = _EXTERNAL_PROPERTIES


class TlsInternalReportService(ManagementService):
    """Outbound TLS reports Stalwart generates (``x:TlsInternalReport``)."""

    type = "TlsInternalReport"
    default_properties = [*_INTERNAL_PROPERTIES, "mailRua", "httpRua", "policyIdentifiers"]


class ArfExternalReportService(ManagementService):
    """Received ARF feedback reports (``x:ArfExternalReport``)."""

    type = "ArfExternalReport"
    default_properties = _EXTERNAL_PROPERTIES

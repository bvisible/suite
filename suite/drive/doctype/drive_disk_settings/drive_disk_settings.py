# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe
from frappe.model.document import Document

from suite.drive.webdav import ALLOWED_METHODS, parse_webdav_methods


class DriveDiskSettings(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        aws_key: DF.Data | None
        aws_secret: DF.Password | None
        bucket: DF.Data | None
        enabled: DF.Check
        endpoint_url: DF.Data | None
        flat: DF.Check
        preview_size: DF.Int
        quota: DF.Int
        root_folder: DF.Data | None
        signature_version: DF.Data | None
        thumbnail_prefix: DF.Data | None
        webdav_allowed_methods: DF.SmallText | None
        webdav_enabled: DF.Check
    # end: auto-generated types

    def validate(self):
        # A mirrored tree on S3 means a folder move copies and deletes every object
        # under it, which times out on large folders.
        if self.enabled:
            self.flat = 1
        self._validate_webdav_methods()
        # //// Neoffice — the S3 endpoint is a public storage service (neoffice-maintenance#2296), see below
        self._validate_endpoint_url()

    # //// Neoffice — added (neoffice-maintenance#2296): Suite Admin, a role of the client's own admin, set the endpoint
    # //// the Drive's S3 client calls with no check, and the server then sent signed requests to an address of its
    # //// choosing (a metadata service, a loopback port, a host of our network) and gave back what they answered. An
    # //// endpoint set by anyone but Administrator is an http(s) URL whose host resolves to public addresses only.
    def _validate_endpoint_url(self):
        if not self.endpoint_url or frappe.session.user == "Administrator":
            return
        if not self.is_new():
            before = self.get_doc_before_save()
            if before is not None and before.endpoint_url == self.endpoint_url:
                return
        import ipaddress
        import socket
        from urllib.parse import urlsplit

        refused = frappe._("The storage endpoint must be a public http(s) address")
        try:
            parts = urlsplit(self.endpoint_url.strip())
            port = parts.port
        except ValueError:
            frappe.throw(refused, frappe.ValidationError)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            frappe.throw(refused, frappe.ValidationError)
        try:
            infos = socket.getaddrinfo(parts.hostname, port or (443 if parts.scheme == "https" else 80))
        except (socket.gaierror, UnicodeError):
            frappe.throw(refused, frappe.ValidationError)
        for info in infos:
            address = ipaddress.ip_address(info[4][0].split("%", 1)[0])
            if not address.is_global:
                frappe.throw(refused, frappe.ValidationError)

    def _validate_webdav_methods(self):
        methods, unknown = parse_webdav_methods(self.webdav_allowed_methods)
        if unknown:
            frappe.throw(
                "Unsupported WebDAV method(s): {}. Valid methods are: {}".format(
                    ", ".join(unknown), ", ".join(ALLOWED_METHODS)
                ),
                frappe.ValidationError,
            )
        # store the canonical form, implied methods (OPTIONS, GET→HEAD) included
        self.webdav_allowed_methods = (
            ", ".join(methods) if self.webdav_allowed_methods and self.webdav_allowed_methods.strip() else ""
        )

    def __getattribute__(self, attr):
        """
        We want explicit denial of , so require '/' at the DB level.
        However, this causes a lot of problems with `Path`, so override empty prefixes.
        """
        val = object.__getattribute__(self, attr)
        if attr == "root_folder":
            return val if val and val != "/" else ""
        return val

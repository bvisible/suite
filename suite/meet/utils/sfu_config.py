# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from urllib.parse import urlparse

import frappe
from frappe.utils.caching import redis_cache


@redis_cache(ttl=5 * 60)
def get_sfu_config():
    """Get SFU configuration from site config or defaults"""
    return {
        "sfu_server_url": frappe.conf.get("sfu_server_url", "http://localhost"),
        "sfu_server_port": frappe.conf.get("sfu_server_port", 3000),
        "sfu_secret": frappe.conf.get("sfu_secret", ""),
    }


def get_tenant() -> str:
    """Unique tenant id for this site, injected into the SFU JWT.

    #//// Neoffice — added function (no upstream equivalent), ported from
    #//// bvisible/meet. Upstream assumes one SFU per site; the fleet shares ONE
    #//// central SFU (neoservice) across every instance, and every instance has
    #//// the same `frappe.local.site` ("prod.local"), so the SFU cannot tell them
    #//// apart. It prefixes room names with this `tenant` claim instead — without
    #//// it, two customers dialing "standup" land in the same room. The public
    #//// hostname is the one thing that is unique per instance.
    #////
    #//// Order: `sfu_tenant` override -> `host_name` (scheme-stripped) -> site.
    """
    explicit = frappe.conf.get("sfu_tenant")
    if explicit:
        return str(explicit)
    host_name = frappe.conf.get("host_name")
    if host_name:
        parsed = urlparse(host_name)
        return parsed.hostname or host_name.rstrip("/")
    return frappe.local.site

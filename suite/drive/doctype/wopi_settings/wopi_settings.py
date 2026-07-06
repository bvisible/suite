# Copyright (c) 2025, Neoservice and contributors
# For license information, please see license.txt

from __future__ import annotations

import secrets

import frappe
import requests
from frappe import _
from frappe.model.document import Document


class WOPISettings(Document):
    def validate(self):
        if not self.jwt_secret:
            self.jwt_secret = secrets.token_hex(32)

    @frappe.whitelist()
    def test_connection(self):
        """Test connection to Collabora server."""
        if not self.collabora_server_url:
            frappe.throw(_("Collabora Server URL is required"))

        try:
            # Test discovery endpoint
            discovery_url = f"{self.collabora_server_url.rstrip('/')}/hosting/discovery"
            response = requests.get(discovery_url, timeout=10)

            if response.status_code == 200:
                self.connection_status = "Connected"
                self.last_check = frappe.utils.now()
                self.save()
                return {"success": True, "message": _("Connection successful")}
            else:
                self.connection_status = f"Error: HTTP {response.status_code}"
                self.last_check = frappe.utils.now()
                self.save()
                return {"success": False, "message": f"HTTP {response.status_code}"}

        except requests.exceptions.Timeout:
            self.connection_status = "Error: Connection timeout"
            self.last_check = frappe.utils.now()
            self.save()
            return {"success": False, "message": _("Connection timeout")}
        except requests.exceptions.ConnectionError as e:
            self.connection_status = "Error: Connection failed"
            self.last_check = frappe.utils.now()
            self.save()
            return {"success": False, "message": str(e)}
        except Exception as e:
            self.connection_status = f"Error: {str(e)}"
            self.last_check = frappe.utils.now()
            self.save()
            return {"success": False, "message": str(e)}


def get_wopi_settings():
    """Get WOPI settings from DocType."""
    try:
        settings = frappe.get_single("WOPI Settings")
        return {
            "enabled": settings.enabled,
            "collabora_server_url": settings.collabora_server_url,
            "jwt_secret": settings.get_password("jwt_secret") if settings.jwt_secret else None,
            "jwt_expiry_hours": settings.jwt_expiry_hours or 10,
        }
    except Exception:
        return {
            "enabled": False,
            "collabora_server_url": None,
            "jwt_secret": None,
            "jwt_expiry_hours": 10,
        }

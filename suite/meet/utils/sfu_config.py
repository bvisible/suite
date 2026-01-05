# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe


def get_sfu_config():
	"""Get SFU configuration from site config or defaults"""
	return {
		"sfu_server_url": frappe.conf.get("sfu_server_url", "http://localhost"),
		"sfu_server_port": frappe.conf.get("sfu_server_port", 3000),
		"sfu_secret": frappe.conf.get("sfu_secret", ""),
	}

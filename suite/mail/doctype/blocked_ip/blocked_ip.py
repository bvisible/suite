# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from mail.mail_server import get_mail_server_api
from mail.utils import extract_filter_values, rename_keys


class BlockedIP(Document):
	def db_insert(self, *args, **kwargs) -> None:
		raise NotImplementedError

	def load_from_db(self) -> "BlockedIP":
		raise NotImplementedError

	def db_update(self) -> None:
		raise NotImplementedError

	def delete(self) -> None:
		raise NotImplementedError

	@staticmethod
	def get_list(filters=None, page_length=20, **kwargs) -> list:
		filters = filters or []
		cluster, text = extract_filter_values(filters, [{"cluster": "="}, {"text": "like"}])

		if cluster:
			blocked_ips = fetch_blocked_ips(cluster, limit=page_length, text=text)
			if not blocked_ips:
				frappe.msgprint(_("No blocked IPs found."), alert=True)

			return blocked_ips

		frappe.msgprint(_("Please select a cluster to view blocked IPs."), alert=True)
		return []

	@staticmethod
	def get_count(filters=None, **kwargs) -> int:
		filters = filters or []
		cluster, text = extract_filter_values(filters, [{"cluster": "="}, {"text": "like"}])

		return frappe.cache.get_value(get_total_cache_key(cluster, text)) if cluster else 0

	@staticmethod
	def get_stats(**kwargs) -> dict:
		return {}


def get_total_cache_key(cluster_name: str, text: str | None = None) -> str:
	"""Returns a cache key for total blocked IP count."""

	text = text or ""
	return f"{cluster_name}:blocked-ip:{text}:total"


def fetch_blocked_ips(cluster_name: str, page: int = 1, limit: int = 10, text: str | None = None) -> list:
	"""Fetches a list of blocked ips from the mail server."""

	server_api = get_mail_server_api(cluster_name)
	response = server_api.request(
		method="GET",
		endpoint="api/settings/group",
		params={"page": page, "prefix": "server.blocked-ip", "limit": limit, "filter": text},
	)

	if response.status_code == 200:
		data = response.json()["data"]
		frappe.cache.set_value(get_total_cache_key(cluster_name, text), data["total"], expires_in_sec=600)

		return [format_blocked_ip(item, cluster_name) for item in data["items"]]

	frappe.throw(title=_("Request failed for {0}").format(server_api.base_url), msg=response.text)


def format_blocked_ip(blocked_ip: dict, cluster_name: str) -> dict:
	"""Formats a blocked ip dictionary to match expected output."""

	blocked_ip = rename_keys(blocked_ip, {"_id": "ip_address"})
	blocked_ip.update(
		{
			"cluster": cluster_name,
			"name": f"{cluster_name}-{blocked_ip['ip_address']}",
		}
	)

	return blocked_ip

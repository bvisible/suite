import json
from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.parse import urljoin

import frappe
import requests
from frappe import _

from mail.mail.doctype.mail_server_request.mail_server_request import create_mail_server_request
from mail.utils import get_dkim_selector
from mail.utils.cache import get_clusters


@dataclass
class Principal:
	"""Dataclass to represent a principal."""

	name: str
	type: Literal["domain", "apiKey", "individual"]
	id: int = 0
	quota: int = 0
	description: str = ""
	secrets: str | list[str] = field(default_factory=list)
	emails: list[str] = field(default_factory=list)
	urls: list[str] = field(default_factory=list)
	memberOf: list[str] = field(default_factory=list)
	roles: list[str] = field(default_factory=list)
	lists: list[str] = field(default_factory=list)
	members: list[str] = field(default_factory=list)
	enabledPermissions: list[str] = field(default_factory=list)
	disabledPermissions: list[str] = field(default_factory=list)
	externalMembers: list[str] = field(default_factory=list)


class MailServerAPI:
	"""Class to interact with the Mail Server API."""

	def __init__(
		self,
		base_url: str,
		api_key: str | None = None,
		username: str | None = None,
		password: str | None = None,
	) -> None:
		self.base_url = base_url
		self.__api_key = api_key
		self.__username = username
		self.__password = password
		self.__session = requests.Session()

		self.__auth = None
		self.__headers = {}
		if self.__api_key:
			self.__headers.update({"Authorization": f"Bearer {self.__api_key}"})
		else:
			if not self.__username or not self.__password:
				frappe.throw(_("API Key or Username and Password is required."))

			self.__auth = (self.__username, self.__password)

	def request(
		self,
		method: str,
		endpoint: str,
		params: dict | None = None,
		data: dict | None = None,
		json: dict | None = None,
		files: dict | None = None,
		headers: dict[str, str] | None = None,
		timeout: int | tuple[int, int] = (60, 120),
	) -> Any | None:
		"""Makes an HTTP request to the Mail Server API."""

		url = urljoin(self.base_url, endpoint)

		headers = headers or {}
		headers.update(self.__headers)

		if files:
			headers.pop("content-type", None)

		response = self.__session.request(
			method=method,
			url=url,
			params=params,
			data=data,
			headers=headers,
			files=files,
			auth=self.__auth,
			timeout=timeout,
			json=json,
		)

		return response


def get_mail_server_api(cluster_name: str) -> MailServerAPI:
	"""Returns an authenticated MailServerAPI instance."""

	cluster = frappe.get_cached_doc("Mail Cluster", cluster_name)
	api_key = cluster.get_password("api_key") if cluster.api_key else None

	return MailServerAPI(
		cluster.base_url,
		api_key=api_key,
		username=cluster.admin_username,
		password=cluster.get_password("admin_password"),
	)


def reload_configuration(clusters: list[str] | None = None) -> None:
	"""Reloads the configuration on all the clusters."""

	clusters = clusters or get_clusters()
	for cluster in clusters:
		create_mail_server_request(
			cluster=cluster,
			method="GET",
			endpoint="/api/reload",
			do_not_enqueue=True,
		)


def block_ip_on_clusters(ip_address: str, clusters: list[str] | None = None) -> None:
	"""Blocks an IP address on all the clusters."""

	clusters = clusters or get_clusters()
	request_data = json.dumps(
		[
			{
				"type": "insert",
				"prefix": None,
				"values": [[f"server.blocked-ip.{ip_address}", ""]],
				"assert_empty": True,
			}
		]
	)
	for cluster in clusters:
		create_mail_server_request(
			cluster=cluster,
			method="POST",
			endpoint="/api/settings",
			request_data=request_data,
		)


def unblock_ip_on_clusters(ip_address: str, clusters: list[str] | None = None) -> None:
	"""Unblocks an IP address on all the clusters."""

	clusters = clusters or get_clusters()
	request_data = json.dumps([{"type": "delete", "keys": [f"server.blocked-ip.{ip_address}"]}])
	for cluster in clusters:
		create_mail_server_request(
			cluster=cluster,
			method="POST",
			endpoint="/api/settings",
			request_data=request_data,
		)


def create_dkim_key_on_clusters(
	domain_name: str, rsa_private_key: str, clusters: list[str] | None = None
) -> None:
	"""Creates a DKIM Key on all the clusters."""

	clusters = clusters or get_clusters()
	request_data = json.dumps(
		[
			{
				"type": "insert",
				"prefix": f"signature.rsa-{domain_name}",
				"values": [
					["report", "true"],
					["selector", get_dkim_selector("rsa")],
					["canonicalization", "relaxed/relaxed"],
					["private-key", rsa_private_key],
					["algorithm", "rsa-sha256"],
					["domain", domain_name],
				],
				"assert_empty": True,
			}
		]
	)
	for cluster in clusters:
		create_mail_server_request(
			cluster=cluster,
			method="POST",
			endpoint="/api/settings",
			request_data=request_data,
		)


def delete_dkim_key_from_clusters(domain_name: str, clusters: list[str] | None = None) -> None:
	"""Deletes a DKIM Key from all the clusters."""

	clusters = clusters or get_clusters()
	request_data = json.dumps(
		[
			{
				"type": "clear",
				"prefix": f"signature.rsa-{domain_name}",
			}
		]
	)
	for cluster in clusters:
		create_mail_server_request(
			cluster=cluster,
			method="POST",
			endpoint="/api/settings",
			request_data=request_data,
		)


def create_domain_on_clusters(domain_name: str, clusters: list[str] | None = None) -> None:
	"""Creates a domain on all the clusters."""

	clusters = clusters or get_clusters()
	principal = Principal(name=domain_name, type="domain").__dict__
	for cluster in clusters:
		create_mail_server_request(
			cluster=cluster, method="POST", endpoint="/api/principal", request_data=principal
		)


def delete_domain_from_clusters(domain_name: str, clusters: list[str] | None = None) -> None:
	"""Deletes a domain from all the clusters."""

	clusters = clusters or get_clusters()
	for cluster in clusters:
		create_mail_server_request(cluster=cluster, method="DELETE", endpoint=f"/api/principal/{domain_name}")


def create_account_on_clusters(
	email: str, display_name: str, secret: str, clusters: list[str] | None = None
) -> None:
	"""Creates an account on all the clusters."""

	clusters = clusters or get_clusters()
	principal = Principal(
		name=email,
		type="individual",
		description=display_name,
		secrets=[secret],
		emails=[email],
		roles=["user"],
	).__dict__
	for cluster in clusters:
		create_mail_server_request(
			cluster=cluster, method="POST", endpoint="/api/principal", request_data=principal
		)


def patch_account_on_clusters(
	email: str, display_name: str, new_secret: str, old_secret: str, clusters: list[str] | None = None
) -> None:
	"""Patches an account on all the clusters."""

	clusters = clusters or get_clusters()
	request_data = [
		{
			"action": "set",
			"field": "description",
			"value": display_name,
		}
	]

	if old_secret != new_secret:
		request_data.extend(
			[
				{
					"action": "addItem",
					"field": "secrets",
					"value": new_secret,
				},
				{
					"action": "removeItem",
					"field": "secrets",
					"value": old_secret,
				},
			]
		)

	request_data = json.dumps(request_data)
	for cluster in clusters:
		create_mail_server_request(
			cluster=cluster, method="PATCH", endpoint=f"/api/principal/{email}", request_data=request_data
		)


def delete_account_from_clusters(email: str, clusters: list[str] | None = None) -> None:
	"""Deletes an account from all the clusters."""

	clusters = clusters or get_clusters()
	for cluster in clusters:
		create_mail_server_request(cluster=cluster, method="DELETE", endpoint=f"/api/principal/{email}")


def create_group_on_clusters(email: str, display_name: str, clusters: list[str] | None = None) -> None:
	"""Creates a group on all the clusters."""

	clusters = clusters or get_clusters()
	principal = Principal(
		name=email,
		type="group",
		description=display_name,
		emails=[email],
		enabledPermissions=["email-send", "email-receive"],
	).__dict__
	for cluster in clusters:
		create_mail_server_request(
			cluster=cluster, method="POST", endpoint="/api/principal", request_data=principal
		)


def patch_group_on_clusters(email: str, display_name: str, clusters: list[str] | None = None) -> None:
	"""Patches a group on all the clusters."""

	clusters = clusters or get_clusters()
	request_data = json.dumps(
		[
			{
				"action": "set",
				"field": "description",
				"value": display_name,
			}
		]
	)
	for cluster in clusters:
		create_mail_server_request(
			cluster=cluster, method="PATCH", endpoint=f"/api/principal/{email}", request_data=request_data
		)


def delete_group_from_clusters(email: str, clusters: list[str] | None = None) -> None:
	"""Deletes a group from all the clusters."""

	delete_account_from_clusters(email, clusters)


def create_alias_on_clusters(email: str, alias: str, clusters: list[str] | None = None) -> None:
	"""Creates an alias on all the clusters."""

	clusters = clusters or get_clusters()
	request_data = json.dumps([{"action": "addItem", "field": "emails", "value": alias}])
	for cluster in clusters:
		create_mail_server_request(
			cluster=cluster, method="PATCH", endpoint=f"/api/principal/{email}", request_data=request_data
		)


def patch_alias_on_clusters(
	new_email: str, old_email: str, alias: str, clusters: list[str] | None = None
) -> None:
	"""Patches an alias on all the clusters."""

	delete_alias_from_clusters(old_email, alias, clusters)
	create_alias_on_clusters(new_email, alias, clusters)


def delete_alias_from_clusters(email: str, alias: str, clusters: list[str] | None = None) -> None:
	"""Deletes an alias from all the clusters."""

	clusters = clusters or get_clusters()
	request_data = json.dumps([{"action": "removeItem", "field": "emails", "value": alias}])
	for cluster in clusters:
		create_mail_server_request(
			cluster=cluster, method="PATCH", endpoint=f"/api/principal/{email}", request_data=request_data
		)


def create_member_on_clusters(
	email: str, member: str, is_group: bool, clusters: list[str] | None = None
) -> None:
	"""Creates a group member on all the clusters."""

	clusters = clusters or get_clusters()
	endpoint = None
	request_data = None
	if is_group:
		endpoint = f"/api/principal/{member}"
		request_data = json.dumps([{"action": "addItem", "field": "memberOf", "value": email}])
	else:
		endpoint = f"/api/principal/{email}"
		request_data = json.dumps([{"action": "addItem", "field": "members", "value": member}])

	for cluster in clusters:
		create_mail_server_request(
			cluster=cluster, method="PATCH", endpoint=endpoint, request_data=request_data
		)


def patch_member_on_clusters(
	new_email: str, old_email: str, member: str, is_group: bool, clusters: list[str] | None = None
) -> None:
	"""Patches a group member on all the clusters."""

	delete_member_from_clusters(old_email, member, is_group, clusters)
	create_member_on_clusters(new_email, member, is_group, clusters)


def delete_member_from_clusters(
	email: str, member: str, is_group: bool, clusters: list[str] | None = None
) -> None:
	"""Deletes a group member from all the clusters."""

	clusters = clusters or get_clusters()
	endpoint = None
	request_data = None
	if is_group:
		endpoint = f"/api/principal/{member}"
		request_data = json.dumps([{"action": "removeItem", "field": "memberOf", "value": email}])
	else:
		endpoint = f"/api/principal/{email}"
		request_data = json.dumps([{"action": "removeItem", "field": "members", "value": member}])

	for cluster in clusters:
		create_mail_server_request(
			cluster=cluster, method="PATCH", endpoint=endpoint, request_data=request_data
		)

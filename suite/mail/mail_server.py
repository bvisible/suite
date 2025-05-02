import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urljoin

import frappe
import requests
from frappe import _

from mail.mail.doctype.mail_backend_request.mail_backend_request import create_mail_backend_request
from mail.utils import get_dkim_selector

if TYPE_CHECKING:
	from mail.mail.doctype.mail_backend_request.mail_backend_request import MailBackendRequest


@dataclass
class Principal:
	"""Dataclass to represent a principal."""

	name: str
	type: Literal["domain", "apiKey", "individual", "group"]
	id: int = 0
	quota: int = 0
	description: str = ""
	secrets: list[str] = field(default_factory=list)
	emails: list[str] = field(default_factory=list)
	urls: list[str] = field(default_factory=list)
	memberOf: list[str] = field(default_factory=list)
	roles: list[str] = field(default_factory=list)
	lists: list[str] = field(default_factory=list)
	members: list[str] = field(default_factory=list)
	enabledPermissions: list[str] = field(default_factory=list)
	disabledPermissions: list[str] = field(default_factory=list)
	externalMembers: list[str] = field(default_factory=list)


class MailBackendAPI:
	"""Class to interact with the Mail Backend API."""

	def __init__(
		self,
		base_url: str,
		api_key: str | None = None,
		username: str | None = None,
		password: str | None = None,
	) -> None:
		self.base_url = base_url

		self.__auth = None
		self.__headers = {}
		self.__session = requests.Session()

		if api_key:
			self.__headers.update({"Authorization": f"Bearer {api_key}"})
		elif username and password:
			self.__auth = (username, password)
		else:
			frappe.throw(_("API Key or Username and Password is required."))

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
	) -> Any:
		"""Makes an HTTP request to the Mail Backend API."""

		url = urljoin(self.base_url, endpoint)
		headers = {**self.__headers, **(headers or {})}

		if files:
			headers.pop("content-type", None)

		return self.__session.request(
			method=method,
			url=url,
			params=params,
			data=data,
			json=json,
			files=files,
			headers=headers,
			auth=self.__auth,
			timeout=timeout,
		)


class MailServerManagerBase:
	"""Base class for Mail Server Managers."""

	def __init__(self, backend_type: Literal["Mail Cluster", "Mail Server"], backend_name: str) -> None:
		self.backend_type = backend_type
		self.backend_name = backend_name

	def create_request(
		self,
		method: str,
		endpoint: str,
		request_headers: dict | None = None,
		request_params: dict | None = None,
		request_data: str | None = None,
		request_json: dict | None = None,
		execute_on_start: Callable | str | None = None,
		execute_on_end: Callable | str | None = None,
		do_not_enqueue: bool = False,
	) -> None:
		"""Creates a new Mail Backend Request."""

		create_mail_backend_request(
			backend_type=self.backend_type,
			backend_name=self.backend_name,
			method=method,
			endpoint=endpoint,
			request_headers=request_headers,
			request_params=request_params,
			request_data=request_data,
			request_json=request_json,
			execute_on_start=execute_on_start,
			execute_on_end=execute_on_end,
			do_not_enqueue=do_not_enqueue,
		)


class MailServerDKIMManager(MailServerManagerBase):
	"""Class to manage DKIM keys on the Mail Server."""

	def create(self, domain_name: str, rsa_private_key: str) -> None:
		"""Creates a DKIM key on the backend."""

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
		self.create_request(
			method="POST",
			endpoint="/api/settings",
			request_data=request_data,
			execute_on_end="mail.mail_server.reload_request_cluster_servers",
		)

	def delete(self, domain_name: str) -> None:
		"""Deletes a DKIM key from the backend."""

		request_data = json.dumps(
			[
				{
					"type": "clear",
					"prefix": f"signature.rsa-{domain_name}",
				}
			]
		)
		self.create_request(
			method="POST",
			endpoint="/api/settings",
			request_data=request_data,
		)


class MailServerDomainManager(MailServerManagerBase):
	"""Class to manage domains on the Mail Server."""

	def create(self, domain_name: str) -> None:
		"""Creates a domain on the backend."""

		principal = Principal(name=domain_name, type="domain").__dict__
		self.create_request(method="POST", endpoint="/api/principal", request_data=principal)

	def delete(self, domain_name: str) -> None:
		"""Deletes a domain from the backend."""

		self.create_request(method="DELETE", endpoint=f"/api/principal/{domain_name}")


class MailServerAccountManager(MailServerManagerBase):
	"""Class to manage accounts on the Mail Server."""

	def create(self, email: str, display_name: str, secret: str) -> None:
		"""Creates an account on the backend."""

		principal = Principal(
			name=email,
			type="individual",
			description=display_name,
			secrets=[secret],
			emails=[email],
			roles=["user"],
		).__dict__
		self.create_request(method="POST", endpoint="/api/principal", request_data=principal)

	def update(self, email: str, display_name: str, new_secret: str, old_secret: str) -> None:
		"""Updates an account on the backend."""

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
		self.create_request(method="PATCH", endpoint=f"/api/principal/{email}", request_data=request_data)

	def delete(self, email: str) -> None:
		"""Deletes an account from the backend."""

		self.create_request(method="DELETE", endpoint=f"/api/principal/{email}")


class MailServerGroupManager(MailServerManagerBase):
	"""Class to manage groups on the Mail Server."""

	def create(self, email: str, display_name: str) -> None:
		"""Creates a group on the backend."""

		principal = Principal(
			name=email,
			type="group",
			description=display_name,
			emails=[email],
			enabledPermissions=["email-send", "email-receive"],
		).__dict__
		self.create_request(method="POST", endpoint="/api/principal", request_data=principal)

	def update(self, email: str, display_name: str) -> None:
		"""Updates a group on the backend."""

		request_data = json.dumps(
			[
				{
					"action": "set",
					"field": "description",
					"value": display_name,
				}
			]
		)
		self.create_request(method="PATCH", endpoint=f"/api/principal/{email}", request_data=request_data)

	def delete(self, email: str) -> None:
		"""Deletes a group from the backend."""

		self.create_request(method="DELETE", endpoint=f"/api/principal/{email}")


class MailServerAliasManager(MailServerManagerBase):
	"""Class to manage aliases on the Mail Server."""

	def create(self, email: str, alias: str) -> None:
		"""Creates an alias on the backend."""

		request_data = json.dumps([{"action": "addItem", "field": "emails", "value": alias}])
		self.create_request(method="PATCH", endpoint=f"/api/principal/{email}", request_data=request_data)

	def update(self, new_email: str, old_email: str, alias: str) -> None:
		"""Updates an alias on the backend."""

		self.delete(old_email, alias)
		self.create(new_email, alias)

	def delete(self, email: str, alias: str) -> None:
		"""Deletes an alias from the backend."""

		request_data = json.dumps([{"action": "removeItem", "field": "emails", "value": alias}])
		self.create_request(method="PATCH", endpoint=f"/api/principal/{email}", request_data=request_data)


class MailServerMemberManager(MailServerManagerBase):
	"""Class to manage group members on the Mail Server."""

	def create(self, email: str, member: str, is_group: bool) -> None:
		"""Creates a group member on the backend."""

		endpoint = None
		request_data = None
		if is_group:
			endpoint = f"/api/principal/{member}"
			request_data = json.dumps([{"action": "addItem", "field": "memberOf", "value": email}])
		else:
			endpoint = f"/api/principal/{email}"
			request_data = json.dumps([{"action": "addItem", "field": "members", "value": member}])

		self.create_request(method="PATCH", endpoint=endpoint, request_data=request_data)

	def update(self, new_email: str, old_email: str, member: str, is_group: bool) -> None:
		"""Updates a group member on the backend."""

		self.delete(old_email, member, is_group)
		self.create(new_email, member, is_group)

	def delete(self, email: str, member: str, is_group: bool) -> None:
		"""Deletes a group member from the backend."""

		endpoint = None
		request_data = None
		if is_group:
			endpoint = f"/api/principal/{member}"
			request_data = json.dumps([{"action": "removeItem", "field": "memberOf", "value": email}])
		else:
			endpoint = f"/api/principal/{email}"
			request_data = json.dumps([{"action": "removeItem", "field": "members", "value": member}])

		self.create_request(method="PATCH", endpoint=endpoint, request_data=request_data)


def get_mail_backend_api(
	backend_type: Literal["Mail Cluster", "Mail Server"], backend_name: str
) -> MailBackendAPI:
	"""Returns an authenticated MailBackendAPI instance."""

	cluster_name = backend_name
	if backend_type == "Mail Server":
		cluster_name = frappe.db.get_value("Mail Server", backend_name, "cluster")

		if not cluster_name:
			frappe.throw(_("Mail Server {0} does not have a cluster.").format(backend_name))

	cluster = frappe.get_cached_doc("Mail Cluster", cluster_name)

	base_url = cluster.base_url
	if backend_type == "Mail Server":
		base_url = frappe.db.get_value("Mail Server", backend_name, "base_url")

		if not base_url:
			frappe.throw(_("Mail Server {0} does not have a base URL.").format(backend_name))

	api_key = cluster.get_password("api_key") if cluster.api_key else None

	return MailBackendAPI(
		base_url,
		api_key=api_key,
		username=cluster.fallback_admin_user,
		password=cluster.get_password("fallback_admin_password"),
	)


# Execute on Start/End


def reload_request_cluster_servers(request: "MailBackendRequest") -> None:
	from mail.mail.doctype.mail_cluster.mail_cluster import reload_servers_config

	try:
		reload_servers_config([request.cluster])
	except Exception:
		frappe.log_error(
			title=_("Error reloading {0} servers configuration").format(request.cluster),
			message=frappe.get_traceback(with_context=True),
		)

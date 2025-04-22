from functools import cached_property
from typing import Any
from urllib.parse import urljoin

import frappe
import requests
from frappe import _
from frappe.utils import create_batch
from frappe.utils.caching import redis_cache

from mail.utils import batch_dict
from mail.utils.cache import get_cluster_for_tenant
from mail.utils.validation import validate_permission_for_account


class JMAPClient:
	"""JMAP Client for interacting with JMAP servers."""

	def __init__(self, host: str, username: str, password: str) -> None:
		"""Initialize the JMAP client."""

		self.__host = host
		self.__config = None
		self.__session = requests.Session()
		self.__session.auth = (username, password)

		self._discover_config()

	def _discover_config(self) -> None:
		"""Discover JMAP configuration from the server."""

		well_known_url = urljoin(self.__host, "/.well-known/jmap")

		try:
			response = self.__session.get(well_known_url, headers={"Accept": "application/json"})
			response.raise_for_status()
			self.__config = response.json()
		except Exception as e:
			raise ConnectionError(f"Failed to discover JMAP configuration: {str(e)}")

	@property
	def capabilities(self) -> dict:
		"""Returns the capabilities of the JMAP server."""

		return self.__config["capabilities"]

	@property
	def max_objects_in_get(self) -> int:
		"""Returns the maximum number of objects in a single get request."""

		return self.capabilities["urn:ietf:params:jmap:core"]["maxObjectsInGet"]

	@property
	def max_objects_in_set(self) -> int:
		"""Returns the maximum number of objects in a single set request."""

		return self.capabilities["urn:ietf:params:jmap:core"]["maxObjectsInSet"]

	@property
	def accounts(self) -> dict:
		"""Returns the accounts for the logged-in user."""

		return self.__config["accounts"]

	@property
	def account_ids(self) -> list[str]:
		"""Returns the list of account IDs for the logged-in user."""

		return list(self.__config["accounts"].keys())

	@property
	def account_id(self) -> str:
		"""Returns the primary account ID for the logged-in user."""

		return self.primary_accounts["urn:ietf:params:jmap:mail"]

	@property
	def has_multiple_accounts(self) -> bool:
		"""Returns True if the user has multiple accounts, False otherwise."""

		return len(self.account_ids) > 1

	@property
	def primary_accounts(self) -> dict:
		"""Returns the primary accounts for the logged-in user."""

		return self.__config["primaryAccounts"]

	@property
	def username(self) -> str:
		"""Returns the username of the logged-in user."""

		return self.__config["username"]

	@property
	def api_url(self) -> str:
		"""Returns the API URL for the JMAP server."""

		return self.__config["apiUrl"]

	@property
	def download_url(self) -> str:
		"""Returns the download URL for the JMAP server."""

		return self.__config["downloadUrl"]

	@property
	def upload_url(self) -> str:
		"""Returns the upload URL for the JMAP server."""

		return self.__config["uploadUrl"]

	@property
	def event_source_url(self) -> str:
		"""Returns the event source URL for the JMAP server."""

		return self.__config["eventSourceUrl"]

	@property
	def state(self) -> dict:
		"""Returns the state of the JMAP server."""

		return self.__config["state"]

	@cached_property
	def mailboxes(self) -> dict[list[dict]]:
		"""Returns the mailboxes for the logged-in user."""

		mailboxes = {}
		for account_id in [self.account_id]:
			response = self._make_request(
				["urn:ietf:params:jmap:mail"], [["Mailbox/get", {"accountId": account_id}, "0"]]
			)
			mailboxes[account_id] = response["methodResponses"][0][1]["list"]

		return mailboxes

	def _validate_capabilities(self, capabilities: list[str]) -> None:
		"""Validate the requested capabilities against the server's capabilities."""

		for capability in capabilities:
			if capability not in self.capabilities:
				raise ValueError(f"Unsupported capability: {capability}")

	def _validate_method_calls(self, method_calls: list[list]) -> None:
		"""Validate the method calls against the server's capabilities."""

		call_ids = []
		for method_call in method_calls:
			if not isinstance(method_call, list) or len(method_call) != 3:
				raise ValueError("Method call must be a list of [method_name, arguments, call_id]")

			if (
				not isinstance(method_call[0], str)
				or not isinstance(method_call[1], dict)
				or not isinstance(method_call[2], str)
			):
				raise ValueError("Method call must be a list of [string, dict, string]")

			if method_call[2] in call_ids:
				raise ValueError(f"Duplicate call ID: {method_call[2]}")

			call_ids.append(method_call[2])

	def _make_request(self, using: list[str], method_calls: list[list]) -> Any:
		"""Make a request to the JMAP server."""

		self._validate_capabilities(using)
		self._validate_method_calls(method_calls)

		headers = {"Content-Type": "application/json", "Accept": "application/json"}
		payload = {"using": using, "methodCalls": method_calls}
		response = self.__session.post(self.api_url, headers=headers, json=payload)
		response.raise_for_status()

		return response.json()

	def query_emails(self, filter: dict, position: int = 0, limit: int = 50) -> dict:
		"""Query emails based on the provided filter."""

		response = self._make_request(
			using=["urn:ietf:params:jmap:mail"],
			method_calls=[
				[
					"Email/query",
					{
						"accountId": self.account_id,
						"filter": filter if filter else None,
						"position": position,
						"limit": limit,
						"sort": [{"property": "receivedAt", "isAscending": False}],
						"calculateTotal": True,
					},
					"0",
				]
			],
		)

		return response["methodResponses"][0][1]

	def get_threads(self, thread_ids: list[str]) -> dict[str, list]:
		"""Returns the threads for the provided thread IDs."""

		result = {}
		for ids_batch in create_batch(thread_ids, self.max_objects_in_get):
			response = self._make_request(
				using=["urn:ietf:params:jmap:mail"],
				method_calls=[
					[
						"Thread/get",
						{
							"accountId": self.account_id,
							"ids": ids_batch,
							"properties": ["emailIds"],
						},
						"0",
					]
				],
			)

			if threads := response["methodResponses"][0][1]["list"]:
				result.update({thread["id"]: thread["emailIds"] for thread in threads})

		return result

	def get_emails(self, email_ids: list[str]) -> list[dict]:
		"""Returns the emails for the provided email IDs."""

		properties = [
			"id",
			"blobId",
			"threadId",
			"mailboxIds",
			"keywords",
			"size",
			"receivedAt",
			"sentAt",
			"hasAttachment",
			"subject",
			"from",
			"to",
			"cc",
			"bcc",
			"replyTo",
			"sender",
			"messageId",
			"inReplyTo",
			"references",
			"htmlBody",
			"textBody",
			"bodyValues",
			"attachments",
		]

		results = []
		for ids_batch in create_batch(email_ids, self.max_objects_in_get):
			response = self._make_request(
				using=["urn:ietf:params:jmap:mail"],
				method_calls=[
					[
						"Email/get",
						{
							"accountId": self.account_id,
							"ids": ids_batch,
							"properties": properties,
							"fetchAllBodyValues": True,
						},
						"0",
					]
				],
			)
			results.extend(response["methodResponses"][0][1]["list"])

		return results

	def download_blob(self, blob_id: str, name: str | None = None) -> bytes:
		"""Returns the blob data for the provided blob ID."""

		name = name or "blob"
		download_url = self.download_url.format(
			accountId=self.account_id, blobId=blob_id, name=name, type="application/octet-stream"
		)
		response = self.__session.get(download_url)
		response.raise_for_status()

		return response.content

	def move_emails(self, email_ids: list[str], target_mailbox_id: str) -> None:
		"""Move emails to the target mailbox."""

		for ids_batch in create_batch(email_ids, self.max_objects_in_set):
			self._make_request(
				using=["urn:ietf:params:jmap:mail"],
				method_calls=[
					[
						"Email/set",
						{
							"accountId": self.account_id,
							"update": {
								email_id: {"mailboxIds": {target_mailbox_id: True}} for email_id in ids_batch
							},
						},
						"0",
					]
				],
			)

	def update_emails_keywords(self, email_id_keywords_map: dict[str, dict]) -> None:
		"""Update email keywords."""

		for map_batch in batch_dict(email_id_keywords_map, self.max_objects_in_set):
			self._make_request(
				using=["urn:ietf:params:jmap:mail"],
				method_calls=[
					[
						"Email/set",
						{
							"accountId": self.account_id,
							"update": {
								email_id: {"keywords": keywords} for email_id, keywords in map_batch.items()
							},
						},
						"0",
					]
				],
			)


@redis_cache(ttl=300)
def get_jmap_client(account: str) -> "JMAPClient":
	"""Returns a JMAP client for the given account."""

	account = frappe.get_doc("Mail Account", account)
	cluster = get_cluster_for_tenant(account.tenant)

	if not cluster:
		frappe.throw(_("No cluster found for the account {0}.").format(frappe.bold(account.name)))

	host = frappe.db.get_value("Mail Cluster", cluster, "base_url")
	client = JMAPClient(host, account.email, account.get_password())

	return client


def get_mailboxes(account: str) -> list[dict]:
	"""Returns the mailboxes for the given account."""

	def generator() -> list[dict]:
		client = get_jmap_client(account)

		mailboxes = []
		for mailbox in client.mailboxes[client.account_id]:
			mailboxes.append(
				{
					"id": mailbox["id"],
					"name": mailbox["name"],
					"role": mailbox["role"],
				}
			)

		return mailboxes

	return frappe.cache.hget("jmap:mailboxes", account, generator)


def get_mailbox_id(account: str, role: str | None = None, name: str | None = None) -> str | None:
	"""Returns the mailbox ID for the given role or name."""

	for mailbox in get_mailboxes(account):
		if (role and mailbox.get("role").lower() == role.lower()) or (
			name and mailbox.get("name").lower() == name.lower()
		):
			return mailbox["id"]


def get_mailbox_name(account: str, id: str | None = None, role: str | None = None) -> str | None:
	"""Returns the mailbox name for the given ID or role."""

	for mailbox in get_mailboxes(account):
		if (id and mailbox.get("id") == id) or (role and mailbox.get("role").lower() == role.lower()):
			return mailbox["name"]


@frappe.whitelist()
def get_mailboxes_for_account(account: str) -> list[dict]:
	"""Returns the mailboxes for the given account."""

	validate_permission_for_account(account)
	return get_mailboxes(account)


@frappe.whitelist()
def get_mailbox_id_for_account(account: str, role: str | None = None, name: str | None = None) -> str | None:
	"""Returns the mailbox ID for the given role or name."""

	validate_permission_for_account(account)
	return get_mailbox_id(account, role, name)


@frappe.whitelist()
def get_mailbox_name_for_account(account: str, id: str | None = None, role: str | None = None) -> str | None:
	"""Returns the mailbox name for the given ID or role."""

	validate_permission_for_account(account)
	return get_mailbox_name(account, id, role)

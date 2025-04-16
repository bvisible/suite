import functools
import time
from typing import Any
from urllib.parse import urljoin

import frappe
import requests
from frappe import _
from frappe.utils import create_batch
from frappe.utils.caching import redis_cache

from mail.utils.cache import get_cluster_for_tenant


class JMAPClient:
	def __init__(self, host: str, username: str, password: str) -> None:
		self.__host = host
		self.__config = None
		self.__session = requests.Session()
		self.__session.auth = (username, password)

		self._discover_config()

	def _discover_config(self) -> None:
		well_known_url = urljoin(self.__host, "/.well-known/jmap")

		try:
			response = self.__session.get(well_known_url, headers={"Accept": "application/json"})
			response.raise_for_status()
			self.__config = response.json()
		except Exception as e:
			raise ConnectionError(f"Failed to discover JMAP configuration: {str(e)}")

	@property
	def capabilities(self) -> dict:
		return self.__config["capabilities"]

	@property
	def accounts(self) -> dict:
		return self.__config["accounts"]

	@property
	def account_ids(self) -> list[str]:
		return list(self.__config["accounts"].keys())

	@property
	def has_multiple_accounts(self) -> bool:
		return len(self.account_ids) > 1

	@property
	def primary_accounts(self) -> dict:
		return self.__config["primaryAccounts"]

	@property
	def username(self) -> str:
		return self.__config["username"]

	@property
	def api_url(self) -> str:
		return self.__config["apiUrl"]

	@property
	def download_url(self) -> str:
		return self.__config["downloadUrl"]

	@property
	def upload_url(self) -> str:
		return self.__config["uploadUrl"]

	@property
	def event_source_url(self) -> str:
		return self.__config["eventSourceUrl"]

	@property
	def state(self) -> dict:
		return self.__config["state"]

	@functools.cached_property
	def mailboxes(self) -> dict[list[dict]]:
		mailboxes = {}

		for account_id in self.account_ids:
			response = self._make_request(
				["urn:ietf:params:jmap:mail"], [["Mailbox/get", {"accountId": account_id}, "0"]]
			)
			mailboxes[account_id] = response["methodResponses"][0][1]["list"]

		return mailboxes

	def _validate_capabilities(self, capabilities: list[str]) -> None:
		for capability in capabilities:
			if capability not in self.capabilities:
				raise ValueError(f"Unsupported capability: {capability}")

	def _validate_method_calls(self, method_calls: list[list]) -> None:
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
		self._validate_capabilities(using)
		self._validate_method_calls(method_calls)

		headers = {"Content-Type": "application/json", "Accept": "application/json"}
		payload = {"using": using, "methodCalls": method_calls}
		response = self.__session.post(self.api_url, headers=headers, json=payload)
		response.raise_for_status()

		return response.json()

	def get_mailboxes(self, account_id: str) -> list[dict]:
		mailboxes = []

		for mailbox in self.mailboxes[account_id]:
			mailboxes.append(
				{
					"id": mailbox["id"],
					"name": mailbox["name"],
					"role": mailbox["role"],
					"totalEmails": mailbox["totalEmails"],
					"unreadEmails": mailbox["unreadEmails"],
					"totalThreads": mailbox["totalThreads"],
					"unreadThreads": mailbox["unreadThreads"],
				}
			)

		return mailboxes

	def get_mailbox_id(self, account_id: str, role: str | None = None, name: str | None = None) -> str | None:
		for mailbox in self.mailboxes[account_id]:
			if role and mailbox.get("role").lower() == role.lower():
				return mailbox["id"]
			if name and mailbox.get("name").lower() == name.lower():
				return mailbox["id"]

	def get_mailbox_name(self, account_id: str, mailbox_id: str) -> str | None:
		for mailbox in self.mailboxes[account_id]:
			if mailbox["id"] == mailbox_id:
				return mailbox["name"]

	def query_emails(self, account_id: str, filter: dict, position: int = 0, limit: int = 50) -> dict:
		response = self._make_request(
			using=["urn:ietf:params:jmap:mail"],
			method_calls=[
				[
					"Email/query",
					{
						"accountId": account_id,
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

	def get_emails(self, account_id: str, ids: list[str]) -> list[dict]:
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
			"preview",
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
		for ids_batch in create_batch(ids, 100):
			response = self._make_request(
				using=["urn:ietf:params:jmap:mail"],
				method_calls=[
					[
						"Email/get",
						{
							"accountId": account_id,
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

	def download_blob(self, account_id: str, blob_id: str, name: str | None = None) -> bytes:
		name = name or "blob"
		download_url = self.download_url.format(
			accountId=account_id, blobId=blob_id, name=name, type="application/octet-stream"
		)
		response = self.__session.get(download_url)
		response.raise_for_status()

		return response.content

	def get_query_state(self, account_id: str, mailbox_id: str = None) -> str:
		filters = {}
		if mailbox_id:
			filters["inMailbox"] = mailbox_id

		response = self._make_request(
			using=["urn:ietf:params:jmap:mail"],
			method_calls=[
				[
					"Email/query",
					{
						"accountId": account_id,
						"filter": filters or None,
						"sort": [{"property": "receivedAt", "isAscending": False}],
						"limit": 0,
					},
					"1",
				]
			],
		)
		return response["methodResponses"][0][1]["queryState"]

	def watch_for_new_emails(self, account_id: str, mailbox_id: str = None, interval: int = 5) -> None:
		last_state = self.get_query_state(account_id, mailbox_id)

		while True:
			print(f"⏳ Waiting for {interval} seconds before checking for new emails...")
			time.sleep(interval)
			print("⏳ Checking for new emails...")

			response = self._make_request(
				using=["urn:ietf:params:jmap:mail"],
				method_calls=[
					[
						"Email/queryChanges",
						{
							"accountId": account_id,
							"filter": {"inMailbox": mailbox_id} if mailbox_id else None,
							"sinceQueryState": last_state,
						},
						"1",
					]
				],
			)

			changes = response["methodResponses"][0][1]
			added_ids = changes.get("added", [])
			last_state = changes["newQueryState"]

			if added_ids:
				email_ids = [entry["id"] for entry in added_ids]
				emails = self.get_emails(account_id, email_ids)
				for email in emails:
					print(f"📥 New: {email['subject']} — {email['receivedAt']}")


@redis_cache(ttl=300)
def get_jmap_client(account: str) -> "JMAPClient":
	account = frappe.get_doc("Mail Account", account)
	cluster = get_cluster_for_tenant(account.tenant)

	if not cluster:
		frappe.throw(_("No cluster found for the account {0}.").format(frappe.bold(account.name)))

	host = frappe.db.get_value("Mail Cluster", cluster, "base_url")
	client = JMAPClient(host, account.email, account.get_password())

	return client

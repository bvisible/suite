# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document

from mail.mail_server import MailServerAPI
from mail.utils import rename_keys

cluster_message_count_map = {}


class MessageQueue(Document):
	def db_insert(self, *args, **kwargs) -> None:
		raise NotImplementedError

	def load_from_db(self) -> "MessageQueue":
		message = fetch_message_details(self.name)
		return super(Document, self).__init__(message)

	def db_update(self) -> None:
		raise NotImplementedError

	def delete(self) -> None:
		raise NotImplementedError

	@staticmethod
	def get_list(filters=None, page_length=20, **kwargs) -> list:
		filters = filters or []
		cluster, text = extract_filter_values(filters, [{"cluster": "="}, {"text": "like"}])

		if cluster:
			return fetch_messages(cluster, limit=page_length, text=text)

		return frappe.msgprint(_("Please select a cluster to view messages."), alert=True)

	@staticmethod
	def get_count(filters=None, **kwargs) -> int:
		filters = filters or []
		cluster = extract_filter_values(filters, [{"cluster": "="}])

		return cluster_message_count_map.get(cluster[0], 0) if cluster else 0

	@staticmethod
	def get_stats(**kwargs) -> dict:
		return {}


def extract_filter_values(filters: list, conditions: list[dict]) -> tuple:
	"""Extracts specific filter values from a filter list based on given conditions."""

	values = {list(condition.keys())[0]: None for condition in conditions}
	condition_map = {list(condition.keys())[0]: list(condition.values())[0] for condition in conditions}

	for filter in filters:
		key, operator, value = filter[1], filter[2], filter[3]
		if key in condition_map and operator == condition_map[key]:
			values[key] = value.replace("%", "") if operator == "like" else value

	return tuple(values[key] for key in values)


def get_mail_server_api(cluster_name: str) -> MailServerAPI:
	"""Returns an authenticated MailServerAPI instance."""

	cluster = frappe.get_doc("Mail Cluster", cluster_name)
	api_key = cluster.get_password("api_key") if cluster.api_key else None

	return MailServerAPI(
		cluster.base_url,
		api_key=api_key,
		username=cluster.admin_username,
		password=cluster.get_password("admin_password"),
	)


def fetch_messages(cluster_name: str, page: int = 1, limit: int = 10, text: str | None = None) -> list:
	"""Fetches a list of messages from the mail server."""

	server_api = get_mail_server_api(cluster_name)
	response = server_api.request(
		method="GET",
		endpoint="/api/queue/messages",
		params={"page": page, "limit": limit, "values": 1, "text": text},
	)

	if response.status_code == 200:
		data = response.json()["data"]
		cluster_message_count_map[cluster_name] = data["total"]

		return [format_message(item, cluster_name) for item in data["items"]]

	frappe.throw(title=_("Mail Server Request Failed"), msg=response.text)


def fetch_message_details(name: str) -> dict:
	"""Fetches details of a specific message from the mail server."""

	cluster_name, queue_id = name.split("-")
	server_api = get_mail_server_api(cluster_name)
	response = server_api.request(method="GET", endpoint=f"/api/queue/messages/{queue_id}")

	if response.status_code == 200:
		message = response.json()["data"]
		message["recipients"] = extract_recipients(message)
		message = format_message(message, cluster_name)
		message["_message"] = fetch_blob(cluster_name, message["blob_hash"])

		return message

	frappe.throw(title=_("Mail Server Request Failed"), msg=response.text)


def extract_recipients(message: dict) -> list:
	"""Extracts recipient details from a message dictionary."""

	recipients = []
	domains = json.loads(message["domains"]) if isinstance(message["domains"], str) else message["domains"]
	for domain in domains:
		for recipient in domain["recipients"]:
			server_response = {}
			if domain["status"] != recipient["status"]:
				if isinstance(recipient["status"], dict):
					server_response = json.dumps(recipient["status"], indent=4)

			recipients.append(
				{
					"email": recipient["address"],
					"domain_name": domain["name"],
					"status": domain["status"],
					"retry_num": domain["retry_num"],
					"next_retry": domain["next_retry"],
					"next_notify": domain["next_notify"],
					"expires": domain["expires"],
					"server_response": server_response,
				}
			)

	return recipients


def format_message(message: dict, cluster_name: str) -> dict:
	"""Formats a message dictionary to match expected output."""

	message = rename_keys(
		message,
		{
			"id": "queue_id",
			"size": "message_size",
			"created": "created_at",
		},
	)

	message.update(
		{
			"cluster": cluster_name,
			"name": f"{cluster_name}-{message['queue_id']}",
			"domains": json.dumps(message.get("domains", []), indent=4),
		}
	)

	return message


def fetch_blob(cluster_name: str, blob_id: str) -> str:
	"""Fetches a blob (email content) from the mail server."""

	server_api = get_mail_server_api(cluster_name)
	response = server_api.request(method="GET", endpoint=f"/api/store/blobs/{blob_id}")

	if response.status_code == 200:
		return response.text

	frappe.throw(title=_("Mail Server Request Failed"), msg=response.text)

# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import base64

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import random_string

from mail.agent import AgentAPI, Principal
from mail.utils import generate_secret


class MailAgentGroup(Document):
	def autoname(self) -> None:
		self.agent_group = self.agent_group.lower()
		self.name = self.agent_group

	def validate(self) -> None:
		self.validate_enabled()
		self.validate_agent_group()
		self.validate_priority()
		self.validate_admin_password()
		self.validate_cluster_encryption_key()

	def on_update(self) -> None:
		self.clear_cache()

	def on_trash(self) -> None:
		self.clear_cache()

	def validate_enabled(self) -> None:
		"""Validates the enabled status of the agent group."""

		if self.enabled and not self.inbound and not self.outbound:
			self.enabled = 0

		if self.enabled:
			return

		if agent := frappe.db.exists("Mail Agent", {"enabled": 1, "agent_group": self.name}):
			frappe.throw(_("Mail Agent {0} is enabled. Please disable it first.").format(frappe.bold(agent)))

	def validate_agent_group(self) -> None:
		"""Validates the agent group."""

		if self.is_new() and frappe.db.exists("Mail Agent Group", self.agent_group):
			frappe.throw(_("Mail Agent Group {0} already exists.").format(frappe.bold(self.agent_group)))

	def validate_priority(self) -> None:
		"""Validates the priority of the agent group."""

		if frappe.db.exists(
			"Mail Agent Group",
			{"enabled": 1, "inbound": 1, "priority": self.priority, "name": ["!=", self.name]},
		):
			frappe.throw(
				_("Mail Agent Group with priority {0} already exists.").format(frappe.bold(self.priority))
			)

	def validate_admin_password(self) -> None:
		if self.admin_password:
			if len(self.admin_password) < 16:
				frappe.throw(_("Password must be at least 16 characters long."))
		else:
			self.admin_password = random_string(length=20)

	def validate_cluster_encryption_key(self) -> None:
		"""Validates the encryption key of the agent group."""

		if not self.cluster_encryption_key:
			self.cluster_encryption_key = random_string(length=64)

	def clear_cache(self) -> None:
		"""Clears the cache."""

		frappe.cache.delete_value("agent_groups")

	@frappe.whitelist()
	def get_admin_password(self) -> str:
		"""Returns the admin password of the agent group."""

		frappe.only_for("System Manager")
		return self.get_password("admin_password")

	@frappe.whitelist()
	def generate_api_key(self) -> None:
		"""Generates an API key for the agent group."""

		frappe.only_for("System Manager")
		self.api_key = self._generate_api_key()
		self.save()

	def _generate_api_key(self) -> str:
		"""Generates an API key for the agent group."""

		if not self.base_url:
			frappe.throw(_("Base URL is required."))

		name = f"{random_string(10)}-{self.agent_group}".lower()
		secret = generate_secret()
		principal = Principal(
			name=name, type="apiKey", secrets=secret, roles=["admin"], enabledPermissions=["authenticate"]
		)
		agent_api = AgentAPI(
			self.base_url, username=self.admin_username, password=self.get_password("admin_password")
		)
		response = agent_api.request(method="POST", endpoint="/api/principal", json=principal.__dict__)
		response.raise_for_status()
		response_json = response.json()

		if error := response_json.get("error"):
			frappe.throw(error)

		return f"api_{base64.b64encode(f'{name}:{secret}'.encode()).decode()}"

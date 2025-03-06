# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import Order

from mail.mail.doctype.dns_record.dns_record import create_or_update_dns_record
from mail.mail.doctype.mail_server_config.mail_server_config import create_mail_server_config
from mail.mail.doctype.mail_settings.mail_settings import (
	validate_mail_settings,
)
from mail.utils.dns import get_dns_record

if TYPE_CHECKING:
	from mail.mail.doctype.mail_server_config.mail_server_config import MailServerConfig


class MailServer(Document):
	def autoname(self) -> None:
		self.server = self.server.lower()
		self.name = self.server

	def validate(self) -> None:
		if self.is_new():
			validate_mail_settings()

		self.validate_server()
		self.validate_cluster()
		self.validate_cluster_node_id()

	def on_update(self) -> None:
		if self.has_value_changed("enabled"):
			create_or_update_spf_dns_record()

	def on_trash(self) -> None:
		if frappe.session.user != "Administrator":
			frappe.throw(_("Only Administrator can delete Mail Server."))

		if frappe.db.get_value("Mail Cluster", self.cluster, "outbound"):
			self.db_set("enabled", 0)
			create_or_update_spf_dns_record()

	def validate_server(self) -> None:
		"""Validates the server and fetches the IP addresses."""

		if self.is_new() and frappe.db.exists("Mail Server", self.server):
			frappe.throw(_("Mail Server {0} already exists.").format(frappe.bold(self.server)))

		if ipv4_addresses := [r.address for r in get_dns_record(self.server, "A") or []]:
			if len(ipv4_addresses) > 1:
				frappe.throw(
					_("Multiple IPv4 addresses found for Mail Server {0}. Found: {1}.").format(
						frappe.bold(self.server), ", ".join(ipv4_addresses)
					)
				)

			self.public_ipv4 = ipv4_addresses[0]

		if ipv6_addresses := [r.address for r in get_dns_record(self.server, "AAAA") or []]:
			if len(ipv6_addresses) > 1:
				frappe.throw(
					_("Multiple IPv6 addresses found for Mail Server {0}. Found: {1}.").format(
						frappe.bold(self.server), ", ".join(ipv6_addresses)
					)
				)

			self.public_ipv6 = ipv6_addresses[0]

	def validate_cluster(self) -> None:
		"""Validates the cluster."""

		if not frappe.db.get_value("Mail Cluster", self.cluster, "enabled"):
			frappe.throw(_("Mail Cluster {0} is disabled.").format(frappe.bold(self.cluster)))

	def validate_cluster_node_id(self) -> None:
		"""Validates the cluster node ID."""

		if frappe.db.exists(
			"Mail Server",
			{
				"cluster": self.cluster,
				"cluster_node_id": self.cluster_node_id,
				"name": ["!=", self.name],
			},
		):
			frappe.throw(
				_("Node ID {0} already assigned to another Mail Server.").format(
					frappe.bold(self.cluster_node_id)
				)
			)

	@frappe.whitelist()
	def generate_config(self) -> None:
		"""Generates the Mail Server Config."""

		frappe.only_for("System Manager")
		self._generate_config()
		frappe.msgprint(_("Mail Server Config generated successfully."), indicator="green", alert=True)

	def _generate_config(self) -> "MailServerConfig":
		"""Generates the Mail Server Config."""

		return create_mail_server_config(self.name)


def create_or_update_spf_dns_record(spf_host: str | None = None) -> None:
	"""Refreshes the SPF DNS Record."""

	mail_settings = frappe.get_single("Mail Settings")
	spf_host = spf_host or mail_settings.spf_host

	SERVER = frappe.qb.DocType("Mail Server")
	CLUSTER = frappe.qb.DocType("Mail Cluster")
	outbound_servers = (
		frappe.qb.from_(CLUSTER)
		.join(SERVER)
		.on(CLUSTER.name == SERVER.cluster)
		.select(SERVER.name)
		.where((CLUSTER.enabled == 1) & (CLUSTER.outbound == 1) & (SERVER.enabled == 1))
		.orderby(SERVER.name, order=Order.asc)
	).run(pluck="name")

	if outbound_servers:
		outbound_servers = [f"a:{outbound_server}" for outbound_server in outbound_servers]
		create_or_update_dns_record(
			host=spf_host,
			type="TXT",
			value=f"v=spf1 {' '.join(outbound_servers)} ~all",
			ttl=mail_settings.default_ttl,
			category="Server Record",
		)
	else:
		if spf_dns_record := frappe.db.exists("DNS Record", {"host": spf_host, "type": "TXT"}):
			frappe.delete_doc("DNS Record", spf_dns_record, ignore_permissions=True)


def on_doctype_update() -> None:
	frappe.db.add_unique(
		"Mail Server", ["cluster", "cluster_node_id"], constraint_name="unique_cluster_node_id"
	)

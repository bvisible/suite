# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import Order

from mail.mail.doctype.dns_record.dns_record import create_or_update_dns_record
from mail.mail.doctype.mail_settings.mail_settings import (
	validate_mail_settings,
)
from mail.utils import flatten_dict, hash_password
from mail.utils.dns import get_dns_record

PROTOCOL_MAP = {
	"SMTP": "smtp",
	"LMTP": "lmtp",
	"HTTP": "http",
	"IMAP4": "imap",
	"POP3": "pop3",
	"ManageSieve": "managesieve",
}
STORE_TYPE_MAP = {
	"RocksDB": "rocksdb",
	"FoundationDB": "foundationdb",
	"PostgreSQL": "postgresql",
	"mySQL": "mysql",
	"SQLite": "sqlite",
	"S3-compatible": "s3",
	"Redis/Memcached": "redis",
	"ElasticSearch": "elasticsearch",
	"Azure blob storage": "azure",
	"Filesystem": "fs",
	"SQL with Replicas": "sql-read-replica",
	"Sharded Blob Store": "sharded-blob",
	"Sharded In-Memory Store": "sharded-in-memory",
}
LOCAL_KEYS = [
	"store.*",
	"directory.*",
	"tracer.*",
	"!server.blocked-ip.*",
	"!server.allowed-ip.*",
	"server.*",
	"config.local-keys.*",
	"certificate.*",
	"cluster.*",
	"storage.data",
	"storage.blob",
	"storage.lookup",
	"storage.fts",
	"storage.directory",
	"authentication.fallback-admin.*",
	"enterprise.license-key",
]


class MailAgent(Document):
	@property
	def config(self) -> str:
		return get_config_toml(agent=self.name)

	def autoname(self) -> None:
		self.agent = self.agent.lower()
		self.name = self.agent

	def validate(self) -> None:
		if self.is_new():
			validate_mail_settings()

		self.validate_agent()
		self.validate_agent_group()
		self.validate_cluster_node_id()

	def on_update(self) -> None:
		if self.has_value_changed("enabled"):
			create_or_update_spf_dns_record()

	def on_trash(self) -> None:
		if frappe.session.user != "Administrator":
			frappe.throw(_("Only Administrator can delete Mail Agent."))

		if frappe.db.get_value("Mail Agent Group", self.agent_group, "outbound"):
			self.db_set("enabled", 0)
			create_or_update_spf_dns_record()

	def validate_agent(self) -> None:
		"""Validates the agent and fetches the IP addresses."""

		if self.is_new() and frappe.db.exists("Mail Agent", self.agent):
			frappe.throw(_("Mail Agent {0} already exists.").format(frappe.bold(self.agent)))

		if ipv4_addresses := [r.address for r in get_dns_record(self.agent, "A") or []]:
			if len(ipv4_addresses) > 1:
				frappe.throw(
					_("Multiple IPv4 addresses found for Mail Agent {0}. Found: {1}.").format(
						frappe.bold(self.agent), ", ".join(ipv4_addresses)
					)
				)

			self.public_ipv4 = ipv4_addresses[0]

		if ipv6_addresses := [r.address for r in get_dns_record(self.agent, "AAAA") or []]:
			if len(ipv6_addresses) > 1:
				frappe.throw(
					_("Multiple IPv6 addresses found for Mail Agent {0}. Found: {1}.").format(
						frappe.bold(self.agent), ", ".join(ipv6_addresses)
					)
				)

			self.public_ipv6 = ipv6_addresses[0]

	def validate_agent_group(self) -> None:
		"""Validates the Mail Agent Group."""

		if not frappe.db.get_value("Mail Agent Group", self.agent_group, "enabled"):
			frappe.throw(_("Mail Agent Group {0} is disabled.").format(frappe.bold(self.agent_group)))

	def validate_cluster_node_id(self) -> None:
		"""Validates the cluster node ID."""

		if frappe.db.exists(
			"Mail Agent",
			{
				"agent_group": self.agent_group,
				"cluster_node_id": self.cluster_node_id,
				"name": ["!=", self.name],
			},
		):
			frappe.throw(
				_("Node ID {0} already assigned to another Mail Agent.").format(
					frappe.bold(self.cluster_node_id)
				)
			)


def create_or_update_spf_dns_record(spf_host: str | None = None) -> None:
	"""Refreshes the SPF DNS Record."""

	mail_settings = frappe.get_single("Mail Settings")
	spf_host = spf_host or mail_settings.spf_host

	MAIL_AGENT = frappe.qb.DocType("Mail Agent")
	AGENT_GROUP = frappe.qb.DocType("Mail Agent Group")
	outbound_agents = (
		frappe.qb.from_(AGENT_GROUP)
		.join(MAIL_AGENT)
		.on(AGENT_GROUP.name == MAIL_AGENT.agent_group)
		.select(MAIL_AGENT.name)
		.where((AGENT_GROUP.enabled == 1) & (AGENT_GROUP.outbound == 1) & (MAIL_AGENT.enabled == 1))
		.orderby(MAIL_AGENT.name, order=Order.asc)
	).run(pluck="name")

	if outbound_agents:
		outbound_agents = [f"a:{outbound_agent}" for outbound_agent in outbound_agents]
		create_or_update_dns_record(
			host=spf_host,
			type="TXT",
			value=f"v=spf1 {' '.join(outbound_agents)} ~all",
			ttl=mail_settings.default_ttl,
			category="Server Record",
		)
	else:
		if spf_dns_record := frappe.db.exists("DNS Record", {"host": spf_host, "type": "TXT"}):
			frappe.delete_doc("DNS Record", spf_dns_record, ignore_permissions=True)


def get_config_toml(agent: str) -> str | None:
	"""Returns the TOML configuration for the Mail Agent."""

	def get_listeners(listeners: list) -> dict:
		"""Returns the listener configuration for the Mail Agent."""

		listeners_config = {}
		for listener in listeners:
			if listener.listener_id in listeners_config:
				continue

			bind_addresses = listener.bind_addresses.split("\n")
			bind = bind_addresses[0] if len(bind_addresses) == 1 else bind_addresses
			listeners_config[listener.listener_id] = {
				"bind": bind,
				"protocol": PROTOCOL_MAP[listener.protocol],
			}

			if listener.implicit_tls:
				listeners_config[listener.listener_id]["tls"] = {"implicit": True}

		return listeners_config

	def get_seed_nodes(agent: str, agent_group: str) -> dict:
		"""Returns the seed nodes for the Mail Agent."""

		seed_nodes = []
		for a in frappe.db.get_all(
			"Mail Agent",
			filters={"agent_group": agent_group, "name": ["!=", agent]},
			fields=[
				"private_ipv4",
				"private_ipv6",
				"public_ipv4",
				"public_ipv6",
				"cluster_advertise_address",
			],
		):
			if not a["cluster_advertise_address"]:
				continue

			if seed_node := a[frappe.scrub(a["cluster_advertise_address"])]:
				seed_nodes.append(seed_node)

		num_digits = len(str(len(seed_nodes) - 1))
		return {f"{str(i).zfill(num_digits)}": v for i, v in enumerate(seed_nodes)}

	def get_local_keys() -> dict:
		"""Returns the local keys for the configuration."""

		num_digits = len(str(len(LOCAL_KEYS) - 1))
		return {f"{str(i).zfill(num_digits)}": v for i, v in enumerate(LOCAL_KEYS)}

	def get_stores(stores: list) -> dict:
		"""Returns the store configuration for the Mail Agent."""

		store_config = {}
		for store in stores:
			if store.store_id in store_config:
				continue

			store_config.setdefault(store.store_id, {})
			match store.type:
				case "RocksDB":
					store_config.update(
						{
							store.store_id: {
								"type": STORE_TYPE_MAP[store.type],
								"path": store.path,
								"compression": store.compression.lower(),
								"min-blob-size": store.min_blob_size_bytes,
								"write-buffer-size": store.write_buffer_size_mb,
								"workers": store.thread_pool_size,
								"purge": {"frequency": store.purge_frequency_cron},
							}
						}
					)
				case "mySQL":
					store_config.update(
						{
							store.store_id: {
								"type": STORE_TYPE_MAP[store.type],
								"host": store.hostname,
								"port": store.port,
								"database": store.database,
								"user": store.username,
								"password": store.get_password("password") if store.password else None,
								"max-allowed-packet": store.max_allowed_packet_bytes,
								"timeout": f"{store.timeout_seconds}s" if store.timeout_seconds else 0,
								"compression": store.compression.lower(),
								"purge": {"frequency": store.purge_frequency_cron},
								"tls": {
									"enable": store.enable_tls,
									"allow-invalid-certs": store.allow_invalid_certs,
								},
								"pool": {
									"max-connections": store.max_connections,
									"min-connections": store.min_connections,
								},
							}
						}
					)

		return store_config

	agent = frappe.get_doc("Mail Agent", agent)
	agent_group = frappe.get_doc("Mail Agent Group", agent.agent_group)

	config = {
		"authentication": {
			"fallback-admin": {
				"user": agent_group.admin_username,
				"secret": hash_password(agent_group.get_password("admin_password")),
			}
		},
		"server": {
			"hostname": agent.agent,
			"max-connections": agent.server_max_connections,
			"listener": get_listeners(agent.listeners or agent_group.listeners),
			"socket": {
				"backlog": 1024,
				"nodelay": True,
				"reuse-addr": True,
				"reuse-port": True,
			},
		},
		"cluster": {
			"node-id": agent.cluster_node_id,
			"bind-addr": agent.cluster_bind_address,
			"bind-port": agent.cluster_bind_port,
			"advertise-addr": agent.get(frappe.scrub(agent.cluster_advertise_address)),
			"key": agent_group.get_password("cluster_encryption_key"),
			"heartbeat": f"{agent.cluster_heartbeat}s" if agent.cluster_heartbeat else 0,
			"seed-nodes": get_seed_nodes(agent.name, agent_group.name),
		},
		"config": {
			"local-keys": get_local_keys(),
		},
		"directory": {
			f"{agent_group.directory_store}": {
				"type": "internal",
				"store": f"{agent_group.directory_store}",
				"cache": {
					"size": 1048576,
					"ttl": {
						"negative": "10m",
						"positive": "1h",
					},
				},
			}
		},
		"storage": {
			"directory": agent_group.directory_store,
			"data": agent_group.data_store,
			"blob": agent_group.blob_store,
			"fts": agent_group.fts_store,
			"lookup": agent_group.in_memory_store,
			"full-text": {"default-language": agent_group.default_language},
		},
		"store": get_stores(agent_group.stores),
		"tracer": {
			"log": {
				"type": "log",
				"path": "/opt/stalwart-mail/logs",
				"prefix": "stalwart.log",
				"rotate": "daily",
				"level": "info",
				"ansi": False,
				"enable": True,
			}
		},
	}

	toml_lines = []
	for key, value in sorted(flatten_dict(config).items()):
		if value or isinstance(value, bool):
			if isinstance(value, str):
				toml_lines.append(f'{key} = "{value}"')
			elif isinstance(value, bool):
				toml_lines.append(f"{key} = {str(value).lower()}")
			else:
				toml_lines.append(f"{key} = {value}")

	return "\n".join(toml_lines)


def on_doctype_update() -> None:
	frappe.db.add_unique(
		"Mail Agent", ["agent_group", "cluster_node_id"], constraint_name="unique_cluster_node_id"
	)

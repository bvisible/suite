# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document

from mail.mail.doctype.dns_record.dns_record import create_or_update_dns_record
from mail.mail.doctype.mail_settings.mail_settings import (
	validate_mail_settings,
)
from mail.utils import flatten_dict, hash_password
from mail.utils.dns import get_dns_record


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
		if self.has_value_changed("enabled") or self.has_value_changed("enable_outbound"):
			create_or_update_spf_dns_record()

	def on_trash(self) -> None:
		if frappe.session.user != "Administrator":
			frappe.throw(_("Only Administrator can delete Mail Agent."))

		if self.enable_outbound:
			self.db_set("enabled", 0)
			create_or_update_spf_dns_record()

	def validate_agent(self) -> None:
		"""Validates the agent and fetches the IP addresses."""

		if self.is_new() and frappe.db.exists("Mail Agent", self.agent):
			frappe.throw(_("Mail Agent {0} already exists.").format(frappe.bold(self.agent)))

		self.ipv4_addresses = "\n".join([r.address for r in get_dns_record(self.agent, "A") or []])
		self.ipv6_addresses = "\n".join([r.address for r in get_dns_record(self.agent, "AAAA") or []])

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
	outbound_agents = frappe.db.get_all(
		"Mail Agent",
		filters={"enabled": 1, "enable_outbound": 1},
		pluck="agent",
		order_by="agent asc",
	)

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

	def get_seed_nodes(agent: str, agent_group: str) -> dict:
		"""Returns the seed nodes for the Mail Agent."""

		seed_nodes = []
		for a in frappe.db.get_all(
			"Mail Agent",
			filters={"agent_group": agent_group, "name": ["!=", agent]},
			fields=["public_ip", "private_ip", "cluster_advertise_address"],
		):
			if not a["cluster_advertise_address"]:
				continue

			if seed_node := a[frappe.scrub(a["cluster_advertise_address"])]:
				seed_nodes.append(seed_node)

		num_digits = len(str(len(seed_nodes) - 1))
		return {f"{str(i).zfill(num_digits)}": v for i, v in enumerate(seed_nodes)}

	def get_local_keys() -> dict:
		"""Returns the local keys for the configuration."""

		local_keys = [
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
		num_digits = len(str(len(local_keys) - 1))
		return {f"{str(i).zfill(num_digits)}": v for i, v in enumerate(local_keys)}

	def get_stores(*stores) -> dict:
		"""Returns the store configuration for the Mail Agent."""

		store_type_map = {
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
								"type": store_type_map[store.type],
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
								"type": store_type_map[store.type],
								"host": store.hostname,
								"port": store.port,
								"database": store.database,
								"user": store.username,
								"password": store.get_password("password"),
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
	directory_store = frappe.get_doc("Mail Agent Store", agent_group.directory_store)
	data_store = frappe.get_doc("Mail Agent Store", agent_group.data_store)
	blob_store = frappe.get_doc("Mail Agent Store", agent_group.blob_store)
	fts_store = frappe.get_doc("Mail Agent Store", agent_group.fts_store)
	lookup_store = frappe.get_doc("Mail Agent Store", agent_group.in_memory_store)

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
			"listener": {
				"http": {"bind": "[::]:8080", "protocol": "http"},
				"https": {
					"bind": "[::]:443",
					"protocol": "http",
					"tls": {
						"implicit": True,
					},
				},
				"imap": {"bind": "[::]:143", "protocol": "imap"},
				"imaptls": {
					"bind": "[::]:993",
					"protocol": "imap",
					"tls": {
						"implicit": True,
					},
				},
				"pop3": {"bind": "[::]:110", "protocol": "pop3"},
				"pop3s": {
					"bind": "[::]:995",
					"protocol": "pop3",
					"tls": {
						"implicit": True,
					},
				},
				"sieve": {"bind": "[::]:4190", "protocol": "managesieve"},
				"smtp": {"bind": "[::]:25", "protocol": "smtp"},
				"submission": {
					"bind": "[::]:587",
					"protocol": "smtp",
				},
				"submissions": {
					"bind": "[::]:465",
					"protocol": "smtp",
					"tls": {
						"implicit": True,
					},
				},
			},
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
			f"{directory_store.store_id}": {
				"type": "internal",
				"store": f"{directory_store.store_id}",
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
			"directory": directory_store.store_id,
			"data": data_store.store_id,
			"blob": blob_store.store_id,
			"fts": fts_store.store_id,
			"lookup": lookup_store.store_id,
		},
		"store": get_stores(directory_store, data_store, blob_store, fts_store, lookup_store),
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
		"Mail Agent", ["cluster_node_id", "agent_group"], constraint_name="unique_cluster_node_id"
	)

# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from mail.utils import flatten_dict

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
	"storage.directory",
	"storage.data",
	"storage.encryption.*",
	"storage.blob",
	"storage.fts",
	"storage.full-text.*",
	"storage.lookup",
	"jmap.account.*",
	"jmap.email.*",
	"jmap.protocol.*",
	"authentication.fallback-admin.*",
	"enterprise.license-key",
]
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
PROTOCOL_MAP = {
	"SMTP": "smtp",
	"LMTP": "lmtp",
	"HTTP": "http",
	"IMAP4": "imap",
	"POP3": "pop3",
	"ManageSieve": "managesieve",
}


class MailServerConfig(Document):
	@property
	def config(self) -> str | None:
		"""Returns the TOML configuration for the Mail Server."""

		frappe.only_for("System Manager")

		if self.config_toml:
			return self.get_password("config_toml")

	def before_insert(self) -> None:
		self.generate_config_toml()

	def generate_config_toml(self) -> None:
		"""Generates the TOML configuration for the Mail Server."""

		self.config_toml = get_config_toml(self.server)


def create_mail_server_config(server: str) -> "MailServerConfig":
	"""Creates a new Mail Server Config."""

	config = frappe.new_doc("Mail Server Config")
	config.server = server
	config.insert()

	return config


def get_mail_server_config(server: str) -> MailServerConfig | None:
	"""Returns the Mail Server Config."""

	if config := frappe.db.exists("Mail Server Config", {"server": server}):
		return frappe.get_doc("Mail Server Config", config)


def get_config_toml(server: str) -> str | None:
	"""Returns the TOML configuration for the Mail Server."""

	def get_listeners(listeners: list) -> dict:
		"""Returns the listener configuration for the Mail Server."""

		listeners_config = {}
		for listener in listeners:
			if listener.listener_id in listeners_config:
				continue

			bind_addresses = listener.bind_addresses.split("\n")
			bind = bind_addresses[0] if len(bind_addresses) == 1 else bind_addresses
			listeners_config[listener.listener_id] = {
				"bind": bind,
				"protocol": PROTOCOL_MAP[listener.protocol],
				"tls": {"implicit": bool(listener.implicit_tls)},
			}

		return listeners_config

	def get_seed_nodes(server: str, cluster: str) -> dict:
		"""Returns the seed nodes for the Mail Server."""

		seed_nodes = []
		for s in frappe.db.get_all(
			"Mail Server",
			filters={"enabled": 1, "cluster": cluster, "name": ["!=", server]},
			fields=[
				"private_ipv4",
				"private_ipv6",
				"public_ipv4",
				"public_ipv6",
				"cluster_advertise_address",
			],
		):
			if not s["cluster_advertise_address"]:
				continue

			if seed_node := s[frappe.scrub(s["cluster_advertise_address"])]:
				seed_nodes.append(seed_node)

		num_digits = len(str(len(seed_nodes) - 1))
		return {f"{str(i).zfill(num_digits)}": v for i, v in enumerate(seed_nodes)}

	def get_local_keys() -> dict:
		"""Returns the local keys for the configuration."""

		num_digits = len(str(len(LOCAL_KEYS) - 1))
		return {f"{str(i).zfill(num_digits)}": v for i, v in enumerate(LOCAL_KEYS)}

	def get_stores(stores: list) -> dict:
		"""Returns the store configuration for the Mail Server."""

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
									"enable": bool(store.enable_tls),
									"allow-invalid-certs": bool(store.allow_invalid_certs),
								},
								"pool": {
									"max-connections": store.max_connections,
									"min-connections": store.min_connections,
								},
							}
						}
					)

		return store_config

	server = frappe.get_doc("Mail Server", server)
	cluster = frappe.get_doc("Mail Cluster", server.cluster)

	config = {
		"authentication": {
			"fallback-admin": {
				"user": cluster.admin_username,
				"secret": cluster.admin_password_hash,
			}
		},
		"server": {
			"hostname": server.server,
			"proxy": {
				"trusted-networks": cluster.proxy_trusted_networks.split("\n")
				if cluster.proxy_trusted_networks
				else []
			},
			"max-connections": server.server_max_connections,
			"listener": get_listeners(server.listeners or cluster.listeners),
			"socket": {
				"backlog": 1024,
				"nodelay": True,
				"reuse-addr": True,
				"reuse-port": True,
			},
		},
		"cluster": {
			"node-id": server.cluster_node_id,
			"bind-addr": server.cluster_bind_address,
			"bind-port": cluster.cluster_bind_port,
			"advertise-addr": server.get(frappe.scrub(server.cluster_advertise_address)),
			"key": cluster.get_password("cluster_encryption_key"),
			"heartbeat": f"{server.cluster_heartbeat}s" if server.cluster_heartbeat else 0,
			"seed-nodes": get_seed_nodes(server.name, cluster.name),
		},
		"config": {
			"local-keys": get_local_keys(),
		},
		"directory": {
			f"{cluster.directory_storage}": {
				"type": "internal",
				"store": f"{cluster.directory_storage}",
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
			"directory": cluster.directory_storage,
			"data": cluster.data_storage,
			"encryption": {
				"enable": bool(cluster.enable_encryption_at_rest),
				"append": bool(cluster.encrypt_on_append),
			},
			"blob": cluster.blob_storage,
			"fts": cluster.fts_storage,
			"full-text": {"default-language": cluster.default_language},
			"lookup": cluster.in_memory_storage,
		},
		"jmap": {
			"account": {"purge": {"frequency": cluster.jmap_frequency_cron}},
			"email": {
				"auto-expunge": f"{cluster.jmap_trash_auto_expunge_days}d"
				if cluster.jmap_trash_auto_expunge_days
				else 0
			},
			"protocol": {
				"changes": {
					"max-history": f"{cluster.jmap_changes_history_days}d"
					if cluster.jmap_changes_history_days
					else 0
				}
			},
		},
		"store": get_stores(cluster.stores),
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
			match value:
				case str():
					toml_lines.append(f'{key} = "{value}"')
				case bool():
					toml_lines.append(f"{key} = {str(value).lower()}")
				case list():
					formatted_list = ", ".join(f'"{v}"' if isinstance(v, str) else str(v) for v in value)
					toml_lines.append(f"{key} = [{formatted_list}]")
				case _:
					toml_lines.append(f"{key} = {value}")

	return "\n".join(toml_lines)

// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

const STORE_DEFAULTS = {
	RocksDB: {
		store_id: 'rocksdb',
		path: '/opt/stalwart-mail/data',
		compression: 'LZ4',
		min_blob_size_bytes: 16834,
		write_buffer_size_mb: 128,
		purge_frequency_cron: '0 3 * * *',
	},
	mySQL: {
		store_id: 'mysql',
		port: 3306,
		database: 'frappemail',
		timeout_seconds: 15,
		username: 'frappemail',
		compression: 'LZ4',
		purge_frequency_cron: '0 3 * * *',
		max_connections: 10,
		min_connections: 5,
	},
}

frappe.ui.form.on('Mail Agent Store', {
	type(frm) {
		frm.trigger('set_defaults')
	},

	set_defaults(frm) {
		if (!frm.doc.__islocal || !frm.doc.type) return

		const defaults = STORE_DEFAULTS[frm.doc.type]
		if (!defaults) return

		Object.entries(defaults).forEach(([key, value]) => frm.set_value(key, value))
	},
})

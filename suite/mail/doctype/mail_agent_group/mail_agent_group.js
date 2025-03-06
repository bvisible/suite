// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

const STORES_PRESET = {
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

frappe.ui.form.on('Mail Agent Group', {
	setup(frm) {
		frm.trigger('initialize_defaults')
	},

	refresh(frm) {
		frm.trigger('add_actions')
	},

	initialize_defaults(frm) {
		if (!frm.doc.__islocal) return

		frappe.call({
			doc: frm.doc,
			method: 'initialize_defaults',
			freeze: true,
			freeze_message: __('Initializing Defaults...'),
			callback: (r) => {
				if (!r.exc) {
					frm.refresh()
				}
			},
		})
	},

	add_actions(frm) {
		if (frm.doc.__islocal) return

		if (frm.doc.admin_password) {
			if (!frappe.user_roles.includes('System Manager')) return

			frm.add_custom_button(__('Show Password'), () => {
				frm.trigger('show_password')
			})
		}

		if (frm.doc.base_url) {
			if (!frappe.user_roles.includes('System Manager')) return

			frm.add_custom_button(
				__('Generate API Key'),
				() => {
					frm.trigger('generate_api_key')
				},
				__('Actions'),
			)
		}
	},

	show_password(frm) {
		frappe.call({
			doc: frm.doc,
			method: 'get_admin_password',
			freeze: true,
			freeze_message: __('Getting Password...'),
			callback: (r) => {
				if (!r.exc) {
					frappe.msgprint(r.message)
				}
			},
		})
	},

	generate_api_key(frm) {
		frappe.call({
			doc: frm.doc,
			method: 'generate_api_key',
			freeze: true,
			freeze_message: __('Generating API Key...'),
			callback: (r) => {
				if (!r.exc) {
					frm.refresh()
				}
			},
		})
	},
})

frappe.ui.form.on('Mail Server Store', {
	type(frm, cdt, cdn) {
		const row = locals[cdt][cdn]

		if (!row.type) return

		const defaults = STORES_PRESET[row.type]
		if (!defaults) return

		Object.entries(defaults).forEach(([key, value]) =>
			frappe.model.set_value(cdt, cdn, key, value),
		)
		refresh_field('stores')
	},
})

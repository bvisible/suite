// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mail Server', {
	setup(frm) {
		frm.trigger('set_queries')
	},

	refresh(frm) {
		frm.trigger('add_actions')
	},

	set_queries(frm) {
		frm.set_query('cluster', () => ({
			filters: {
				enabled: 1,
			},
		}))
	},

	add_actions(frm) {
		if (frm.doc.__islocal) return

		if (!frappe.user_roles.includes('System Manager')) return

		frm.add_custom_button(
			__('Generate Mail Server Config'),
			() => {
				frm.trigger('generate_config')
			},
			__('Actions'),
		)
	},

	generate_config(frm) {
		frappe.call({
			doc: frm.doc,
			method: 'generate_config',
			freeze: true,
			freeze_message: __('Generating Mail Server Config...'),
			callback: (r) => {
				if (!r.exc) {
					frm.refresh()
				}
			},
		})
	},
})

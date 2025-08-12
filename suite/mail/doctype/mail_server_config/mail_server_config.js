// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mail Server Config', {
	refresh(frm) {
		frm.trigger('add_actions')
	},

	add_actions(frm) {
		if (frm.doc.__islocal) return

		if (frappe.user_roles.includes('System Manager')) {
			frm.add_custom_button(__('Deploy'), () => frm.trigger('deploy'), __('Actions'))
		}
	},

	deploy(frm) {
		frappe.call({
			doc: frm.doc,
			method: 'deploy',
			freeze: true,
			freeze_message: __('Deploying Configuration...'),
			callback: (r) => {
				if (!r.exc) {
					frm.refresh()
				}
			},
		})
	},
})

// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mail Account', {
	setup(frm) {
		frm.trigger('set_queries')
	},

	refresh(frm) {
		frm.trigger('add_show_password')
		frm.trigger('add_actions')
	},

	set_queries(frm) {
		frm.set_query('domain_name', () => ({
			filters: {
				enabled: 1,
				is_verified: 1,
			},
		}))

		frm.set_query('user', () => ({
			query: 'mail.utils.query.get_users_with_mail_user_role',
			filters: {
				enabled: 1,
				role: 'Mail User',
			},
		}))
	},

	add_show_password(frm) {
		if (frm.doc.__islocal) return

		if (frm.doc.password) {
			frm.add_custom_button(__('Show Password'), () => frm.trigger('get_account_password'))
		}
	},

	add_actions(frm) {
		if (frm.doc.__islocal) return

		if (frappe.user_roles.includes('System Manager')) {
			frm.add_custom_button(
				__('Sync JMAP Identities'),
				() => frm.trigger('sync_jmap_identities'),
				__('Actions'),
			)
		}

		frm.add_custom_button(
			__('Regenerate Password'),
			() => frm.trigger('regenerate_password'),
			__('Actions'),
		)
	},

	get_account_password(frm) {
		frappe.call({
			doc: frm.doc,
			method: 'get_account_password',
			freeze: true,
			freeze_message: __('Getting Password...'),
			callback: (r) => {
				if (!r.exc) {
					frappe.msgprint(r.message)
				}
			},
		})
	},

	sync_jmap_identities(frm) {
		frappe.call({
			doc: frm.doc,
			method: 'sync_jmap_identities',
			freeze: true,
			freeze_message: __('Syncing JMAP Identities...'),
			callback: (r) => {
				if (!r.exc) {
					frm.refresh()
				}
			},
		})
	},

	regenerate_password(frm) {
		frappe.call({
			doc: frm.doc,
			method: 'regenerate_password',
			freeze: true,
			freeze_message: __('Regenerating Password...'),
			callback: (r) => {
				if (!r.exc) {
					frm.refresh()
				}
			},
		})
	},
})

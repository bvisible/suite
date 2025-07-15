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
			frm.add_custom_button(
				__('Sync JMAP Vacation Response'),
				() => frm.trigger('sync_jmap_vacation_response'),
				__('Actions'),
			)
		}

		if (frm.doc.enabled && frappe.user_roles.includes('Mail Admin')) {
			frm.add_custom_button(__('Set Quota'), () => frm.trigger('set_quota'), __('Actions'))
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

	sync_jmap_vacation_response(frm) {
		frappe.call({
			method: 'mail.mail.doctype.mail_account.mail_account.sync_jmap_vacation_response',
			args: {
				account: frm.doc.name,
				raise_exception: true,
			},
			freeze: true,
			freeze_message: __('Syncing JMAP Vacation Response...'),
			callback: (r) => {
				if (!r.exc) {
					frm.refresh()
				}
			},
		})
	},

	set_quota(frm) {
		const dialog = new frappe.ui.Dialog({
			title: __('Set Quota'),
			size: 'small',
			fields: [
				{
					fieldname: 'quota',
					fieldtype: 'Float',
					label: __('Quota (in GB)'),
					reqd: 1,
					precision: 5,
					default: frm.doc.disk_quota || 0,
				},
			],
			primary_action_label: __('Set Quota'),
			primary_action: (data) => {
				const quota = data.quota
				if (quota < 0) {
					frappe.msgprint(__('Quota cannot be negative.'))
					return
				}

				frappe.call({
					doc: frm.doc,
					method: 'set_quota',
					args: {
						quota: Math.round(quota * 1024 * 1024 * 1024),
					},
					freeze: true,
					freeze_message: __('Setting Quota...'),
					callback: (r) => {
						if (!r.exc) {
							frm.refresh()
							dialog.hide()
						}
					},
				})
			},
		})

		dialog.show()
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

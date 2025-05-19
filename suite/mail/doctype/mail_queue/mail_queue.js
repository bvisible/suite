// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mail Queue', {
	refresh(frm) {
		if (!frm.doc.__islocal) {
			frm.disable_save()
			frm.trigger('add_comments')
		}
	},

	add_comments(frm) {
		if (
			!frm.doc.__islocal &&
			['Failed to Draft', 'Failed to Submit'].includes(frm.doc.status) &&
			frm.doc.error_message
		) {
			frm.dashboard.add_comment(__(frm.doc.error_message), 'red', true)
		}
	},
})

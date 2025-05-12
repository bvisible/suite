// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mail Queue', {
	refresh(frm) {
		frm.trigger('add_comments')
	},

	save_as_draft: mutually_exclusive_checkboxes('save_as_draft', [
		'move_to_sent',
		'delete_after_sending',
	]),
	move_to_sent: mutually_exclusive_checkboxes('move_to_sent', [
		'save_as_draft',
		'delete_after_sending',
	]),
	delete_after_sending: mutually_exclusive_checkboxes('delete_after_sending', [
		'save_as_draft',
		'move_to_sent',
	]),

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

function mutually_exclusive_checkboxes(active_field, fields_to_reset) {
	return function (frm) {
		if (frm.doc[active_field]) {
			fields_to_reset.forEach((field) => frm.set_value(field, 0))
		}
	}
}

// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Email Message', {
	refresh(frm) {
		frm.trigger('add_actions')
	},

	add_actions(frm) {
		if (frm.doc.has_attachment) {
			frm.add_custom_button(
				__('Load Attachments'),
				() => {
					frm.trigger('load_attachments')
				},
				__('Actions'),
			)
		}

		if (!frm.doc.message) {
			frm.add_custom_button(
				__('Load MIME Message'),
				() => {
					frm.trigger('load_mime_message')
				},
				__('Actions'),
			)
		}
	},

	load_attachments(frm) {
		frappe.call({
			doc: frm.doc,
			method: 'preload_attachments_to_cache',
			freeze: true,
			freeze_message: __('Loading Attachments...'),
			callback: (r) => {
				if (!r.exc) {
					frm.refresh()
				}
			},
		})
	},

	load_mime_message(frm) {
		frappe.call({
			doc: frm.doc,
			method: 'get_mime_message',
			freeze: true,
			freeze_message: __('Loading MIME Message...'),
			callback: (r) => {
				if (!r.exc) {
					frm.refresh()
				}
			},
		})
	},
})

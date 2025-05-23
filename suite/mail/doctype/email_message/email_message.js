// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Email Message', {
	refresh(frm) {
		frm.disable_save()

		if (!frm.doc.__islocal && !frm.doc.destroyed) {
			if (!frm.doc.draft) {
				frm.trigger('add_seen_flagged_buttons')
			}

			frm.trigger('add_destroy_button')

			if (!frm.doc.draft) {
				frm.trigger('add_reply_forward_buttons')
				frm.trigger('add_move_buttons')
			}

			frm.trigger('add_actions')
		}
	},

	add_seen_flagged_buttons(frm) {
		function add_toggle_button(field, method, labels, freeze_messages) {
			const current = frm.doc[field]
			const label = current ? __(labels[1]) : __(labels[0])
			const freeze_message = current ? __(freeze_messages[1]) : __(freeze_messages[0])

			frm.add_custom_button(label, () => {
				frappe.call({
					doc: frm.doc,
					method,
					args: {
						[field]: !current,
					},
					freeze: true,
					freeze_message,
					callback: (r) => {
						if (!r.exc) {
							frm.refresh()
						}
					},
				})
			})
		}

		add_toggle_button(
			'seen',
			'set_seen',
			['Seen', 'Unseen'],
			['Marking as Seen...', 'Marking as Unseen...'],
		)

		add_toggle_button(
			'flagged',
			'set_flagged',
			['Flag', 'Unflag'],
			['Flagging...', 'Unflagging...'],
		)
	},

	add_destroy_button(frm) {
		if (!frm.doc.destroyed) {
			frm.add_custom_button(__('Destroy'), () => {
				frappe.confirm(__('Are you sure you want to destroy this email?'), () => {
					frappe.call({
						doc: frm.doc,
						method: 'destroy',
						freeze: true,
						freeze_message: __('Destroying...'),
						callback: (r) => {
							if (!r.exc) {
								frm.refresh()
							}
						},
					})
				})
			})
		}
	},

	add_reply_forward_buttons(frm) {
		frm.add_custom_button(
			__('Reply'),
			() => {
				frappe.model.open_mapped_doc({
					method: 'mail.mail.doctype.email_message.email_message.reply',
					frm: frm,
					freeze: true,
					freeze_message: __('Loading...'),
				})
			},
			__('Reply / Forward'),
		)

		frm.add_custom_button(
			__('Reply All'),
			() => {
				frappe.model.open_mapped_doc({
					method: 'mail.mail.doctype.email_message.email_message.reply_all',
					frm: frm,
					freeze: true,
					freeze_message: __('Loading...'),
				})
			},
			__('Reply / Forward'),
		)

		frm.add_custom_button(
			__('Forward'),
			() => {
				frappe.model.open_mapped_doc({
					method: 'mail.mail.doctype.email_message.email_message.forward',
					frm: frm,
					freeze: true,
					freeze_message: __('Loading...'),
				})
			},
			__('Reply / Forward'),
		)
	},

	add_move_buttons(frm) {
		const add_move_button = (label, target) => {
			frm.add_custom_button(
				__(label),
				() => frm.events.move_to_mailbox(frm, target),
				__('Move'),
			)
		}

		const current_role = frm.doc.mailbox_role

		if (current_role !== 'trash') add_move_button('Move to Trash', 'trash')
		if (current_role !== 'junk' && current_role !== 'sent')
			add_move_button('Move to Junk', 'junk')
		if (['trash', 'junk'].includes(current_role)) {
			add_move_button('Move to Inbox', 'inbox')
			add_move_button('Move to Sent', 'sent')
		}
	},

	add_actions(frm) {
		if (frm.doc.has_attachment) {
			frm.add_custom_button(
				__('Load Attachments'),
				() => {
					frappe.call({
						doc: frm.doc,
						method: 'preload_attachments_to_cache',
						args: {
							include_inline: true,
							include_regular: true,
						},
						freeze: true,
						freeze_message: __('Loading Attachments...'),
						callback: (r) => {
							if (!r.exc) {
								frm.refresh()
							}
						},
					})
				},
				__('Actions'),
			)
		}

		if (!frm.doc.message) {
			frm.add_custom_button(
				__('Load MIME Message'),
				() => {
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
				__('Actions'),
			)
		}
	},

	move_to_mailbox(frm, mailbox_role) {
		frappe.call({
			doc: frm.doc,
			method: 'move_to_mailbox',
			freeze: true,
			freeze_message: __('Moving to Mailbox...'),
			args: {
				mailbox_role: mailbox_role,
			},
			callback: (r) => {
				if (!r.exc) {
					frm.refresh()
				}
			},
		})
	},
})

// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Email Message', {
	refresh(frm) {
		frm.disable_save()

		if (!frm.doc.destroyed) {
			if (!frm.doc.__islocal) {
				if (!frm.doc.draft) {
					frm.trigger('add_reply_buttons')
					frm.trigger('add_forward_button')
					frm.trigger('add_mark_buttons')
					frm.trigger('add_move_buttons')
				}

				frm.trigger('add_actions')
			}
		}
	},

	add_reply_buttons(frm) {
		frm.add_custom_button(__('Reply'), () => {
			frappe.model.open_mapped_doc({
				method: 'mail.mail.doctype.email_message.email_message.reply',
				frm: frm,
				freeze: true,
				freeze_message: __('Loading...'),
			})
		})

		frm.add_custom_button(__('Reply All'), () => {
			frappe.model.open_mapped_doc({
				method: 'mail.mail.doctype.email_message.email_message.reply_all',
				frm: frm,
				freeze: true,
				freeze_message: __('Loading...'),
			})
		})
	},

	add_forward_button(frm) {
		frm.add_custom_button(__('Forward'), () => {
			frappe.model.open_mapped_doc({
				method: 'mail.mail.doctype.email_message.email_message.forward',
				frm: frm,
				freeze: true,
				freeze_message: __('Loading...'),
			})
		})
	},

	add_mark_buttons(frm) {
		if (frm.doc.seen) {
			frm.add_custom_button(__('Mark as Unread'), () => {
				frappe.call({
					doc: frm.doc,
					method: 'mark_as_unseen',
					freeze: true,
					freeze_message: __('Marking as Unread...'),
					callback: (r) => {
						if (!r.exc) {
							frm.refresh()
						}
					},
				})
			})
		} else {
			frm.add_custom_button(__('Mark as Read'), () => {
				frappe.call({
					doc: frm.doc,
					method: 'mark_as_seen',
					freeze: true,
					freeze_message: __('Marking as Read...'),
					callback: (r) => {
						if (!r.exc) {
							frm.refresh()
						}
					},
				})
			})
		}
	},

	add_move_buttons(frm) {
		frappe.call({
			method: 'mail.jmap.get_mailboxes_for_account',
			args: { account: frm.doc.account },
			callback: ({ message: mailboxes = [] }) => {
				const roles = Object.fromEntries(mailboxes.map((m) => [m.id, m.role]))
				const current_role = roles[frm.doc.mailbox_id]

				const add_move_button = (label, target) => {
					frm.add_custom_button(
						__(label),
						() => frm.events.move_to_mailbox(frm, target),
						__('Move'),
					)
				}

				if (current_role !== 'trash') add_move_button('Move to Trash', 'trash')
				if (current_role !== 'junk' && current_role !== 'sent')
					add_move_button('Move to Junk', 'junk')
				if (['trash', 'junk'].includes(current_role))
					add_move_button('Move to Inbox', 'inbox')
			},
		})
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

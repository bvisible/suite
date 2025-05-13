// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Email Message', {
	refresh(frm) {
		if (!frm.doc.__islocal && !frm.doc.destroyed) {
			frm.trigger('add_actions')
		}
	},

	add_actions(frm) {
		const add_button = (label, trigger) => {
			frm.add_custom_button(__(label), () => frm.trigger(trigger), __('Actions'))
		}

		if (frm.doc.has_attachment) add_button('Load Attachments', 'load_attachments')
		if (!frm.doc.message) add_button('Load MIME Message', 'load_mime_message')

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
						__('Actions'),
					)
				}

				if (current_role !== 'trash') add_move_button('Move to Trash', 'trash')
				if (current_role !== 'junk' && current_role !== 'sent')
					add_move_button('Move to Junk', 'junk')
				if (['trash', 'junk'].includes(current_role))
					add_move_button('Move to Inbox', 'inbox')
			},
		})

		if (frm.doc.seen) {
			add_button('Mark as Unread', 'mark_as_unseen')
		} else {
			add_button('Mark as Read', 'mark_as_seen')
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

	mark_as_unseen(frm) {
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
	},

	mark_as_seen(frm) {
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
	},
})

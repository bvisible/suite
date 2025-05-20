// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('JMAP Push Subscription', {
	refresh(frm) {
		frm.trigger('add_actions')
		frm.trigger('add_comments')
	},

	add_actions(frm) {
		if (frm.doc.__islocal || !frappe.user_roles.includes('System Manager')) return

		if (
			frm.doc.verified &&
			frm.doc.subscription_id &&
			['Active', 'Expired', 'Failed to Renew'].includes(frm.doc.status)
		) {
			frm.add_custom_button(
				__('Renew'),
				() => {
					frm.trigger('renew')
				},
				__('Actions'),
			)
		}

		if (
			[
				'Expired',
				'Failed to Verify',
				'Failed to Renew',
				'Failed to Subscribe',
				'Pending Verification',
			].includes(frm.doc.status)
		) {
			frm.add_custom_button(
				__('Resubscribe'),
				() => {
					frm.trigger('resubscribe')
				},
				__('Actions'),
			)
		}

		frm.add_custom_button(
			__('Destroy All Subscriptions'),
			() => {
				frappe.confirm(__('Are you sure you want to destroy all subscriptions?'), () =>
					frm.trigger('destroy_all_subscriptions'),
				)
			},
			__('Actions'),
		)
	},

	add_comments(frm) {
		if (frm.doc.endpoint && !frm.doc.endpoint.startsWith('https')) {
			frm.dashboard.add_comment(
				__("The endpoint must start with 'https://'."),
				'yellow',
				true,
			)
		}
	},

	renew(frm) {
		frappe.call({
			doc: frm.doc,
			method: 'renew',
			freeze: true,
			freeze_message: __('Renewing...'),
			callback: (r) => {
				if (!r.exc) {
					frm.refresh()
				}
			},
		})
	},

	resubscribe(frm) {
		frappe.call({
			doc: frm.doc,
			method: 'resubscribe',
			freeze: true,
			freeze_message: __('Resubscribing...'),
			callback: (r) => {
				if (!r.exc) {
					frm.refresh()
				}
			},
		})
	},

	destroy_all_subscriptions(frm) {
		frappe.call({
			doc: frm.doc,
			method: 'destroy_all_subscriptions',
			freeze: true,
			freeze_message: __('Destroying all subscriptions...'),
			callback: (r) => {
				if (!r.exc) {
					frm.refresh()
				}
			},
		})
	},
})

// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.listview_settings['Message Queue'] = {
	refresh: (listview) => {
		add_pause_resume_buttons(listview)
		add_bulk_retry_button_to_actions(listview)
	},
}

function add_pause_resume_buttons(listview) {
	if (!listview.filters) return

	const cluster_filter = listview.filters.find(
		(f) => f[0] === 'Message Queue' && f[1] === 'cluster' && f[2] === '=',
	)
	const cluster = cluster_filter ? cluster_filter[3] : null

	if (!cluster) return

	listview.page.add_inner_button('Pause', () => {
		pause_queue(listview, cluster)
	})
	listview.page.add_inner_button('Resume', () => {
		resume_queue(listview, cluster)
	})
}

function pause_queue(listview, cluster) {
	frappe.call({
		method: 'mail.mail.doctype.message_queue.message_queue.pause_queue',
		args: {
			cluster_name: cluster,
		},
		freeze: true,
		freeze_message: __('Pausing Queue...'),
		callback: (r) => {
			if (!r.exc) {
				listview.refresh()
			}
		},
	})
}

function resume_queue(listview, cluster) {
	frappe.call({
		method: 'mail.mail.doctype.message_queue.message_queue.resume_queue',
		args: {
			cluster_name: cluster,
		},
		freeze: true,
		freeze_message: __('Resuming Queue...'),
		callback: (r) => {
			if (!r.exc) {
				listview.refresh()
			}
		},
	})
}

function add_bulk_retry_button_to_actions(listview) {
	listview.page.add_actions_menu_item(__('Retry'), () => {
		frappe.call({
			method: 'mail.mail.doctype.message_queue.message_queue.bulk_retry_delivery',
			args: {
				names: listview.get_checked_items(true),
			},
			callback: (r) => {
				if (!r.exc) {
					listview.refresh()
				}
			},
		})
	})
}

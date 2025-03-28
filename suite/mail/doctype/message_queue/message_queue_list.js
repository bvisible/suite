// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.listview_settings['Message Queue'] = {
	refresh: (listview) => {
		add_bulk_retry_button_to_actions(listview)
	},
}

function add_bulk_retry_button_to_actions(list_view) {
	list_view.page.add_actions_menu_item(__('Retry'), () => {
		frappe.call({
			method: 'mail.mail.doctype.message_queue.message_queue.bulk_retry_delivery',
			args: {
				names: list_view.get_checked_items(true),
			},
			callback: (r) => {
				if (!r.exc) {
					list_view.refresh()
				}
			},
		})
	})
}

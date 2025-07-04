// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.listview_settings['Email Message'] = {
	onload: () => {
		frappe.route_options = {
			destroyed: 0,
		}
	},

	refresh: (listview) => {
		add_bulk_destroy_button_to_actions(listview)
	},
}

function add_bulk_destroy_button_to_actions(listview) {
	listview.page.add_actions_menu_item(__('Destroy'), () => {
		frappe.call({
			method: 'mail.mail.doctype.email_message.email_message.bulk_destroy',
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

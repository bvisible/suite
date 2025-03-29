// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.listview_settings['Mail Cluster'] = {
	refresh: (listview) => {
		add_reload_servers_config_button(listview)
	},
}

function add_reload_servers_config_button(listview) {
	listview.page.add_actions_menu_item(__('Reload Servers Configuration'), () => {
		frappe.call({
			method: 'mail.mail.doctype.mail_cluster.mail_cluster.reload_servers_config',
			args: {
				clusters: listview.get_checked_items(true),
			},
			freeze: true,
			freeze_message: __('Reloading Servers Configuration...'),
			callback: (r) => {
				if (!r.exc) {
					listview.refresh()
				}
			},
		})
	})
}

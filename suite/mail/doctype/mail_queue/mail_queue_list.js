// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.listview_settings['Mail Queue'] = {
	get_indicator: (doc) => {
		const status_colors = {
			Queued: 'blue',
			Pending: 'orange',
			Failed: 'red',
			Drafted: 'grey',
			'Failed to Draft': 'red',
			Submitted: 'green',
			'Failed to Submit': 'red',
		}
		return [__(doc.status), status_colors[doc.status] || 'darkgrey', 'status,=,' + doc.status]
	},
}

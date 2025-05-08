// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.listview_settings['Mail Queue'] = {
	get_indicator: (doc) => {
		const status_colors = {
			Draft: 'grey',
			'Failed to Draft': 'orange',
			Submitted: 'green',
			'Failed to Submit': 'orange',
			Failed: 'red',
		}
		return [__(doc.status), status_colors[doc.status], 'status,=,' + doc.status]
	},
}

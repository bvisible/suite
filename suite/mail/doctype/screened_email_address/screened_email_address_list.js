// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.listview_settings['Screened Email Address'] = {
	onload(listview) {
		if (!frappe.user.has_role('System Manager')) return

		// Changing global rules (rows without an account) deliberately rebuilds nothing, so an admin
		// batches their changes and then pushes them to every account's sieve script from here.
		listview.page.add_inner_button(__('Rebuild Automation Sieves'), () => {
			frappe.confirm(
				__(
					'Rebuild the automation sieve script for all accounts? This applies the global screened email addresses and runs in the background.'
				),
				() =>
					frappe.call(
						'suite.mail.doctype.sieve_script.sieve_script.rebuild_all_automation_sieves'
					)
			)
		})
	},
}

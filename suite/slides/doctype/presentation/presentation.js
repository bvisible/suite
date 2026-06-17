// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Presentation", {
	refresh: function (frm) {
		frm.add_custom_button("Optimize Images", function () {
			frappe.call({
				method: "slides.slides.doctype.presentation.presentation.optimize_images",
				args: {
					name: frm.doc.name,
				},
				callback: function (r) {
					if (r.message) {
						frappe.msgprint("Image optimization completed successfully.");
					}
				},
			});
		});
	},
});

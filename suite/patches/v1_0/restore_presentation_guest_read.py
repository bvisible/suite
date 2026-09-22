# //// Neoffice — added file (no upstream equivalent).
# ////
# //// REPAIRS A PATCH OF OURS THAT WAS WRONG.
# ////
# //// An earlier patch removed `Guest: read` from Presentation, reading it as
# //// an anonymous leak: the collection endpoint did list every presentation
# //// to a caller with no session at all. That much was true.
# ////
# //// What it missed is that the row is LOAD-BEARING. Frappe checks role
# //// permissions FIRST and only then calls the `has_permission` hook, so with
# //// no Guest row the hook never runs — and the hook is the whole gate:
# //// `presentation.has_permission` lets anyone read a TEMPLATE and sends
# //// everything else to Drive's sharing model. Remove the row and
# //// `get_public_presentation`, an `allow_guest` endpoint, can never return
# //// anything: sharing a deck by link stops working. Measured on the dev
# //// instance right after the bad patch ran — PermissionError, every time.
# ////
# //// So the anonymous surface is not "every presentation", it is "every
# //// TEMPLATE", by an explicit `is_template = 1` clause in the query
# //// conditions and `ptype == "read"` in the hook. That is a deliberate
# //// choice — a shared template library — and whether an anonymous visitor
# //// should see it is a product question, not a permission bug. It does not
# //// get answered by deleting a row that something else depends on.

import frappe


def execute():
	if not frappe.db.exists("DocType", "Presentation"):
		return
	if frappe.db.exists("Custom DocPerm", {"parent": "Presentation", "role": "Guest"}):
		return
	if not frappe.db.exists("Custom DocPerm", {"parent": "Presentation"}):
		#: No Custom rows at all: the doctype's own permissions are what frappe
		#: reads, and the JSON carries the Guest row again. Nothing to repair.
		return

	frappe.get_doc(
		{
			"doctype": "Custom DocPerm",
			"parent": "Presentation",
			"parenttype": "DocType",
			"parentfield": "permissions",
			"role": "Guest",
			"read": 1,
			"email": 1,
			"export": 1,
			"print": 1,
			"report": 1,
			"share": 1,
			"permlevel": 0,
		}
	).insert(ignore_permissions=True)
	frappe.clear_cache(doctype="Presentation")
	print("restore_presentation_guest_read: public sharing of a presentation works again")

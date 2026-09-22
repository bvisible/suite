# //// Neoffice — added file (no upstream equivalent).
# ////
# //// PRESENTATIONS WERE READABLE BY ANYONE, WITH NO ACCOUNT AT ALL.
# ////
# //// The doctype shipped `Guest: read`, and nothing gated it: there is no
# //// published/unpublished field on it, so the grant did not mean "the ones
# //// their owner shared", it meant all of them. Measured over plain HTTP on a
# //// dev instance, with no session and no cookie: the collection endpoint
# //// listed every presentation and the document endpoint returned one whole.
# ////
# //// Removing the row from the doctype JSON is NOT enough on a site that
# //// already exists. Once any `Custom DocPerm` exists for a doctype, those
# //// rows REPLACE the ones the code ships — frappe stops reading the JSON for
# //// that doctype entirely. So a fix that only edits the file would ship, look
# //// applied, and change nothing on every instance already running.

import frappe


def execute():
	if not frappe.db.exists("DocType", "Presentation"):
		return

	#: Only the anonymous grant. What a signed-in account may reach is a
	#: separate question with a separate answer, and a patch that quietly
	#: widened its own scope would be the harder thing to review.
	rows = frappe.get_all(
		"Custom DocPerm", filters={"parent": "Presentation", "role": "Guest"}, pluck="name"
	)
	if rows:
		frappe.db.delete("Custom DocPerm", {"name": ("in", rows)})
		print(f"presentations_are_not_public: removed {len(rows)} anonymous grant(s)")

	#: And the DocPerm the code used to ship, on a site that never grew Custom
	#: rows — there the JSON is still what frappe reads, but the row already
	#: synced into `tabDocPerm` and a doctype sync does not delete it.
	shipped = frappe.get_all("DocPerm", filters={"parent": "Presentation", "role": "Guest"}, pluck="name")
	if shipped:
		frappe.db.delete("DocPerm", {"name": ("in", shipped)})
		print(f"presentations_are_not_public: removed {len(shipped)} shipped anonymous grant(s)")

	if rows or shipped:
		frappe.clear_cache(doctype="Presentation")

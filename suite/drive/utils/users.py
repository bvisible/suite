from __future__ import annotations
import os

import frappe
import requests
from frappe.rate_limiter import rate_limit
from frappe.utils import now


def mark_as_viewed(entity):
	if (
		frappe.session.user == "Guest"
		or not frappe.has_permission(doctype="Drive Entity Log", ptype="create", user=frappe.session.user)
		or entity.is_folder
	):
		return

	entity_log = frappe.db.get_value(
		"Drive Entity Log", {"entity_name": entity.name, "user": frappe.session.user}
	)
	if entity_log:
		frappe.db.set_value(
			"Drive Entity Log",
			entity_log,
			"last_interaction",
			now(),
			update_modified=False,
		)
		return
	doc = frappe.new_doc("Drive Entity Log")
	doc.entity_name = entity.name
	doc.user = frappe.session.user
	doc.last_interaction = now()
	doc.insert()
	return doc


def generate_otp():
	"""Generates a cryptographically secure random OTP"""

	return int.from_bytes(os.urandom(5), byteorder="big") % 900000 + 100000


def get_country_info():
	ip = frappe.local.request_ip

	def _get_country_info():
		fields = [
			"status",
			"message",
			"continent",
			"continentCode",
			"country",
			"countryCode",
			"region",
			"regionName",
			"city",
			"district",
			"zip",
			"lat",
			"lon",
			"timezone",
			"offset",
			"currency",
			"isp",
			"org",
			"as",
			"asname",
			"reverse",
			"mobile",
			"proxy",
			"hosting",
			"query",
		]

		try:
			res = requests.get(f"https://pro.ip-api.com/json/{ip}?fields={','.join(fields)}")
			data = res.json()
			if data.get("status") != "fail":
				return data
		except Exception:
			pass

		return {}

	return frappe.cache().hget("ip_country_map", ip, generator=_get_country_info)


def assign_drive_role(user, method: str | None = None) -> None:
	"""Assign the "Drive User" role to a new User.

	Runs on `before_insert` (not `after_insert`) so the role is present by the
	time Frappe's `User.validate` runs: `check_roles_added` would otherwise warn
	"Newly created user X has no roles enabled", and `set_system_user` would
	demote the user to a Website User for having no desk-access role.

	#//// Neoffice — `desk_access=False`. The Role default is 1, and a desk-access
	#//// role re-promotes a frontend signup to System User. Upstream calls
	#//// assign_role() without this argument; keep it through the next merge.
	"""
	from suite.suite_core.roles import assign_role

	assign_role(user, "Drive User", desk_access=False)


def create_drive_settings_and_team(user, method: str | None = None) -> None:
	"""Create Drive Settings and a personal team for a newly created User."""
	from suite.drive.api.product import create_team

	user_name = user.name

	if not user_name or user_name in ("Guest", "Administrator"):
		return

	frappe.get_doc({"doctype": "Drive Settings", "user": user.email}).insert(ignore_permissions=True)

	# Created as the new user so the team is owned by and shared with them.
	# Snapshot the full session state: frappe.set_user() overwrites session.sid with the
	# username and wipes session.data, so restoring only the user would leave the original
	# session corrupted (logging the acting user out on the next request).
	original_user = frappe.session.user
	original_sid = frappe.session.sid
	original_data = frappe.session.data
	try:
		frappe.set_user(user_name)
		create_team(user=user_name, team_name=user_name, personal=1)
	# //// Neoffice — creating the personal Drive team must never abort the
	# //// creation of the USER. create_team() inserts a Drive Team as the new
	# //// user, which only "Drive User" and "System Manager" may do — and the
	# //// role granted a few lines above does not always survive: a User with a
	# //// role_profile_name has its roles REPLACED by the profile's on validate
	# //// (populate_role_profile_roles), so the role is gone by then. The
	# //// PermissionError climbed out of after_insert and no user was created
	# //// at all (measured 28.08.2026: profile "Caissier" -> PermissionError,
	# //// no profile -> fine). Drive is an annex; the account is not.
	except Exception:
		frappe.log_error(
			f"Drive: personal team not created for {user_name}",
			frappe.get_traceback(),
		)
	finally:
		frappe.set_user(original_user)
		frappe.session.sid = original_sid
		frappe.session.data = original_data


# //// Neoffice — added function (no upstream equivalent).
# on_trash(User) → drop the Drive Settings this app's after_insert created.
#
# Upstream provisions Drive Settings for every new user but never removes it, and
# the doctype autonames `field:user` — so the row's primary key IS the e-mail.
# Deleting a User therefore leaves a row that makes re-creating an account with
# the SAME address die on `DuplicateEntryError: Drive Settings`, from anywhere:
# the desk, a signup, or the fiduciary portal re-inviting a colleague who was
# removed. Mail already cleans up after itself in on_trash; Drive did not.
#
# Deliberately NOT deleting the personal Drive Team: it autonames by hash, so it
# blocks nothing, and it holds the user's files — that is data, and reaping it
# behind a user deletion is not this hook's call.
def delete_drive_settings(doc, method: str | None = None) -> None:
	"""Remove the deleted user's Drive Settings so the address can be reused."""
	if frappe.db.exists("Drive Settings", doc.name):
		frappe.delete_doc("Drive Settings", doc.name, force=1, ignore_permissions=True)

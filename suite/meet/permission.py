import frappe


def _is_administrator(user: str) -> bool:
	return user == "Administrator"


def _get_meeting_user_ids(doc) -> set[str]:
	user_ids = {doc.owner}

	for fieldname in ("members", "co_hosts"):
		for row in doc.get(fieldname) or []:
			if row.user:
				user_ids.add(row.user)

	return user_ids


def has_app_permission() -> bool:
	if _is_administrator(frappe.session.user):
		return True

	roles = frappe.get_roles()
	meet_roles = ["Meet User"]
	if any(role in roles for role in meet_roles):
		return True

	return False


def get_meeting_permission_query_conditions(user: str | None = None) -> str:
	user = user or frappe.session.user

	if _is_administrator(user):
		return ""

	if user == "Guest":
		return "1=0"

	escaped_user = frappe.db.escape(user)

	return f"""
		(
			`tabSae Meeting`.`owner` = {escaped_user}
			or exists(
				select 1
				from `tabSae Meeting User` as `meeting_user`
				where `meeting_user`.`parent` = `tabSae Meeting`.`name`
				and `meeting_user`.`parenttype` = 'Sae Meeting'
				and `meeting_user`.`user` = {escaped_user}
			)
		)
	"""


def has_meeting_permission(doc, ptype: str = "read", user: str | None = None) -> bool:
	user = user or frappe.session.user

	if _is_administrator(user):
		return True

	if user == "Guest":
		return False

	if ptype == "create":
		return has_app_permission()

	meeting_user_ids = _get_meeting_user_ids(doc)

	if ptype in {"read", "print", "email", "export", "share"}:
		return user in meeting_user_ids

	if ptype == "write":
		return user == doc.owner or any(row.user == user for row in doc.get("co_hosts") or [])

	if ptype == "delete":
		return user == doc.owner

	return False

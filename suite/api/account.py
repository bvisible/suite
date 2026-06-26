import frappe


@frappe.whitelist()
def is_setup_complete() -> bool:
	return bool(frappe.is_setup_complete())


@frappe.whitelist()
def mark_setup_complete() -> None:
	frappe.only_for("System Manager")

	from frappe.desk.page.setup_wizard.setup_wizard import enable_setup_wizard_complete

	enable_setup_wizard_complete("frappe")
	enable_setup_wizard_complete("suite")
	frappe.db.set_single_value("System Settings", "setup_complete", 1)


@frappe.whitelist()
def get_workspace() -> dict[str, str]:
	return {
		"workspace_name": frappe.db.get_single_value("Suite Settings", "workspace_name") or "",
		"workspace_logo": frappe.db.get_single_value("Suite Settings", "workspace_logo") or "",
	}


@frappe.whitelist(methods=["POST"])
def update_workspace(workspace_name: str, workspace_logo: str = "") -> None:
	frappe.only_for("System Manager")

	settings = frappe.get_single("Suite Settings")
	settings.workspace_name = workspace_name
	settings.workspace_logo = workspace_logo
	settings.save()


@frappe.whitelist(methods=["POST"])
def invite_users(emails: str) -> dict[str, list[str]]:
	from frappe.core.api.user_invitation import invite_by_email

	return invite_by_email(
		emails=emails,
		roles=get_invite_roles(),
		redirect_to_path="/suite",
		app_name="suite",
	)


def get_invite_roles() -> list[str]:
	hook = frappe.get_hooks("user_invitation", app_name="suite")
	allowed_roles = (hook if isinstance(hook, dict) else {}).get("allowed_roles") or {}
	user_roles = set(frappe.get_roles())
	roles: set[str] = set()
	for role, granted in allowed_roles.items():
		if role in user_roles:
			roles.update(granted)
	return list(roles)


@frappe.whitelist()
def get_logged_in_user() -> dict | None:
	user = frappe.session.user
	if user == "Guest":
		return None

	user_doc = frappe.get_doc("User", user)
	return {
		"name": user_doc.name,
		"email": user_doc.email,
		"full_name": user_doc.full_name,
		"avatar": user_doc.user_image,
		"roles": [role.role for role in user_doc.roles],
	}

from drive.api.permissions import get_teams
import frappe


def filter_templates(user):
    if user == "Administrator":
        return ""
    teams = get_teams()
    teams = ", ".join(frappe.db.escape(team) for team in teams)
    return f"""(`owner` == "{user}" or team in ({teams}))"""

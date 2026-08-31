# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt


from __future__ import annotations
import re

import frappe
from frappe.core.doctype.user.user import User
from frappe.utils.caching import redis_cache


def unique_users(user_list: list) -> list[dict]:
	"""Return unique child table rows, preserving order and metadata."""
	seen = set()
	unique_list = []

	for user in user_list or []:
		if isinstance(user, str):
			user_id = user
			user_row = {"user": user_id}
		else:
			user_id = user.get("user") if hasattr(user, "get") else getattr(user, "user", None)
			if not user_id:
				continue
			user_row = dict(user) if isinstance(user, dict) else user.as_dict()

		if user_id in seen:
			continue

		seen.add(user_id)
		unique_list.append(user_row)

	return unique_list


def assign_meet_role(user: User, method: str | None = None) -> None:
	"""Assign the "Meet User" role to a new User.

	Runs on `before_insert`, like its Drive counterpart: the role belongs to the
	document Frappe is about to validate, and no second `User.save` is needed.

	#//// Neoffice — `desk_access=False`. The Role default is 1, and a desk-access
	#//// role re-promotes a frontend signup to System User. Upstream calls
	#//// assign_role() without this argument; keep it through the next merge.
	"""
	from suite.suite_core.roles import assign_role

	assign_role(user, "Meet User", desk_access=False)


def is_guest_user(user_id: str) -> bool:
	"""Check if a user ID is a guest identifier."""
	return user_id.startswith("guest_")


@redis_cache(ttl=5 * 60)
def get_user_info(user_id: str) -> dict | None:
	"""
	Get user information for both authenticated users and guests.

	Returns dict with full_name, user_image, and is_guest flag.
	Returns None if user not found or guest session expired.
	"""
	if not user_id:
		return None

	if is_guest_user(user_id):
		guest_session = get_guest_session(user_id)
		if not guest_session:
			return None

		return {
			"full_name": guest_session.get("guest_name"),
			"is_guest": True,
		}

	user_info = frappe.db.get_value("User", user_id, ["full_name", "user_image"], as_dict=True)

	if not user_info:
		return None

	return {
		"full_name": user_info.get("full_name") or user_id,
		"user_image": user_info.get("user_image"),
		"is_guest": False,
	}


def get_guest_session(guest_id: str) -> dict | None:
	"""Retrieve guest session data from cache."""
	cache_key = f"guest_session:{guest_id}"
	session_data = frappe.cache.get_value(cache_key)

	if not session_data:
		return None

	if isinstance(session_data, dict):
		return session_data

	return None


def set_guest_session(guest_id: str, session_data: dict, ttl: int = 86400) -> None:
	"""Store guest session data (default 24 hours)."""
	cache_key = f"guest_session:{guest_id}"
	frappe.cache.set_value(cache_key, session_data, expires_in_sec=ttl)


def validate_guest_name(guest_name: str) -> tuple[bool, str | None]:
	"""
	Validate guest name.

	Returns (is_valid, error_message).
	"""
	if not guest_name or not guest_name.strip():
		return False, "Guest name is required"

	guest_name = guest_name.strip()

	if len(guest_name) < 2:
		return False, "Guest name must be at least 2 characters"

	if len(guest_name) > 50:
		return False, "Guest name must be at most 50 characters"

	if not re.match(r"^[a-zA-Z0-9\s'\-]+$", guest_name):
		return False, "Guest name contains invalid characters"

	return True, None

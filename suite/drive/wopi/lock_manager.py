# //// Neoffice: new file — Collabora/WOPI port (from drive_wopi), maintained by Neoffice ////
"""
WOPI lock management to prevent editing conflicts.
Uses Redis cache for distributed locking.
"""

from __future__ import annotations
import frappe
from datetime import datetime


LOCK_EXPIRY_SECONDS = 1800  # 30 minutes


def get_lock_key(file_id: str) -> str:
    """Generate Redis key for file lock."""
    return f"wopi_lock:{file_id}"


def get_lock(file_id: str) -> dict | None:
    """
    Get current lock for a file.

    Returns:
        dict with 'lock_id' and 'user' or None if no lock
    """
    lock_data = frappe.cache().get_value(get_lock_key(file_id))
    return lock_data


def acquire_lock(file_id: str, lock_id: str, user: str) -> dict:
    """
    Attempt to acquire a lock on a file.

    Returns:
        dict with 'success', 'status', and optionally 'current_lock'
    """
    current_lock = get_lock(file_id)

    if current_lock and current_lock.get("lock_id") != lock_id:
        return {
            "success": False,
            "status": 409,
            "current_lock": current_lock.get("lock_id"),
        }

    lock_data = {
        "lock_id": lock_id,
        "user": user,
        "created_at": datetime.utcnow().isoformat(),
    }

    # Note: Frappe cache doesn't support expires_in_sec, lock will persist until cleared
    frappe.cache().set_value(get_lock_key(file_id), lock_data)

    return {"success": True, "status": 200}


def refresh_lock(file_id: str, lock_id: str) -> dict:
    """
    Refresh an existing lock to extend its expiration.
    """
    current_lock = get_lock(file_id)

    if not current_lock:
        return {"success": False, "status": 409, "current_lock": ""}

    if current_lock.get("lock_id") != lock_id:
        return {
            "success": False,
            "status": 409,
            "current_lock": current_lock.get("lock_id"),
        }

    # Reset lock (Note: Frappe cache doesn't support expires_in_sec)
    frappe.cache().set_value(get_lock_key(file_id), current_lock)

    return {"success": True, "status": 200}


def release_lock(file_id: str, lock_id: str) -> dict:
    """
    Release a lock.
    """
    current_lock = get_lock(file_id)

    if current_lock and current_lock.get("lock_id") != lock_id:
        return {
            "success": False,
            "status": 409,
            "current_lock": current_lock.get("lock_id"),
        }

    frappe.cache().delete_value(get_lock_key(file_id))

    return {"success": True, "status": 200}


def unlock_expired(file_id: str, lock_id: str, new_lock_id: str, user: str) -> dict:
    """
    Unlock and relock operation (UNLOCK_AND_RELOCK).
    Used when Collabora needs to change the lock ID.
    """
    current_lock = get_lock(file_id)

    if current_lock and current_lock.get("lock_id") != lock_id:
        return {
            "success": False,
            "status": 409,
            "current_lock": current_lock.get("lock_id"),
        }

    # Set new lock (Note: Frappe cache doesn't support expires_in_sec)
    lock_data = {
        "lock_id": new_lock_id,
        "user": user,
        "created_at": datetime.utcnow().isoformat(),
    }

    frappe.cache().set_value(get_lock_key(file_id), lock_data)

    return {"success": True, "status": 200}

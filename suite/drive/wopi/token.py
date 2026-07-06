# //// Neoffice: new file — Collabora/WOPI port (from drive_wopi), maintained by Neoffice ////
"""
JWT token management for WOPI authentication.
"""
from __future__ import annotations
import jwt
import frappe
from frappe import _
from datetime import datetime, timedelta


def get_wopi_settings():
    """Get WOPI settings from DocType."""
    try:
        settings = frappe.get_single("WOPI Settings")
        return {
            "enabled": settings.enabled,
            "collabora_server_url": settings.collabora_server_url,
            "jwt_secret": settings.get_password("jwt_secret") if settings.jwt_secret else None,
            "jwt_expiry_hours": settings.jwt_expiry_hours or 10,
        }
    except Exception:
        return {
            "enabled": False,
            "collabora_server_url": None,
            "jwt_secret": None,
            "jwt_expiry_hours": 10,
        }


def get_wopi_secret() -> str:
    """Get JWT secret from WOPI Settings."""
    settings = get_wopi_settings()
    secret = settings.get("jwt_secret")
    if not secret:
        secret = frappe.generate_hash(length=32)
        frappe.log_error(
            "WOPI JWT Secret Missing",
            "JWT secret not configured in WOPI Settings. Using generated secret."
        )
    return secret


def generate_wopi_token(file_id: str, user: str = None, can_write: bool = True) -> dict:
    """
    Generate a JWT token for WOPI access.

    Args:
        file_id: File ID
        user: User email (defaults to current user)
        can_write: Write permission flag

    Returns:
        dict with 'access_token' and 'access_token_ttl' (in milliseconds)
    """
    if user is None:
        user = frappe.session.user

    settings = get_wopi_settings()
    expiry_hours = settings.get("jwt_expiry_hours", 10)
    expiry = datetime.utcnow() + timedelta(hours=expiry_hours)

    payload = {
        "file_id": file_id,
        "user_id": user,
        "can_write": can_write,
        "exp": expiry,
        "iat": datetime.utcnow(),
    }

    token = jwt.encode(payload, get_wopi_secret(), algorithm="HS256")
    # WOPI spec: access_token_ttl is Unix timestamp in milliseconds when token expires
    ttl = int(expiry.timestamp() * 1000)

    return {
        "access_token": token,
        "access_token_ttl": ttl,
    }


def validate_wopi_token(token: str) -> dict:
    """
    Validate a WOPI JWT token.

    Args:
        token: JWT token to validate

    Returns:
        Decoded payload

    Raises:
        frappe.AuthenticationError if invalid
    """
    try:
        payload = jwt.decode(token, get_wopi_secret(), algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        frappe.throw(_("WOPI token expired"), frappe.AuthenticationError)
    except jwt.InvalidTokenError as e:
        frappe.throw(_("Invalid WOPI token: {0}").format(str(e)), frappe.AuthenticationError)

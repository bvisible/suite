# //// Neoffice: new file — Collabora/WOPI port (from drive_wopi), maintained by Neoffice ////
"""
JWT token management for WOPI authentication.
"""
from __future__ import annotations
import jwt
import frappe
from frappe import _
from datetime import datetime, timedelta


def _read_jwt_secret(settings) -> str | None:
    """Read the signing secret, re-minting it if this site cannot decrypt it.

    Encrypted fields are sealed with the site's own encryption key, so a site
    restored from another site's backup inherits a secret it can never read:
    get_password() raises "Encryption key is invalid".

    That is recoverable here, unlike most secrets. This one is not shared with
    anybody — it only signs the WOPI tokens this site hands to its own
    Collabora — so minting a fresh one costs nothing beyond invalidating tokens
    issued in the last few hours, and it is written back so every later call
    agrees on the same value.

    Worth being explicit about why this matters: the old code wrapped the whole
    settings read in a bare `except` that returned enabled=False. A file that
    could not be decrypted therefore surfaced as "WOPI/Collabora is disabled",
    and Drive quietly fell back to the Microsoft Office viewer — sending
    customer documents to a third party because of an unreadable local secret.
    Measured on the Neoffice Lite tenants, 2026-08-04.
    """
    if not settings.jwt_secret:
        return None
    try:
        return settings.get_password("jwt_secret")
    except Exception:
        secret = frappe.generate_hash(length=32)
        try:
            settings.db_set("jwt_secret", secret)
            frappe.db.commit()
            frappe.log_error(
                "WOPI: JWT secret re-minted",
                "The stored WOPI JWT secret could not be decrypted with this site's encryption "
                "key (usual cause: the site was restored from another site's backup). A new "
                "secret was generated and saved so Collabora keeps working.",
            )
        except Exception:
            # Read-only transaction (a GET request) — use the value in memory and
            # let a later write persist it, rather than falling back to Microsoft.
            pass
        return secret


def get_wopi_settings():
    """Get WOPI settings from DocType."""
    try:
        settings = frappe.get_single("WOPI Settings")
    except Exception:
        # No WOPI Settings at all (doctype not installed): genuinely off.
        return {
            "enabled": False,
            "collabora_server_url": None,
            "jwt_secret": None,
            "jwt_expiry_hours": 10,
        }

    return {
        "enabled": settings.enabled,
        "collabora_server_url": settings.collabora_server_url,
        "jwt_secret": _read_jwt_secret(settings),
        "jwt_expiry_hours": settings.jwt_expiry_hours or 10,
    }


def get_wopi_secret() -> str:
    """Get JWT secret from WOPI Settings."""
    settings = get_wopi_settings()
    secret = settings.get("jwt_secret")
    if not secret:
        # Persist it. A secret generated per call differs on every call, so a
        # token signed by one request could never be verified by the next.
        secret = frappe.generate_hash(length=32)
        try:
            doc = frappe.get_single("WOPI Settings")
            doc.db_set("jwt_secret", secret)
            frappe.db.commit()
        except Exception:
            pass
        frappe.log_error(
            "WOPI JWT Secret Missing",
            "No JWT secret was configured in WOPI Settings; one was generated and saved.",
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

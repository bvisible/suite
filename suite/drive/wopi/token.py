# //// Neoffice: new file — Collabora/WOPI port (from drive_wopi), maintained by Neoffice ////
"""
JWT token management for WOPI authentication.
"""
from __future__ import annotations
import jwt
import frappe
from frappe import _
# //// Neoffice — `timezone` for the aware expiry below; the rest of this block
# //// (the default lifetime, and the helper that refuses to hand out a secret it
# //// could not persist) is new. See the commit and the notes on each.
from datetime import datetime, timedelta, timezone

# Lifetime of a WOPI access token, in hours, when WOPI Settings says nothing.
#
# `access_token_ttl` is an absolute expiry instant in milliseconds since the
# epoch, not a duration (Microsoft's WOPI spec, which Collabora implements). The
# spec suggests 10 hours; Collabora warns the user 15 minutes before expiry and
# refuses to save afterwards, and reloading the document mints a fresh token.
#
# We ship 4 hours instead. The token freezes `file_id` and `can_write` at the
# moment the editor opened, so its lifetime is the window in which a leaked or
# stale token still works. Four hours covers an editing session end to end while
# more than halving that window; the endpoints re-check the live permission on
# every read and write anyway (see endpoints.py), so the TTL is a session knob,
# not the authorisation boundary. Raise `jwt_expiry_hours` in WOPI Settings on an
# instance where people genuinely keep one document open all day.
DEFAULT_JWT_EXPIRY_HOURS = 4


def _persist_jwt_secret(settings, secret: str) -> bool:
    """Write the signing secret back to WOPI Settings. True if it landed.

    A GET request runs in a read-only transaction, so this can legitimately
    fail; the caller must then NOT hand out the value, because nothing else
    would ever agree on it.
    """
    try:
        settings.db_set("jwt_secret", secret)
        frappe.db.commit()
        return True
    except Exception:
        return False


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
        # //// Neoffice — a re-minted secret is only usable if it was WRITTEN. The
        # //// previous version swallowed the failure and returned the in-memory value
        # //// anyway, so a read-only request handed out a secret nobody else would
        # //// ever see: the token it signed could not be verified by the next request
        # //// and Collabora answered "Invalid WOPI token". Returning None instead
        # //// makes get_wopi_secret() say what is actually wrong.
        if not _persist_jwt_secret(settings, secret):
            # //// Neoffice — say what is wrong instead of returning a private value.
            frappe.log_error(
                "WOPI: JWT secret unreadable and not re-mintable",
                # //// Neoffice — new message: the READ failed and so did the write.
                "The stored WOPI JWT secret could not be decrypted with this site's encryption "
                "key, and this request could not write a replacement (read-only transaction). "
                "Run `bench --site <site> migrate` to provision one.",
            )
            return None
        # //// Neoffice — reached only when the write above actually landed.
        frappe.log_error(
            "WOPI: JWT secret re-minted",
            "The stored WOPI JWT secret could not be decrypted with this site's encryption "
            "key (usual cause: the site was restored from another site's backup). A new "
            "secret was generated and saved so Collabora keeps working.",
        )
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
            # //// Neoffice — see DEFAULT_JWT_EXPIRY_HOURS above (was a bare 10).
            "jwt_expiry_hours": DEFAULT_JWT_EXPIRY_HOURS,
        }

    return {
        "enabled": settings.enabled,
        "collabora_server_url": settings.collabora_server_url,
        "jwt_secret": _read_jwt_secret(settings),
        # //// Neoffice — see DEFAULT_JWT_EXPIRY_HOURS above (was a bare 10).
        "jwt_expiry_hours": settings.jwt_expiry_hours or DEFAULT_JWT_EXPIRY_HOURS,
    }


# //// Neoffice — this function no longer invents a secret. It used to generate one
# //// per call and try to save it inside `except Exception: pass`; on a read-only
# //// request (every WOPI GET) the write failed silently and each call returned a
# //// DIFFERENT random secret, so a token signed by one request could never be
# //// verified by the next — the "Invalid WOPI token" nobody could reproduce. The
# //// secret has exactly one source of truth now: WOPI Settings, provisioned once by
# //// suite.suite_core.neoffice.ensure_wopi_secret() at install and at every migrate.
def get_wopi_secret() -> str:
    """Return the JWT signing secret from WOPI Settings, or say why it is missing."""
    settings = get_wopi_settings()
    secret = settings.get("jwt_secret")
    if not secret:
        # //// Neoffice — was: mint a random one and try to save it. See above.
        frappe.throw(
            _(
                "The WOPI signing secret is missing from WOPI Settings. "
                "Run a site migration to provision it, or set the JWT Secret manually."
            ),
            frappe.ValidationError,
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
    expiry_hours = settings.get("jwt_expiry_hours", DEFAULT_JWT_EXPIRY_HOURS)
    # //// Neoffice — datetime.utcnow() returns a NAIVE datetime. PyJWT read it as UTC
    # //// for `exp`, but `expiry.timestamp()` below reads a naive value as LOCAL time:
    # //// on a UTC+2 server the access_token_ttl we handed Collabora was two hours
    # //// EARLIER than the moment the token really expired, so Collabora warned about
    # //// and then refused a session that was still perfectly valid. The two now agree.
    # //// utcnow() is also deprecated since Python 3.12.
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(hours=expiry_hours)

    payload = {
        "file_id": file_id,
        "user_id": user,
        "can_write": can_write,
        "exp": expiry,
        # //// Neoffice — the same aware instant as `expiry`, so the two agree.
        "iat": now,
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

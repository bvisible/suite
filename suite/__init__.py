from __future__ import annotations
__version__ = "0.0.1"

# ---- Neoffice: Python 3.12 compatibility -----------------------------------
# uuid.uuid7() landed in Python 3.14 (RFC 9562) and suite imports it as
# `from uuid import uuid7`. The Neoffice fleet runs Frappe v15 on Python 3.12,
# so graft a spec-compliant fallback onto the stdlib module here: this package
# __init__ always runs before any suite.* submodule resolves that import.
# Drop this block when the fleet moves to Python >= 3.14.
import secrets as _secrets
import time as _time
import uuid as _uuid

if not hasattr(_uuid, "uuid7"):

	def _uuid7() -> _uuid.UUID:
		# Layout per RFC 9562: 48-bit unix-ms timestamp | ver(7) | 12 rand bits
		# | variant(0b10) | 62 rand bits.
		ts_ms = _time.time_ns() // 1_000_000
		value = (ts_ms & 0xFFFFFFFFFFFF) << 80
		value |= 0x7 << 76
		value |= _secrets.randbits(12) << 64
		value |= 0b10 << 62
		value |= _secrets.randbits(62)
		return _uuid.UUID(int=value)

	_uuid.uuid7 = _uuid7
# -----------------------------------------------------------------------------

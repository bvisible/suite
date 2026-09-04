#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
__version__ = "0.0.1"

# //// Neoffice: Python 3.12 compatibility ////
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
# //// end Neoffice ////


# //// Neoffice: Frappe v15 compatibility ////
# suite targets Frappe v16 (the develop branch); the fleet runs v15. Two v16-only
# APIs are imported by code that runs in production, so they are grafted here —
# this package __init__ always runs before any suite.* submodule resolves them.
# Everything else v16-only in this app is either guarded by the caller
# (suite_core.setup catches the ImportError) or confined to the test suite
# (frappe.tests.IntegrationTestCase / UnitTestCase, ~90 files, which simply do
# not run on v15). Drop this whole block when the fleet moves to Frappe v16.
import sys as _sys
import types as _types


def _graft_deprecation_dumpster() -> None:
	"""`frappe.deprecation_dumpster` landed in v16; suite.store.search_store imports it
	at module level, so its absence takes the module down at import time — and with it
	every search in Mail. The real one routes through Frappe's deprecation machinery;
	all we owe the caller is a warning that does not raise."""
	if "frappe.deprecation_dumpster" in _sys.modules:
		return
	import warnings as _warnings

	module = _types.ModuleType("frappe.deprecation_dumpster")

	def deprecation_warning(marked: str = "", graduation: str = "", msg: str = "", **kwargs) -> None:
		_warnings.warn(
			f"[deprecated since {marked}, removed in {graduation}] {msg}",
			DeprecationWarning,
			stacklevel=2,
		)

	module.deprecation_warning = deprecation_warning
	_sys.modules["frappe.deprecation_dumpster"] = module


def _graft_get_safe_file_name() -> None:
	"""`frappe.core.doctype.file.utils.get_safe_file_name` landed in v16; suite.mail.api.mail
	imports it inside upload_file() to build the temp path of an upload. Without it, every
	attachment upload raises ImportError. It guards a path built from a client-supplied
	name, so the fallback stays strict: basename only, and nothing outside a safe alphabet."""
	try:
		from frappe.core.doctype.file import utils as _file_utils
	except Exception:
		return
	if hasattr(_file_utils, "get_safe_file_name"):
		return

	import os as _os
	import re as _re

	def get_safe_file_name(filename: str) -> str:
		# Take the basename under both separators: a Windows client sends backslashes,
		# and os.path.basename ignores those on POSIX.
		name = _os.path.basename(str(filename or "").replace("\\", "/").split("/")[-1])
		name = _re.sub(r"[^A-Za-z0-9._-]", "_", name).lstrip(".")
		return name or "file"

	_file_utils.get_safe_file_name = get_safe_file_name


_graft_deprecation_dumpster()
_graft_get_safe_file_name()
# //// end Neoffice ////

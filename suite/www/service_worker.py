# frappe caches rendered www pages in redis for 30 minutes; a deploy must ship
# the new worker at once
# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations

no_cache = 1

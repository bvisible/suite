# frappe caches rendered www pages in redis for 30 minutes; a deploy must ship
# the new worker at once
from __future__ import annotations
no_cache = 1

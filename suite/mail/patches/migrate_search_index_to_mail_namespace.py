# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from suite.mail.patches.migrate_cache_to_mail_namespace import _migrate_base
from suite.store import get_search_base_path


def execute() -> None:
    """Relocate pre-namespace search indexes into the ``mail`` namespace.

    Search indexes were namespaced after the data/blob stores, so the earlier
    ``migrate_cache_to_mail_namespace`` patch (which had already run) never touched them. Each
    account's index lived directly at ``<search-base>/<account>/<entity>`` and now lives at
    ``<search-base>/mail/<account>/<entity>``. As with the other stores the leaf directory name is
    unchanged, so migrating is just moving every top-level account directory under a ``mail/``
    subdirectory — the same move `_migrate_base` performs for the data and blob bases.

    Best-effort: indexes rebuild lazily from cached data, so anything already migrated (or any
    stray file) is left as-is.
    """

    _migrate_base(get_search_base_path())

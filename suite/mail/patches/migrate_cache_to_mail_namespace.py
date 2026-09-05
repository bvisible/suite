# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import os
import shutil

from suite.mail.store import MAIL_NAMESPACE
from suite.store import get_blob_base_path, get_data_base_path


def execute() -> None:
    """Relocate pre-namespace cache directories into the ``mail`` namespace.

    Before stores were namespaced, each JMAP account's data/blob cache lived directly at
    ``<base>/<account>``; it now lives at ``<base>/mail/<account>``. The leaf directory name is
    unchanged, so migrating is just moving every existing top-level account directory under a
    ``mail/`` subdirectory. Both bases were used only by mail before this change, so every
    top-level directory is a mail account cache.

    Best-effort: caches rebuild lazily from JMAP, so anything already migrated (or any stray
    file such as an interrupted blob-store temp file) is left as-is.
    """

    for base_path in (get_data_base_path(), get_blob_base_path()):
        _migrate_base(base_path)


def _migrate_base(base_path: str) -> None:
    """Move each top-level account directory in `base_path` into its ``mail`` subdirectory."""

    if not os.path.isdir(base_path):
        return

    target = os.path.join(base_path, MAIL_NAMESPACE)

    # Snapshot the listing first: the moves add entries to `base_path`, which must not perturb
    # the iteration.
    for name in os.listdir(base_path):
        if name == MAIL_NAMESPACE:
            continue

        source = os.path.join(base_path, name)

        # Only per-account directories move; leave stray files and symlinks untouched.
        if os.path.islink(source) or not os.path.isdir(source):
            continue

        os.makedirs(target, exist_ok=True)
        destination = os.path.join(target, name)

        # Already migrated for this account: the namespaced copy is authoritative, so drop the
        # stale pre-namespace directory rather than overwrite it.
        if os.path.exists(destination):
            shutil.rmtree(source, ignore_errors=True)
            continue

        os.rename(source, destination)

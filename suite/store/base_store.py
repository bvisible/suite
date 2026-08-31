from __future__ import annotations
import os
from collections.abc import Sequence
from threading import RLock
from typing import Any, ClassVar
from urllib.parse import quote

import frappe
from frappe.utils import random_string

# A namespace is a relative path (one or more segments) that scopes a store to its own
# directory under the base path, e.g. ``("mail", account)`` -> ``<base>/mail/<account>``.
Namespace = str | Sequence[str]


def normalize_namespace(namespace: Namespace) -> tuple[str, ...]:
    """Validate a namespace and return it as a tuple of segments.

    Accepts either a ``"a/b"`` string (split on ``/``) or a sequence of segments. Rejects an
    empty namespace and any empty, ``.`` or ``..`` segment, so a namespace can never escape the
    base path once its segments are joined.
    """

    segments = namespace.split("/") if isinstance(namespace, str) else list(namespace)

    if not segments:
        raise ValueError("namespace must have at least one segment")

    for segment in segments:
        if not segment or segment in (".", ".."):
            raise ValueError(f"invalid namespace segment: {segment!r}")

    return tuple(segments)


def resolve_namespace_path(base_path: str, namespace: Namespace) -> str:
    """Return the on-disk directory for a namespace under `base_path`.

    Each segment is percent-encoded so it is a single, filesystem-safe path component (a
    segment containing ``/`` cannot spill into extra directories).
    """

    segments = normalize_namespace(namespace)
    return os.path.join(base_path, *(quote(segment, safe="") for segment in segments))


class _StorageLogger:
    """Structured logger for the stores.

    Each level takes an event name plus optional fields (and tolerates a pre-built dict as the
    event) and emits one record per event to the ``suite.store`` frappe logger.
    """

    def __init__(self, ctx: dict) -> None:
        self.ctx = ctx
        self.logger = frappe.logger("suite.store", allow_site=True)

    def _record(self, event: Any, fields: dict) -> dict:
        if isinstance(event, dict):
            return {**self.ctx, **event}
        return {**self.ctx, **fields, "event": event}

    def debug(self, event: Any, **fields: Any) -> None:
        self.logger.debug(self._record(event, fields))

    def info(self, event: Any, **fields: Any) -> None:
        self.logger.info(self._record(event, fields))

    def warning(self, event: Any, **fields: Any) -> None:
        self.logger.warning(self._record(event, fields))

    def error(self, event: Any, **fields: Any) -> None:
        self.logger.error(self._record(event, fields))

    def exception(self, event: Any, **fields: Any) -> None:
        self.logger.exception(self._record(event, fields))


class BaseStore:
    """Base for stores scoped to a `namespace` (a relative directory under `base_path`).

    The namespace gives each store its own directory, so a store's keys need no further
    prefixing to stay isolated from other namespaces. Subclasses decide how keys map to
    values within that directory (LMDB entries for `DataStore`, files for `BlobStore`).
    """

    SEPARATOR: ClassVar[str] = ":"
    _PROCESS_LOCKS: ClassVar[dict[str, RLock]] = {}
    _PROCESS_LOCKS_GUARD: ClassVar[RLock] = RLock()

    def __init__(
        self,
        base_path: str,
        namespace: Namespace,
    ) -> None:
        """Initialize a store rooted at ``<base_path>/<namespace>``.

        `namespace` is a relative path (``"a/b"`` string or sequence of segments) scoping this
        store to its own directory.
        """

        self.base_path = base_path
        self.namespace = normalize_namespace(namespace)

        self.logger_context = {"req_id": random_string(10), "namespace": "/".join(self.namespace)}
        self.logger = _StorageLogger(self.logger_context)

        self.path = resolve_namespace_path(self.base_path, self.namespace)
        os.makedirs(self.path, exist_ok=True)

    def _get_process_lock(self, path: str | None = None) -> RLock:
        """Return a process-local lock shared by all storage instances for the same path."""

        path = path or self.path

        self.logger.debug("acquiring-rlock", path=path)

        with self._PROCESS_LOCKS_GUARD:
            lock = self._PROCESS_LOCKS.get(path)
            if lock is None:
                lock = RLock()
                self._PROCESS_LOCKS[path] = lock

            self.logger.debug("rlock-acquired", path=path)
            return lock

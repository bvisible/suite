#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe
from frappe import _
from frappe.utils import create_batch

from suite.mail.store import MAIL_NAMESPACE, Entity, get_data_store
from suite.mail.utils.dt import to_utc_z
from suite.store import get_data_base_path, list_namespaces

# Timestamp fields each cached entity carries. Records cached before the UTC wire change hold
# naive system-time strings in these fields; the APIs now serve the cache verbatim, reading a
# naive value as UTC — so the stale values must be converted, not reinterpreted.
ENTITY_TIMESTAMP_FIELDS = {
    Entity.EMAIL: ("sent_at", "received_at", "creation", "modified"),
    Entity.CONTACT_CARD: ("created_at", "updated_at", "creation", "modified"),
}

# Records converted per get/set round-trip. Message values carry full bodies, so batching
# bounds both memory and the size of each LMDB write transaction.
BATCH_SIZE = 500


def execute() -> None:
    """Convert cached data-store timestamps from naive system time to the UTC ``...Z`` format.

    The mail APIs now speak UTC ``...Z`` on the wire, and cached records are served verbatim —
    but caches written before that change hold timestamps as naive system-time strings, which a
    client would misread as UTC. Rather than destroying every account's cache, convert the
    timestamp fields in place: each store directory is scanned and every naive value is read in
    the system time zone and rewritten as ``...Z``.

    Idempotent and re-runnable: an already-converted value round-trips to itself and is not
    rewritten. Best-effort per account — a failing store is logged and skipped, since its cache
    can always be destroyed and rebuilt lazily from JMAP.
    """

    for account in _account_namespaces():
        try:
            _migrate_account(account)
        except Exception:
            from suite.mail.utils import log_mail_error

            log_mail_error(
                _("Failed to migrate cached timestamps to UTC for account {0}").format(account),
                frappe.get_traceback(with_context=True),
            )


def _account_namespaces() -> list[str]:
    """Return every JMAP account that has a data store on disk, from the ``mail/<account>`` dirs."""

    accounts = []
    for namespace in list_namespaces(get_data_base_path()):
        if len(namespace) == 2 and namespace[0] == MAIL_NAMESPACE:
            accounts.append(namespace[1])

    return accounts


def _migrate_account(account: str) -> None:
    """Convert every stale timestamp in one account's data store, rewriting only changed records."""

    store = get_data_store(account)

    # Collect keys per entity without deserializing any values, then convert in bounded batches.
    entity_by_prefix = {entity.value: entity for entity in ENTITY_TIMESTAMP_FIELDS}
    keys_by_entity = {entity: [] for entity in ENTITY_TIMESTAMP_FIELDS}
    state_keys = []

    for entry in store.browse():
        if entity := entity_by_prefix.get(entry["entity"]):
            keys_by_entity[entity].append(entry["key"])
        elif entry["entity"] == Entity.STATE.value and entry["key"].endswith("_state_last_update"):
            state_keys.append(entry["key"])

    for entity, keys in keys_by_entity.items():
        fields = ENTITY_TIMESTAMP_FIELDS[entity]
        for batch in create_batch(keys, BATCH_SIZE):
            changed = {}
            for key, record in store.get_many(entity, batch).items():
                if isinstance(record, dict) and _convert_record(record, fields):
                    changed[key] = record

            store.set_many(entity, changed)

    # Sync-state stamps (``<type>_state_last_update``) are bare timestamp strings.
    changed = {}
    for key, value in store.get_many(Entity.STATE, state_keys).items():
        converted = _to_wire(value)
        if converted and converted != value:
            changed[key] = converted

    store.set_many(Entity.STATE, changed)


def _convert_record(record: dict, fields: tuple[str, ...]) -> bool:
    """Convert `fields` on `record` in place, returning whether anything changed."""

    changed = False
    for field in fields:
        value = record.get(field)
        converted = _to_wire(value)
        if converted and converted != value:
            record[field] = converted
            changed = True

    return changed


def _to_wire(value) -> str | None:
    """Convert one cached timestamp to ``...Z``, or None if it isn't a convertible string.

    A naive value is read in the system time zone — the format the old cache was written in.
    Aware values (``...Z`` or an offset form) convert by their own zone, so an already-migrated
    value round-trips unchanged. Unparsable values are left as they are rather than corrupted.
    """

    if not value or not isinstance(value, str):
        return None

    try:
        return to_utc_z(value)
    except Exception:
        return None

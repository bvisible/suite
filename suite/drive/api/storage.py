# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations

# //// Neoffice — the disk the Drive writes to (drive_disk)
import shutil

import frappe
from frappe import _
from pypika import functions as fn

# //// Neoffice — the files a computer writes beside the person's (storage_breakdown)
from suite.drive.api.list import is_system_file
from suite.drive.utils import STATUS_ACTIVE

MEGA_BYTE = 1024**2
DriveFile = frappe.qb.DocType("File")
DriveStorageReservation = frappe.qb.DocType("Drive Storage Reservation")


def acquire_owner_storage_lock(owner: str):
    key = f"drive-storage:{frappe.local.site}:{owner}"
    held_locks = getattr(frappe.local, "drive_storage_locks", None)
    if held_locks is None:
        held_locks = frappe.local.drive_storage_locks = {}
    if key in held_locks:
        return

    lock = frappe.cache.lock(key, timeout=300)
    if not lock.acquire(blocking=True, blocking_timeout=10):
        frappe.throw(_("Drive storage is being updated; try again"))
    held_locks[key] = lock

    def release():
        held_locks.pop(key, None)
        lock.release()

    frappe.db.after_commit.add(release)
    frappe.db.after_rollback.add(release)


def get_quota(user: str | None = None):
    """Effective quota in bytes: the user's override, else the site default. 0 = unlimited."""
    user = user or frappe.session.user
    quota = frappe.get_value("Drive Settings", user, "quota") or frappe.db.get_single_value(
        "Drive Disk Settings", "quota"
    )
    return (quota or 0) * MEGA_BYTE


@frappe.whitelist()
def storage_breakdown():
    limit = get_quota()
    filters = {
        "is_folder": False,
        "status": STATUS_ACTIVE,
        "owner": frappe.session.user,
    }
    if limit:
        filters["file_size"] = [">=", limit / 200]

    entities = frappe.db.get_list(
        "File",
        filters=filters,
        order_by="file_size desc",
        fields=["name", "file_name", "owner", "file_size", "file_type"],
    )
    # //// Neoffice — the files a computer writes beside the person's (the Finder's ._<name>, …) are not offered as large
    # //// files: no list of the Drive shows them (list.py, SYSTEM_FILE_NAMES; maintenance#1598)
    entities = [entity for entity in entities if not is_system_file(entity.file_name)]

    query = (
        frappe.qb.from_(DriveFile)
        .select(DriveFile.file_type, fn.Sum(DriveFile.file_size).as_("file_size"))
        .where(
            (DriveFile.is_folder == 0)
            & (DriveFile.status == STATUS_ACTIVE)
            & (DriveFile.owner == frappe.session.user)
        )
    )

    return {
        "limit": limit,
        "total": query.groupby(DriveFile.file_type).run(as_dict=True),
        "entities": entities,
        # //// Neoffice — said by the statistics when there is no quota, where they said « of your 0 bytes (∞ %) »
        "disk": drive_disk(),
    }


@frappe.whitelist()
def storage_bar_data():
    usage = get_storage_usage()
    # //// Neoffice — the volume the Drive writes its files to: a bar without a quota shows it (it showed « / 5 GB », a
    # //// limit no server has, Jérémy 16.10.2026; maintenance#1598)
    usage["disk"] = drive_disk()
    return usage


# //// Neoffice — added (no upstream equivalent), see storage_bar_data
def drive_disk() -> dict | None:
    """The volume the Drive's files are written to (the site's private files, an additional volume on our servers): its
    size, what is used of it and what is free, in bytes. None when the Drive keeps its files elsewhere (S3), or when the
    volume cannot be read."""
    if frappe.db.get_single_value("Drive Disk Settings", "enabled"):
        return None
    try:
        usage = shutil.disk_usage(frappe.get_site_path("private", "files"))
    except OSError:
        return None
    return {"total": usage.total, "used": usage.used, "free": usage.free}


def get_storage_usage(user: str | None = None):
    user = user or frappe.session.user
    query = (
        frappe.qb.from_(DriveFile)
        .where((DriveFile.is_folder == 0) & (DriveFile.owner == user) & (DriveFile.status == STATUS_ACTIVE))
        .select(fn.Coalesce(fn.Sum(DriveFile.file_size), 0).as_("total_size"))
    )
    result = query.run(as_dict=True)[0]
    reserved = (
        frappe.qb.from_(DriveStorageReservation)
        .select(fn.Coalesce(fn.Sum(DriveStorageReservation.reserved_bytes), 0))
        .where(DriveStorageReservation.storage_owner == user)
    ).run()
    result["reserved_size"] = reserved[0][0]
    result["total_size"] += result["reserved_size"]
    result["limit"] = get_quota(user)
    return result


def validate_quota(user: str | None = None, incoming_size: int = 0):
    """Throw if adding `incoming_size` bytes would push the user past their quota."""
    usage = get_storage_usage(user)
    if usage["limit"] and (usage["limit"] - usage["total_size"]) < incoming_size:
        frappe.throw(_("You're out of storage!"), ValueError)


def create_storage_reservation(owner: str, key: str, reserved_bytes: int):
    """Reserve an absolute byte amount for owner; an exact-key retry is idempotent."""
    reserved_bytes = _validate_reserved_bytes(reserved_bytes)
    _validate_reservation_identity(owner, key)
    acquire_owner_storage_lock(owner)

    reservation = _get_storage_reservation(key, for_update=True)
    if reservation:
        _validate_reservation_owner(reservation, owner)
        if reservation.reserved_bytes != reserved_bytes:
            frappe.throw(_("Storage reservation already exists with a different amount"), ValueError)
        return reservation

    validate_quota(owner, reserved_bytes)
    return frappe.get_doc(
        {
            "doctype": "Drive Storage Reservation",
            "name": key,
            "storage_owner": owner,
            "reserved_bytes": reserved_bytes,
        }
    ).insert(ignore_permissions=True)


def grow_storage_reservation(owner: str, key: str, reserved_bytes: int):
    """Grow an owned reservation to an absolute amount after locked quota admission."""
    reserved_bytes = _validate_reserved_bytes(reserved_bytes)
    reservation = _get_owned_storage_reservation(owner, key)
    if reserved_bytes < reservation.reserved_bytes:
        frappe.throw(_("A storage reservation can only grow to a larger amount"), ValueError)
    if reserved_bytes == reservation.reserved_bytes:
        return reservation

    validate_quota(owner, reserved_bytes - reservation.reserved_bytes)
    reservation.reserved_bytes = reserved_bytes
    reservation.save(ignore_permissions=True)
    return reservation


def reduce_storage_reservation(owner: str, key: str, reserved_bytes: int):
    """Reduce an owned reservation to an absolute nonnegative amount under its owner lock."""
    reserved_bytes = _validate_reserved_bytes(reserved_bytes)
    reservation = _get_owned_storage_reservation(owner, key)
    if reserved_bytes > reservation.reserved_bytes:
        frappe.throw(_("A storage reservation can only reduce to a smaller amount"), ValueError)
    if reserved_bytes == reservation.reserved_bytes:
        return reservation

    reservation.reserved_bytes = reserved_bytes
    reservation.save(ignore_permissions=True)
    return reservation


def release_storage_reservation(owner: str, key: str):
    """Idempotently release an owned reservation under its owner lock."""
    _validate_reservation_identity(owner, key)
    acquire_owner_storage_lock(owner)
    reservation = _get_storage_reservation(key, for_update=True)
    if not reservation:
        return

    _validate_reservation_owner(reservation, owner)
    frappe.db.delete("Drive Storage Reservation", key)


def get_storage_reservation(key: str):
    """Return a reservation by key for trusted server-side callers without an ownership check."""
    return _get_storage_reservation(key)


def _get_storage_reservation(key: str, *, for_update: bool = False):
    if not isinstance(key, str) or not key:
        frappe.throw(_("Storage reservation key must be a nonempty string"), ValueError)
    if not frappe.db.exists("Drive Storage Reservation", key):
        return None
    return frappe.get_doc("Drive Storage Reservation", key, for_update=for_update)


def _get_owned_storage_reservation(owner: str, key: str):
    _validate_reservation_identity(owner, key)
    acquire_owner_storage_lock(owner)
    reservation = _get_storage_reservation(key, for_update=True)
    if not reservation:
        frappe.throw(_("Storage reservation does not exist"), frappe.DoesNotExistError)
    _validate_reservation_owner(reservation, owner)
    return reservation


def _validate_reservation_owner(reservation, owner: str):
    if reservation.storage_owner != owner:
        frappe.throw(_("Storage reservation belongs to a different owner"), ValueError)


def _validate_reservation_identity(owner: str, key: str):
    if not isinstance(owner, str) or not owner:
        frappe.throw(_("Storage reservation owner must be a nonempty string"), ValueError)
    if not isinstance(key, str) or not key:
        frappe.throw(_("Storage reservation key must be a nonempty string"), ValueError)


def _validate_reserved_bytes(reserved_bytes: int) -> int:
    if isinstance(reserved_bytes, bool) or not isinstance(reserved_bytes, int) or reserved_bytes < 0:
        frappe.throw(_("Reserved bytes must be a nonnegative integer"), ValueError)
    return reserved_bytes

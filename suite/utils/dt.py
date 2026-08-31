from __future__ import annotations
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from frappe.utils import get_datetime, get_datetime_str, get_system_timezone


def get_utc_now(naive: bool = False) -> datetime:
    """Returns the current UTC datetime."""

    now = datetime.now(UTC)
    return now.replace(tzinfo=None) if naive else now


def utcnow() -> str:
    """Returns the current UTC time in the canonical ``...Z`` wire format (second precision)."""

    return get_utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def convert_to_utc(
    date_time: datetime | str, from_timezone: str | None = None, naive: bool = False
) -> datetime:
    """Converts the given datetime to UTC timezone."""

    dt = get_datetime(date_time)
    if dt.tzinfo is None:
        tz = ZoneInfo(from_timezone or get_system_timezone())
        dt = dt.replace(tzinfo=tz)

    utc_dt = dt.astimezone(UTC)
    return utc_dt.replace(tzinfo=None) if naive else utc_dt


def parse_iso_datetime(
    datetime_str: str, to_timezone: str | None = None, as_str: bool = True
) -> str | datetime:
    """Converts ISO datetime string to datetime object in given timezone."""

    if not to_timezone:
        to_timezone = get_system_timezone()

    dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        # A naive wire value is UTC — the format the APIs listen in. Without this,
        # .astimezone() would read it in the OS process zone.
        dt = dt.replace(tzinfo=UTC)

    dt = dt.astimezone(ZoneInfo(to_timezone))

    return get_datetime_str(dt) if as_str else dt


def to_iso8601_z(dt: datetime) -> str:
    """
    Convert a datetime (naive or aware) to an ISO 8601 string ending with 'Z' (UTC).

    Rules:
    - If naive, assume UTC.
    - Always return a string like "YYYY-MM-DDTHH:MM:SS.sssZ".
    """

    if isinstance(dt, date):
        dt = get_datetime(dt)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)

    return dt.isoformat().replace("+00:00", "Z")

"""UTC timestamp helpers. Ride files and the API use ISO 8601 with a trailing Z."""
from __future__ import annotations

from datetime import datetime, timezone


def parse_utc(value: str) -> datetime:
    """Parse "YYYY-MM-DDTHH:MM:SS[.fff]Z" into an aware UTC datetime.

    Raises ValueError for anything else, including numeric offsets.
    """
    if not isinstance(value, str) or not value.endswith("Z") or "T" not in value:
        raise ValueError(f"not a UTC timestamp: {value!r}")
    parsed = datetime.fromisoformat(value[:-1])
    if parsed.tzinfo is not None:
        raise ValueError(f"not a UTC timestamp: {value!r}")
    return parsed.replace(tzinfo=timezone.utc)


def format_utc(moment: datetime) -> str:
    if moment.tzinfo is None:
        raise ValueError("naive datetimes are not allowed")
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

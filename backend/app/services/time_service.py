"""User-local date helpers.

Completions are logged against the user's local calendar day, so "today",
streaks, and analytics windows must be computed in the user's timezone — not
the server's. Falls back to UTC for a missing or invalid stored zone so a bad
value can never crash a request.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

UTC = ZoneInfo("UTC")


def local_today(timezone: str | None) -> date:
    """Today's date in the given IANA timezone (UTC fallback on bad input)."""
    try:
        tz = ZoneInfo(timezone) if timezone else UTC
    except (ZoneInfoNotFoundError, ValueError):
        tz = UTC
    return datetime.now(tz).date()

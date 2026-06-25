"""User-local date helpers.

Completions are logged against the user's local calendar day, so "today",
streaks, and analytics windows must be computed in the user's timezone — not
the server's. Falls back to UTC for a missing or invalid stored zone so a bad
value can never crash a request.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

UTC = ZoneInfo("UTC")


def _zone(timezone: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(timezone) if timezone else UTC
    except (ZoneInfoNotFoundError, ValueError):
        return UTC


def local_today(timezone: str | None) -> date:
    """Today's date in the given IANA timezone (UTC fallback on bad input)."""
    return datetime.now(_zone(timezone)).date()


def to_local_date(moment: datetime, timezone: str | None) -> date:
    """The calendar date of an aware (UTC) datetime in the given timezone."""
    return moment.astimezone(_zone(timezone)).date()

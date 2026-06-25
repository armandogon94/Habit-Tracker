"""Daily streak computation.

Streaks are computed on the fly from ``habit_logs`` (no stored ``streaks``
table) so there is a single source of truth. The algorithm counts runs of
consecutive *calendar* days, which is correct because habits are daily-only —
the rrule is validated to ``FREQ=DAILY`` in app/schemas/habit.py. See PLAN.md
lines 287-341 for the original specification.

The pure ``*_from_dates`` helpers hold the algorithm and are unit-tested
directly; the async ``compute_*`` functions are thin database wrappers.
"""

from collections.abc import Iterable
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.habit_log import HabitLog


def current_streak_from_dates(completed_dates: Iterable[date], today: date) -> int:
    """Count consecutive completed days ending at ``today`` (or yesterday).

    An incomplete *today* does not break the streak — counting may start from
    yesterday — but missing both today and yesterday yields 0. Dates after
    ``today`` and duplicate dates are ignored.
    """
    days = {d for d in completed_dates if d <= today}
    if not days:
        return 0

    if today in days:
        expected = today
    elif (today - timedelta(days=1)) in days:
        expected = today - timedelta(days=1)
    else:
        return 0

    streak = 0
    while expected in days:
        streak += 1
        expected -= timedelta(days=1)
    return streak


def longest_streak_from_dates(completed_dates: Iterable[date]) -> int:
    """Return the length of the longest run of consecutive completed days."""
    days = sorted(set(completed_dates))
    if not days:
        return 0

    longest = 1
    current = 1
    for i in range(1, len(days)):
        if (days[i] - days[i - 1]).days == 1:
            current += 1
        else:
            longest = max(longest, current)
            current = 1
    return max(longest, current)


async def compute_current_streak(
    db: AsyncSession, habit_id: UUID, today: date | None = None
) -> int:
    if today is None:
        today = date.today()

    result = await db.execute(
        select(HabitLog.completed_date).where(
            HabitLog.habit_id == habit_id, HabitLog.completed_date <= today
        )
    )
    return current_streak_from_dates((row[0] for row in result.all()), today)


async def compute_longest_streak(db: AsyncSession, habit_id: UUID) -> int:
    result = await db.execute(
        select(HabitLog.completed_date).where(HabitLog.habit_id == habit_id)
    )
    return longest_streak_from_dates(row[0] for row in result.all())

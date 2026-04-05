from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.habit_log import HabitLog


async def compute_current_streak(db: AsyncSession, habit_id: UUID, today: date | None = None) -> int:
    if today is None:
        today = date.today()

    result = await db.execute(
        select(HabitLog.completed_date)
        .where(HabitLog.habit_id == habit_id, HabitLog.completed_date <= today)
        .order_by(HabitLog.completed_date.desc())
    )
    dates = [row[0] for row in result.all()]

    if not dates:
        return 0

    streak = 0
    expected = today

    # Allow today to be incomplete — start from today or yesterday
    if dates[0] == today:
        expected = today
    elif dates[0] == today - timedelta(days=1):
        expected = today - timedelta(days=1)
    else:
        return 0

    for d in dates:
        if d == expected:
            streak += 1
            expected -= timedelta(days=1)
        else:
            break

    return streak


async def compute_longest_streak(db: AsyncSession, habit_id: UUID) -> int:
    result = await db.execute(
        select(HabitLog.completed_date)
        .where(HabitLog.habit_id == habit_id)
        .order_by(HabitLog.completed_date)
    )
    dates = [row[0] for row in result.all()]

    if not dates:
        return 0

    longest = 1
    current = 1

    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days == 1:
            current += 1
        else:
            longest = max(longest, current)
            current = 1

    return max(longest, current)

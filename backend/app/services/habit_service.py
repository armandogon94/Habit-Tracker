from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.habit import Habit
from app.models.habit_log import HabitLog
from app.schemas.habit import (
    CalendarDay,
    HabitAnalytics,
    HabitCreate,
    HabitLogCreate,
    HabitResponse,
    HabitUpdate,
)
from app.services.streak_service import (
    current_streak_from_dates,
    longest_streak_from_dates,
)


def build_habit_responses(
    habits: list[Habit],
    dates_by_habit: dict[UUID, list[date]],
    today: date,
) -> list[HabitResponse]:
    """Build habit responses with streaks computed from pre-fetched logs."""
    responses = []
    for habit in habits:
        dates = dates_by_habit.get(habit.id, [])
        responses.append(
            HabitResponse(
                id=habit.id,
                name=habit.name,
                description=habit.description,
                color=habit.color,
                rrule=habit.rrule,
                created_at=habit.created_at,
                archived_at=habit.archived_at,
                current_streak=current_streak_from_dates(dates, today),
                longest_streak=longest_streak_from_dates(dates),
                completed_today=today in dates,
            )
        )
    return responses


async def list_habits(db: AsyncSession, user_id: UUID) -> list[HabitResponse]:
    result = await db.execute(
        select(Habit)
        .where(Habit.user_id == user_id, Habit.archived_at.is_(None))
        .order_by(Habit.created_at)
    )
    habits = list(result.scalars().all())
    if not habits:
        return []

    # Fetch every log for these habits in one query, then compute streaks in
    # memory — replaces the previous 3-queries-per-habit (N+1) pattern.
    logs_result = await db.execute(
        select(HabitLog.habit_id, HabitLog.completed_date).where(
            HabitLog.habit_id.in_([habit.id for habit in habits])
        )
    )
    dates_by_habit: dict[UUID, list[date]] = defaultdict(list)
    for habit_id, completed_date in logs_result.all():
        dates_by_habit[habit_id].append(completed_date)

    return build_habit_responses(habits, dates_by_habit, date.today())


async def create_habit(db: AsyncSession, user_id: UUID, data: HabitCreate) -> Habit:
    habit = Habit(
        user_id=user_id,
        name=data.name,
        description=data.description,
        color=data.color,
        rrule=data.rrule,
    )
    db.add(habit)
    await db.flush()
    await db.refresh(habit)
    return habit


async def get_habit(db: AsyncSession, habit_id: UUID, user_id: UUID) -> Habit | None:
    result = await db.execute(
        select(Habit).where(Habit.id == habit_id, Habit.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def update_habit(db: AsyncSession, habit: Habit, data: HabitUpdate) -> Habit:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(habit, field, value)
    await db.flush()
    await db.refresh(habit)
    return habit


async def archive_habit(db: AsyncSession, habit: Habit) -> None:
    from datetime import datetime, timezone

    habit.archived_at = datetime.now(timezone.utc)
    await db.flush()


async def log_completion(
    db: AsyncSession, habit_id: UUID, data: HabitLogCreate
) -> HabitLog:
    # Check for existing log on same date
    existing = await db.execute(
        select(HabitLog).where(
            HabitLog.habit_id == habit_id, HabitLog.completed_date == data.completed_date
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Already logged for this date")

    log = HabitLog(
        habit_id=habit_id,
        completed_date=data.completed_date,
        notes=data.notes,
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log


async def remove_completion(db: AsyncSession, habit_id: UUID, completed_date: date) -> bool:
    result = await db.execute(
        select(HabitLog).where(
            HabitLog.habit_id == habit_id, HabitLog.completed_date == completed_date
        )
    )
    log = result.scalar_one_or_none()
    if not log:
        return False
    await db.delete(log)
    await db.flush()
    return True


async def get_logs(
    db: AsyncSession, habit_id: UUID, start_date: date, end_date: date
) -> list[HabitLog]:
    result = await db.execute(
        select(HabitLog)
        .where(
            HabitLog.habit_id == habit_id,
            HabitLog.completed_date >= start_date,
            HabitLog.completed_date <= end_date,
        )
        .order_by(HabitLog.completed_date)
    )
    return list(result.scalars().all())


async def get_calendar(
    db: AsyncSession, habit_id: UUID, start_date: date, end_date: date
) -> list[CalendarDay]:
    logs = await get_logs(db, habit_id, start_date, end_date)
    completed_dates = {log.completed_date for log in logs}

    days = []
    current = start_date
    while current <= end_date:
        days.append(CalendarDay(date=current, completed=current in completed_dates))
        current += timedelta(days=1)
    return days


def completion_rate_pct(
    completed_dates: Iterable[date],
    today: date,
    created_date: date,
    window_days: int = 30,
) -> float:
    """Percent of eligible days completed in the trailing window.

    The window is the last ``window_days`` days, inclusive of today. Days before
    the habit existed do not count toward the denominator, so a brand-new habit
    is not penalised. The result is rounded to one decimal and clamped to 0-100.
    """
    window_start = today - timedelta(days=window_days - 1)
    effective_start = max(window_start, created_date)
    eligible_days = max(1, (today - effective_start).days + 1)
    completed = len({d for d in completed_dates if effective_start <= d <= today})
    rate = (completed / eligible_days) * 100
    return round(min(100.0, max(0.0, rate)), 1)


def build_analytics(
    completed_dates: Iterable[date],
    today: date,
    created_date: date,
) -> HabitAnalytics:
    """Compute analytics from a habit's completion dates (no DB access)."""
    all_dates = list(completed_dates)

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    weekday_counts = Counter(d.weekday() for d in all_dates)
    weekly = {day_names[i]: weekday_counts.get(i, 0) for i in range(7)}
    best_day = None
    if weekday_counts:
        best_day = day_names[max(weekday_counts, key=weekday_counts.get)]

    return HabitAnalytics(
        total_completions=len(all_dates),
        completion_rate=completion_rate_pct(all_dates, today, created_date),
        current_streak=current_streak_from_dates(all_dates, today),
        longest_streak=longest_streak_from_dates(all_dates),
        best_day=best_day,
        weekly_counts=weekly,
    )


async def get_analytics(db: AsyncSession, habit: Habit) -> HabitAnalytics:
    today = date.today()

    # Single fetch of all completion dates; every metric is derived in memory,
    # replacing the previous separate streak/count/weekly/rate queries.
    result = await db.execute(
        select(HabitLog.completed_date).where(HabitLog.habit_id == habit.id)
    )
    all_dates = [row[0] for row in result.all()]

    window_start = today - timedelta(days=29)
    created_date = habit.created_at.date() if habit.created_at else window_start
    return build_analytics(all_dates, today, created_date)

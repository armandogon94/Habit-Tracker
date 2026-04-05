from collections import Counter
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select
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
from app.services.streak_service import compute_current_streak, compute_longest_streak


async def list_habits(db: AsyncSession, user_id: UUID) -> list[HabitResponse]:
    result = await db.execute(
        select(Habit)
        .where(Habit.user_id == user_id, Habit.archived_at.is_(None))
        .order_by(Habit.created_at)
    )
    habits = result.scalars().all()

    today = date.today()
    responses = []
    for habit in habits:
        current = await compute_current_streak(db, habit.id, today)
        longest = await compute_longest_streak(db, habit.id)

        # Check if completed today
        log_result = await db.execute(
            select(HabitLog).where(
                HabitLog.habit_id == habit.id, HabitLog.completed_date == today
            )
        )
        completed_today = log_result.scalar_one_or_none() is not None

        responses.append(
            HabitResponse(
                id=habit.id,
                name=habit.name,
                description=habit.description,
                color=habit.color,
                rrule=habit.rrule,
                created_at=habit.created_at,
                archived_at=habit.archived_at,
                current_streak=current,
                longest_streak=longest,
                completed_today=completed_today,
            )
        )

    return responses


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


async def get_analytics(db: AsyncSession, habit_id: UUID) -> HabitAnalytics:
    # Total completions
    count_result = await db.execute(
        select(func.count()).where(HabitLog.habit_id == habit_id)
    )
    total = count_result.scalar() or 0

    # Streaks
    today = date.today()
    current = await compute_current_streak(db, habit_id, today)
    longest = await compute_longest_streak(db, habit_id)

    # Last 30 days completion rate
    thirty_days_ago = today - timedelta(days=30)
    recent_logs = await get_logs(db, habit_id, thirty_days_ago, today)
    rate = (len(recent_logs) / 30) * 100 if total > 0 else 0.0

    # Weekly distribution
    all_result = await db.execute(
        select(HabitLog.completed_date).where(HabitLog.habit_id == habit_id)
    )
    all_dates = [row[0] for row in all_result.all()]
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    weekday_counts = Counter(d.weekday() for d in all_dates)
    weekly = {day_names[i]: weekday_counts.get(i, 0) for i in range(7)}

    # Best day
    best_day = None
    if weekday_counts:
        best_idx = max(weekday_counts, key=weekday_counts.get)
        best_day = day_names[best_idx]

    return HabitAnalytics(
        total_completions=total,
        completion_rate=round(rate, 1),
        current_streak=current,
        longest_streak=longest,
        best_day=best_day,
        weekly_counts=weekly,
    )

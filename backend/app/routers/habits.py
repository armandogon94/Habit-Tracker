from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.habit import (
    CalendarDay,
    HabitAnalytics,
    HabitCreate,
    HabitLogCreate,
    HabitLogResponse,
    HabitResponse,
    HabitUpdate,
)
from app.services import habit_service
from app.services.streak_service import compute_current_streak, compute_longest_streak

router = APIRouter(prefix="/api/v1/habits", tags=["habits"])


@router.get("", response_model=list[HabitResponse])
async def list_habits(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await habit_service.list_habits(db, user.id)


@router.post("", response_model=HabitResponse, status_code=status.HTTP_201_CREATED)
async def create_habit(
    data: HabitCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    habit = await habit_service.create_habit(db, user.id, data)
    return HabitResponse(
        id=habit.id,
        name=habit.name,
        description=habit.description,
        color=habit.color,
        rrule=habit.rrule,
        created_at=habit.created_at,
        current_streak=0,
        longest_streak=0,
        completed_today=False,
    )


@router.get("/{habit_id}", response_model=HabitResponse)
async def get_habit(
    habit_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    habit = await habit_service.get_habit(db, habit_id, user.id)
    if not habit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found")

    today = date.today()
    current = await compute_current_streak(db, habit.id, today)
    longest = await compute_longest_streak(db, habit.id)
    logs = await habit_service.get_logs(db, habit.id, today, today)
    completed_today = len(logs) > 0

    return HabitResponse(
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


@router.put("/{habit_id}", response_model=HabitResponse)
async def update_habit(
    habit_id: UUID,
    data: HabitUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    habit = await habit_service.get_habit(db, habit_id, user.id)
    if not habit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found")

    habit = await habit_service.update_habit(db, habit, data)
    current = await compute_current_streak(db, habit.id)
    longest = await compute_longest_streak(db, habit.id)

    return HabitResponse(
        id=habit.id,
        name=habit.name,
        description=habit.description,
        color=habit.color,
        rrule=habit.rrule,
        created_at=habit.created_at,
        current_streak=current,
        longest_streak=longest,
    )


@router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_habit(
    habit_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    habit = await habit_service.get_habit(db, habit_id, user.id)
    if not habit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found")
    await habit_service.archive_habit(db, habit)


@router.post("/{habit_id}/log", response_model=HabitLogResponse, status_code=status.HTTP_201_CREATED)
async def log_completion(
    habit_id: UUID,
    data: HabitLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    habit = await habit_service.get_habit(db, habit_id, user.id)
    if not habit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found")

    try:
        log = await habit_service.log_completion(db, habit_id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return log


@router.delete("/{habit_id}/log/{log_date}")
async def remove_log(
    habit_id: UUID,
    log_date: date,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    habit = await habit_service.get_habit(db, habit_id, user.id)
    if not habit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found")

    removed = await habit_service.remove_completion(db, habit_id, log_date)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log not found")
    return {"removed": True}


@router.get("/{habit_id}/logs", response_model=list[HabitLogResponse])
async def get_logs(
    habit_id: UUID,
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    habit = await habit_service.get_habit(db, habit_id, user.id)
    if not habit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found")

    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=90)

    return await habit_service.get_logs(db, habit_id, start_date, end_date)


@router.get("/{habit_id}/calendar", response_model=list[CalendarDay])
async def get_calendar(
    habit_id: UUID,
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    habit = await habit_service.get_habit(db, habit_id, user.id)
    if not habit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found")

    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=365)

    return await habit_service.get_calendar(db, habit_id, start_date, end_date)


@router.get("/{habit_id}/analytics", response_model=HabitAnalytics)
async def get_analytics(
    habit_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    habit = await habit_service.get_habit(db, habit_id, user.id)
    if not habit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found")

    return await habit_service.get_analytics(db, habit.id)

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class HabitCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    color: str = Field(default="#3B82F6", pattern=r"^#[0-9a-fA-F]{6}$")
    rrule: str = "FREQ=DAILY"


class HabitUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    color: str | None = None
    rrule: str | None = None


class HabitResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    color: str
    rrule: str
    created_at: datetime
    archived_at: datetime | None = None
    current_streak: int = 0
    longest_streak: int = 0
    completed_today: bool = False

    model_config = {"from_attributes": True}


class HabitLogCreate(BaseModel):
    completed_date: date
    notes: str | None = None


class HabitLogResponse(BaseModel):
    id: UUID
    habit_id: UUID
    completed_date: date
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CalendarDay(BaseModel):
    date: date
    completed: bool


class HabitAnalytics(BaseModel):
    total_completions: int
    completion_rate: float
    current_streak: int
    longest_streak: int
    best_day: str | None = None
    weekly_counts: dict[str, int]

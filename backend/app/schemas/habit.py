from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# Only daily habits are supported for now. The streak, calendar, and analytics
# logic all assume every calendar day is a due occurrence, so accepting any
# other recurrence (weekly, custom BYDAY, INTERVAL>1) would silently produce
# wrong results. Reject anything but the canonical daily rule until real RRULE
# scheduling is implemented. See PLAN.md lines 287-341.
DAILY_RRULE = "FREQ=DAILY"
# Accepted as "daily": FREQ=DAILY alone, or with an explicit INTERVAL=1. The
# rule is parsed into an unordered set of components so clause order does not
# matter (FREQ=DAILY;INTERVAL=1 and INTERVAL=1;FREQ=DAILY are equivalent).
_DAILY_COMPONENT_SETS = ({"FREQ=DAILY"}, {"FREQ=DAILY", "INTERVAL=1"})


def normalize_daily_rrule(value: str) -> str:
    """Return the canonical ``FREQ=DAILY`` or raise for non-daily schedules."""
    normalized = value.strip()
    if normalized.upper().startswith("RRULE:"):
        normalized = normalized[len("RRULE:") :]
    components = {part.strip().upper() for part in normalized.split(";") if part.strip()}
    if components in _DAILY_COMPONENT_SETS:
        return DAILY_RRULE
    raise ValueError(
        "Only daily habits are supported for now: rrule must be 'FREQ=DAILY'. "
        "Custom schedules are not yet implemented."
    )


class HabitCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    color: str = Field(default="#3B82F6", pattern=r"^#[0-9a-fA-F]{6}$")
    rrule: str = DAILY_RRULE

    @field_validator("rrule")
    @classmethod
    def _validate_rrule(cls, value: str) -> str:
        return normalize_daily_rrule(value)


class HabitUpdate(BaseModel):
    # Mirror HabitCreate's constraints so update cannot set values create rejects
    # (empty/overlong name, non-hex color).
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    rrule: str | None = None

    @field_validator("rrule")
    @classmethod
    def _validate_rrule(cls, value: str | None) -> str | None:
        return None if value is None else normalize_daily_rrule(value)


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

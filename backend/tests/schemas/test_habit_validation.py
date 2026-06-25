import pytest
from pydantic import ValidationError

from app.schemas.habit import HabitUpdate, normalize_daily_rrule


def test_rrule_is_order_insensitive():
    assert normalize_daily_rrule("FREQ=DAILY;INTERVAL=1") == "FREQ=DAILY"
    assert normalize_daily_rrule("INTERVAL=1;FREQ=DAILY") == "FREQ=DAILY"
    assert normalize_daily_rrule("RRULE:FREQ=DAILY") == "FREQ=DAILY"
    assert normalize_daily_rrule("  freq=daily ") == "FREQ=DAILY"


def test_rrule_rejects_non_daily():
    for bad in ("FREQ=WEEKLY", "FREQ=DAILY;INTERVAL=2", "FREQ=DAILY;BYDAY=MO"):
        with pytest.raises(ValueError):
            normalize_daily_rrule(bad)


def test_habit_update_rejects_empty_name():
    with pytest.raises(ValidationError):
        HabitUpdate(name="")


def test_habit_update_rejects_bad_color():
    with pytest.raises(ValidationError):
        HabitUpdate(color="red")


def test_habit_update_accepts_valid_and_all_none():
    updated = HabitUpdate(name="Read", color="#AABBCC")
    assert updated.name == "Read"
    empty = HabitUpdate()
    assert empty.name is None and empty.color is None

"""Tests for the daily-only rrule validation on habit schemas.

The product currently supports daily habits only (PLAN.md lines 287-341); the
streak, calendar, and analytics logic all assume every calendar day is a due
occurrence. These tests pin the API contract to that behavior: only the
canonical ``FREQ=DAILY`` rule is accepted, everything else is rejected.
"""

import pytest
from pydantic import ValidationError

from app.schemas.habit import HabitCreate, HabitUpdate


class TestHabitCreateRrule:
    def test_defaults_to_daily(self):
        habit = HabitCreate(name="Read")
        assert habit.rrule == "FREQ=DAILY"

    def test_accepts_canonical_daily(self):
        assert HabitCreate(name="Read", rrule="FREQ=DAILY").rrule == "FREQ=DAILY"

    def test_normalizes_lowercase_and_whitespace(self):
        assert HabitCreate(name="Read", rrule="  freq=daily  ").rrule == "FREQ=DAILY"

    def test_strips_rrule_prefix(self):
        assert HabitCreate(name="Read", rrule="RRULE:FREQ=DAILY").rrule == "FREQ=DAILY"

    def test_strips_trailing_semicolon(self):
        assert HabitCreate(name="Read", rrule="FREQ=DAILY;").rrule == "FREQ=DAILY"

    def test_accepts_explicit_interval_one(self):
        # INTERVAL=1 is semantically identical to plain daily.
        assert HabitCreate(name="Read", rrule="FREQ=DAILY;INTERVAL=1").rrule == "FREQ=DAILY"

    def test_rejects_weekly_schedule(self):
        with pytest.raises(ValidationError):
            HabitCreate(name="Read", rrule="FREQ=WEEKLY;BYDAY=MO,WE,FR")

    def test_rejects_weekdays_only(self):
        with pytest.raises(ValidationError):
            HabitCreate(name="Read", rrule="FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR")

    def test_rejects_interval_greater_than_one(self):
        # Every-other-day is NOT honored by the streak algorithm, so reject it
        # rather than silently miscount.
        with pytest.raises(ValidationError):
            HabitCreate(name="Read", rrule="FREQ=DAILY;INTERVAL=2")

    def test_rejects_garbage(self):
        with pytest.raises(ValidationError):
            HabitCreate(name="Read", rrule="not-an-rrule")

    def test_rejects_empty_string(self):
        with pytest.raises(ValidationError):
            HabitCreate(name="Read", rrule="")


class TestHabitUpdateRrule:
    def test_none_is_allowed(self):
        # rrule omitted on update means "leave unchanged".
        update = HabitUpdate(name="New name")
        assert update.rrule is None

    def test_explicit_none_is_allowed(self):
        assert HabitUpdate(rrule=None).rrule is None

    def test_accepts_and_normalizes_daily(self):
        assert HabitUpdate(rrule="freq=daily").rrule == "FREQ=DAILY"

    def test_rejects_non_daily(self):
        with pytest.raises(ValidationError):
            HabitUpdate(rrule="FREQ=MONTHLY")

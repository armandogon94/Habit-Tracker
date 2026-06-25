from datetime import date

import pytest

from app.services.habit_service import build_analytics, validate_date_range
from app.services.streak_service import longest_streak_from_dates
from app.services.time_service import local_today


def test_local_today_returns_date_for_valid_zone():
    assert isinstance(local_today("America/Los_Angeles"), date)


def test_local_today_falls_back_to_utc_on_bad_input():
    # Must never raise: a bad/missing stored timezone defaults to UTC.
    assert isinstance(local_today("Not/AZone"), date)
    assert isinstance(local_today(None), date)
    assert isinstance(local_today(""), date)


def test_validate_date_range_accepts_normal_range():
    validate_date_range(date(2026, 1, 1), date(2026, 1, 31))


def test_validate_date_range_rejects_inverted():
    with pytest.raises(ValueError):
        validate_date_range(date(2026, 2, 1), date(2026, 1, 1))


def test_validate_date_range_rejects_too_large():
    with pytest.raises(ValueError):
        validate_date_range(date(2024, 1, 1), date(2026, 1, 1), max_days=366)


def test_validate_date_range_allows_exactly_max():
    # 10 inclusive days == max_days, so it must pass.
    validate_date_range(date(2026, 1, 1), date(2026, 1, 10), max_days=10)


def test_build_analytics_ignores_future_dates():
    today = date(2026, 6, 15)
    dates = [date(2026, 6, 14), today, date(2026, 6, 20)]  # last one is future
    analytics = build_analytics(dates, today, created_date=date(2026, 6, 1))
    assert analytics.total_completions == 2


def test_longest_streak_ignores_future_when_today_given():
    dates = [
        date(2026, 6, 1), date(2026, 6, 2), date(2026, 6, 3),  # 3-day run (past)
        date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 3), date(2026, 7, 4),  # 4-day future
    ]
    today = date(2026, 6, 15)
    assert longest_streak_from_dates(dates) == 4  # unfiltered counts the future run
    assert longest_streak_from_dates(dates, today) == 3  # future run excluded

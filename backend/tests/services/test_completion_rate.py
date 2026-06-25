"""Unit tests for the trailing-window completion-rate calculation.

Regression coverage for a bug where the rate could exceed 100%: the analytics
query used an *inclusive* 31-day window (``today - 30`` .. ``today``) but divided
by 30. The rate is now computed over a true 30-day window, counting only days
the habit has existed (so a brand-new habit isn't penalised), and clamped to
0-100%.
"""

from datetime import date, timedelta

from app.services.habit_service import completion_rate_pct

TODAY = date(2026, 6, 24)


def d(offset: int) -> date:
    """Return TODAY shifted by ``offset`` days (negative = in the past)."""
    return TODAY + timedelta(days=offset)


# An "established" habit existed well before the window started.
ESTABLISHED = d(-365)


class TestCompletionRate:
    def test_no_completions_is_zero(self):
        assert completion_rate_pct([], TODAY, ESTABLISHED) == 0.0

    def test_all_30_days_is_100(self):
        dates = [d(-i) for i in range(30)]  # today .. today-29 inclusive
        assert completion_rate_pct(dates, TODAY, ESTABLISHED) == 100.0

    def test_never_exceeds_100_for_inclusive_window(self):
        # Regression: 31 consecutive logged days must not produce >100%.
        dates = [d(-i) for i in range(31)]  # today .. today-30
        assert completion_rate_pct(dates, TODAY, ESTABLISHED) == 100.0

    def test_half_of_established_window(self):
        dates = [d(-i) for i in range(15)]
        assert completion_rate_pct(dates, TODAY, ESTABLISHED) == 50.0

    def test_dates_before_window_are_ignored(self):
        # Two recent completions + one outside the 30-day window → 2/30.
        dates = [d(0), d(-1), d(-45)]
        assert completion_rate_pct(dates, TODAY, ESTABLISHED) == 6.7

    def test_new_habit_is_not_penalised(self):
        # Created 4 days ago → 5 eligible days; all completed → 100%.
        dates = [d(-i) for i in range(5)]
        assert completion_rate_pct(dates, TODAY, d(-4)) == 100.0

    def test_new_habit_partial(self):
        # 5 eligible days, 3 completed → 60%.
        dates = [d(0), d(-1), d(-2)]
        assert completion_rate_pct(dates, TODAY, d(-4)) == 60.0

    def test_created_today_single_completion_is_100(self):
        assert completion_rate_pct([d(0)], TODAY, TODAY) == 100.0

    def test_rounds_to_one_decimal(self):
        # 1 of 3 eligible days → 33.3
        assert completion_rate_pct([d(0)], TODAY, d(-2)) == 33.3

    def test_future_created_date_does_not_crash(self):
        # Clock skew: created date after today must not divide by zero/negative.
        assert completion_rate_pct([], TODAY, d(5)) == 0.0

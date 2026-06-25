"""Unit tests for the pure streak-counting logic.

These exercise the daily-only streak algorithm directly, without a database,
by testing the pure helpers that the async ``compute_*`` wrappers delegate to.
The algorithm is specified in PLAN.md lines 287-341: a streak is a run of
consecutive *calendar* days, which is valid because every habit is daily-only
(see the rrule validator in app/schemas/habit.py).
"""

from datetime import date, timedelta

from app.services.streak_service import (
    current_streak_from_dates,
    longest_streak_from_dates,
)

TODAY = date(2026, 6, 24)


def d(offset: int) -> date:
    """Return TODAY shifted by ``offset`` days (negative = in the past)."""
    return TODAY + timedelta(days=offset)


# ---------------------------------------------------------------------------
# current_streak_from_dates
# ---------------------------------------------------------------------------


class TestCurrentStreak:
    def test_no_completions_is_zero(self):
        assert current_streak_from_dates([], TODAY) == 0

    def test_only_today_is_one(self):
        assert current_streak_from_dates([d(0)], TODAY) == 1

    def test_today_and_yesterday_is_two(self):
        assert current_streak_from_dates([d(0), d(-1)], TODAY) == 2

    def test_long_unbroken_run(self):
        dates = [d(-offset) for offset in range(0, 10)]  # today .. 9 days ago
        assert current_streak_from_dates(dates, TODAY) == 10

    def test_today_missing_but_yesterday_present_counts_from_yesterday(self):
        # Grace period: an incomplete *today* does not zero the streak.
        assert current_streak_from_dates([d(-1), d(-2), d(-3)], TODAY) == 3

    def test_neither_today_nor_yesterday_is_zero(self):
        # Streak is broken once two due days in a row are missed.
        assert current_streak_from_dates([d(-2), d(-3), d(-4)], TODAY) == 0

    def test_gap_breaks_the_streak(self):
        # today, yesterday present; then a gap at day -2; older days don't count.
        assert current_streak_from_dates([d(0), d(-1), d(-3), d(-4)], TODAY) == 2

    def test_unordered_input_is_handled(self):
        assert current_streak_from_dates([d(-2), d(0), d(-1)], TODAY) == 3

    def test_duplicate_dates_do_not_inflate_the_streak(self):
        assert current_streak_from_dates([d(0), d(0), d(-1)], TODAY) == 2

    def test_future_dates_are_ignored(self):
        # A log dated in the future must not extend or seed the streak.
        assert current_streak_from_dates([d(5), d(0), d(-1)], TODAY) == 2

    def test_only_future_dates_is_zero(self):
        assert current_streak_from_dates([d(1), d(2)], TODAY) == 0

    def test_today_parameter_is_respected(self):
        # Same data, evaluated "as of" two days later → streak is broken.
        dates = [d(0), d(-1)]
        assert current_streak_from_dates(dates, d(2)) == 0


# ---------------------------------------------------------------------------
# longest_streak_from_dates
# ---------------------------------------------------------------------------


class TestLongestStreak:
    def test_no_completions_is_zero(self):
        assert longest_streak_from_dates([]) == 0

    def test_single_completion_is_one(self):
        assert longest_streak_from_dates([d(-5)]) == 1

    def test_unbroken_run(self):
        assert longest_streak_from_dates([d(-2), d(-1), d(0)]) == 3

    def test_picks_the_longest_of_several_runs(self):
        # run of 2 (-10,-9), gap, run of 4 (-5..-2), gap, run of 1 (0)
        dates = [d(-10), d(-9), d(-5), d(-4), d(-3), d(-2), d(0)]
        assert longest_streak_from_dates(dates) == 4

    def test_trailing_run_is_counted(self):
        # The longest run is the most recent one and must not be dropped.
        dates = [d(-10), d(-8), d(-2), d(-1), d(0)]
        assert longest_streak_from_dates(dates) == 3

    def test_unordered_input_is_handled(self):
        assert longest_streak_from_dates([d(0), d(-2), d(-1)]) == 3

    def test_duplicate_dates_do_not_inflate(self):
        assert longest_streak_from_dates([d(-1), d(-1), d(0)]) == 2

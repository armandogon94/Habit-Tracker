"""Unit tests for the pure builders used by the batched habit-service queries.

``list_habits`` and ``get_analytics`` fetch all logs up front in a single query
and then build their responses in memory via these pure helpers (no DB access),
which removed an N+1 (3 queries per habit) and several redundant full-table
fetches. Testing the builders directly proves the in-memory logic without a DB.
"""

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from app.models.habit import Habit
from app.services.habit_service import build_analytics, build_habit_responses

TODAY = date(2026, 6, 24)
ESTABLISHED = date(2026, 6, 24) - timedelta(days=365)
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def d(offset: int) -> date:
    return TODAY + timedelta(days=offset)


def make_habit(name: str = "Habit") -> Habit:
    """An in-memory Habit (never flushed) for exercising the builders."""
    return Habit(
        id=uuid4(),
        name=name,
        description=None,
        color="#3B82F6",
        rrule="FREQ=DAILY",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        archived_at=None,
    )


class TestBuildHabitResponses:
    def test_empty(self):
        assert build_habit_responses([], {}, TODAY) == []

    def test_streaks_and_completed_today(self):
        habit = make_habit()
        [resp] = build_habit_responses([habit], {habit.id: [d(0), d(-1), d(-2)]}, TODAY)
        assert resp.current_streak == 3
        assert resp.longest_streak == 3
        assert resp.completed_today is True

    def test_habit_without_logs(self):
        habit = make_habit()
        [resp] = build_habit_responses([habit], {}, TODAY)
        assert resp.current_streak == 0
        assert resp.longest_streak == 0
        assert resp.completed_today is False

    def test_logs_are_partitioned_per_habit(self):
        a, b = make_habit("A"), make_habit("B")
        dates_by_habit = {a.id: [d(0), d(-1)], b.id: [d(-5)]}
        by_name = {r.name: r for r in build_habit_responses([a, b], dates_by_habit, TODAY)}
        assert by_name["A"].current_streak == 2
        assert by_name["A"].completed_today is True
        # B's only log is 5 days ago — no current streak, not completed today.
        assert by_name["B"].current_streak == 0
        assert by_name["B"].completed_today is False

    def test_preserves_input_order(self):
        habits = [make_habit("first"), make_habit("second"), make_habit("third")]
        responses = build_habit_responses(habits, {}, TODAY)
        assert [r.name for r in responses] == ["first", "second", "third"]


class TestBuildAnalytics:
    def test_empty(self):
        result = build_analytics([], TODAY, ESTABLISHED)
        assert result.total_completions == 0
        assert result.completion_rate == 0.0
        assert result.current_streak == 0
        assert result.longest_streak == 0
        assert result.best_day is None
        assert result.weekly_counts == {name: 0 for name in DAY_NAMES}

    def test_totals_and_streaks(self):
        result = build_analytics([d(0), d(-1), d(-2)], TODAY, ESTABLISHED)
        assert result.total_completions == 3
        assert result.current_streak == 3
        assert result.longest_streak == 3

    def test_completion_rate_uses_window(self):
        # 15 of the last 30 days for an established habit → 50%.
        result = build_analytics([d(-i) for i in range(15)], TODAY, ESTABLISHED)
        assert result.completion_rate == 50.0

    def test_weekly_distribution_and_best_day(self):
        anchor = date(2026, 6, 1)
        # Three completions on one weekday, one on the next day.
        dates = [
            anchor,
            anchor + timedelta(days=7),
            anchor + timedelta(days=14),
            anchor + timedelta(days=1),
        ]
        result = build_analytics(dates, TODAY, ESTABLISHED)
        assert result.best_day == DAY_NAMES[anchor.weekday()]
        assert result.weekly_counts[DAY_NAMES[anchor.weekday()]] == 3
        assert result.weekly_counts[DAY_NAMES[(anchor + timedelta(days=1)).weekday()]] == 1

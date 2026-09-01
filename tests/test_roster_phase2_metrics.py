"""Tests for Phase 2 roster metrics (leave affect_target split)."""

import unittest
from datetime import date

from utils.roster_metrics import recalculate_metrics_from_days_and_leaves


class RosterPhase2MetricsTest(unittest.TestCase):
    def _working_day(self, d: date, full: bool = True):
        return {
            "roster_date": d,
            "day_type": "Working",
            "working_type": "Full" if full else "Half",
            "working_hours": 9.0 if full else 4.5,
        }

    def _leave_day(self, d: date, leave_id: int = 1):
        return {
            "roster_date": d,
            "day_type": "Leave",
            "leave_id": leave_id,
            "working_type": "Full",
            "working_hours": 9.0,
        }

    def test_leave_affect_target_yes_reduces_both(self):
        days = [
            self._working_day(date(2026, 3, 2)),
            self._working_day(date(2026, 3, 3)),
            self._leave_day(date(2026, 3, 4)),
            self._working_day(date(2026, 3, 5)),
        ]
        leaves = [
            {
                "is_active": 1,
                "affect_target": 1,
                "is_half_day": 0,
                "start_date": date(2026, 3, 4),
                "end_date": date(2026, 3, 4),
            }
        ]
        metrics = recalculate_metrics_from_days_and_leaves(days, leaves)
        self.assertEqual(metrics["calendar_working_days"], 3.0)
        self.assertEqual(metrics["target_working_days"], 3.0)
        self.assertEqual(metrics["monthly_target_hours"], 27.0)

    def test_leave_affect_target_no_reduces_calendar_only(self):
        days = [
            self._working_day(date(2026, 3, 2)),
            self._working_day(date(2026, 3, 3)),
            self._leave_day(date(2026, 3, 4)),
            self._working_day(date(2026, 3, 5)),
        ]
        leaves = [
            {
                "is_active": 1,
                "affect_target": 0,
                "is_half_day": 0,
                "start_date": date(2026, 3, 4),
                "end_date": date(2026, 3, 4),
            }
        ]
        metrics = recalculate_metrics_from_days_and_leaves(days, leaves)
        self.assertEqual(metrics["calendar_working_days"], 3.0)
        self.assertEqual(metrics["target_working_days"], 4.0)
        self.assertEqual(metrics["monthly_target_hours"], 36.0)

    def test_half_day_leave_affect_target_no_keeps_full_target(self):
        days = [
            self._working_day(date(2026, 3, 2)),
            self._leave_day(date(2026, 3, 3)),
        ]
        leaves = [
            {
                "is_active": 1,
                "affect_target": 0,
                "is_half_day": 1,
                "start_date": date(2026, 3, 3),
                "end_date": date(2026, 3, 3),
            }
        ]
        metrics = recalculate_metrics_from_days_and_leaves(days, leaves)
        # Half leave still on calendar as 0.5 worked; affect No restores other half
        self.assertEqual(metrics["calendar_working_days"], 1.5)
        self.assertEqual(metrics["target_working_days"], 2.0)
        self.assertEqual(metrics["monthly_target_hours"], 18.0)

    def test_half_day_leave_affect_target_yes_nets_half_day(self):
        """Half leave + affect target: calendar and target both −0.5."""
        days = [
            self._working_day(date(2026, 3, 2)),
            self._leave_day(date(2026, 3, 3)),
            self._working_day(date(2026, 3, 4)),
        ]
        leaves = [
            {
                "is_active": 1,
                "affect_target": 1,
                "is_half_day": 1,
                "start_date": date(2026, 3, 3),
                "end_date": date(2026, 3, 3),
            }
        ]
        metrics = recalculate_metrics_from_days_and_leaves(days, leaves)
        self.assertEqual(metrics["calendar_working_days"], 2.5)
        self.assertEqual(metrics["target_working_days"], 2.5)
        self.assertEqual(metrics["monthly_target_hours"], 22.5)

    def test_mixed_full_and_half_affect_target_yes(self):
        """23 baseline − 4 full − 0.5 half = 18.5 days / 166.5 hours."""
        days = [self._working_day(date(2026, 7, d)) for d in range(1, 24)]
        leave_dates_full = [date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 3), date(2026, 7, 4)]
        half_date = date(2026, 7, 5)
        for i, d in enumerate(days):
            rd = d["roster_date"]
            if rd in leave_dates_full or rd == half_date:
                days[i] = self._leave_day(rd, leave_id=1 if rd != half_date else 2)

        leaves = [
            {
                "is_active": 1,
                "affect_target": 1,
                "is_half_day": 0,
                "start_date": date(2026, 7, 1),
                "end_date": date(2026, 7, 3),
            },
            {
                "is_active": 1,
                "affect_target": 1,
                "is_half_day": 0,
                "start_date": date(2026, 7, 4),
                "end_date": date(2026, 7, 4),
            },
            {
                "is_active": 1,
                "affect_target": 1,
                "is_half_day": 1,
                "start_date": half_date,
                "end_date": half_date,
            },
        ]
        metrics = recalculate_metrics_from_days_and_leaves(days, leaves)
        self.assertEqual(metrics["calendar_working_days"], 18.5)
        self.assertEqual(metrics["target_working_days"], 18.5)
        self.assertEqual(metrics["monthly_target_hours"], 166.5)

    def test_half_working_stale_full_hours_reduces_target(self):
        """Half Working with working_hours still 9 must count 4.5h not 9h."""
        days = [
            self._working_day(date(2026, 7, 1)),
            {
                "roster_date": date(2026, 7, 2),
                "day_type": "Working",
                "working_type": "Half",
                "working_hours": 9.0,
            },
            self._working_day(date(2026, 7, 3)),
        ]
        metrics = recalculate_metrics_from_days_and_leaves(days, [])
        self.assertEqual(metrics["calendar_working_days"], 2.5)
        self.assertEqual(metrics["target_working_days"], 2.5)
        self.assertEqual(metrics["monthly_target_hours"], 22.5)


if __name__ == "__main__":
    unittest.main()

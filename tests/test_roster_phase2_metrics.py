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

    def test_half_day_leave_affect_target_no_credits_4_5(self):
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
        self.assertEqual(metrics["calendar_working_days"], 1.0)
        self.assertEqual(metrics["target_working_days"], 1.5)
        self.assertEqual(metrics["monthly_target_hours"], 13.5)


if __name__ == "__main__":
    unittest.main()

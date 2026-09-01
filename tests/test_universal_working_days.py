"""Universal Mon–Fri minus holiday ceiling for monthly target days/hours."""

import unittest
from datetime import date, timedelta

from utils.roster_helpers import (
    FULL_DAY_HOURS,
    apply_universal_working_days_cap,
    count_universal_working_days,
    generate_roster_days_for_employee,
    compute_roster_metrics,
    month_date_range,
)
from utils.roster_metrics import recalculate_metrics_from_days_and_leaves


class UniversalWorkingDaysTest(unittest.TestCase):
    def test_september_2026_is_22(self):
        start, end = month_date_range(2026, 9)
        self.assertEqual(count_universal_working_days(start, end, {}), 22)

    def test_weekday_holiday_reduces_ceiling(self):
        start, end = month_date_range(2026, 9)
        holidays = {date(2026, 9, 7): {"holiday_id": 1}}  # Monday
        self.assertEqual(count_universal_working_days(start, end, holidays), 21)

    def test_weekend_holiday_does_not_reduce_ceiling(self):
        start, end = month_date_range(2026, 9)
        holidays = {date(2026, 9, 6): {"holiday_id": 1}}  # Sunday
        self.assertEqual(count_universal_working_days(start, end, holidays), 22)

    def test_extra_saturday_working_does_not_raise_target(self):
        employee = {
            "user_id": 1,
            "role_name": "agent",
            "joining_date": date(2026, 9, 1),
        }
        start, end = month_date_range(2026, 9)
        days = generate_roster_days_for_employee(employee, start, end, {})
        for day in days:
            if day["roster_date"] == date(2026, 9, 5):  # Saturday
                day["day_type"] = "Working"
                day["working_hours"] = FULL_DAY_HOURS
        cap = count_universal_working_days(start, end, {})
        metrics = compute_roster_metrics(
            days, universal_days=cap, daily_full_hours=FULL_DAY_HOURS
        )
        self.assertGreater(metrics["calendar_working_days"], cap)
        self.assertEqual(metrics["target_working_days"], float(cap))
        self.assertEqual(metrics["monthly_target_hours"], round(cap * FULL_DAY_HOURS, 2))

    def test_leave_credit_cannot_exceed_universal(self):
        start, end = month_date_range(2026, 9)
        days = []
        d = start
        while d <= end:
            if d.weekday() < 5:
                days.append(
                    {
                        "roster_date": d,
                        "day_type": "Leave" if d == date(2026, 9, 1) else "Working",
                        "working_type": "Full",
                        "working_hours": 9.0,
                    }
                )
            else:
                days.append(
                    {
                        "roster_date": d,
                        "day_type": "WeekOff",
                        "working_type": "Full",
                        "working_hours": 9.0,
                    }
                )
            d += timedelta(days=1)
        leaves = [
            {
                "is_active": 1,
                "affect_target": 0,
                "is_half_day": 0,
                "start_date": date(2026, 9, 1),
                "end_date": date(2026, 9, 1),
            }
        ]
        metrics = recalculate_metrics_from_days_and_leaves(days, leaves)
        self.assertEqual(metrics["target_working_days"], 22.0)
        self.assertEqual(metrics["monthly_target_hours"], 198.0)

    def test_extra_weekday_weekoff_does_not_reduce_target(self):
        employee = {
            "user_id": 1,
            "role_name": "agent",
            "joining_date": date(2026, 9, 1),
        }
        start, end = month_date_range(2026, 9)
        days = generate_roster_days_for_employee(employee, start, end, {})
        for day in days:
            if day["roster_date"] == date(2026, 9, 1):  # Tuesday extra week-off
                day["day_type"] = "WeekOff"
        metrics = recalculate_metrics_from_days_and_leaves(days, [])
        self.assertEqual(metrics["calendar_working_days"], 21.0)
        self.assertEqual(metrics["target_working_days"], 22.0)
        self.assertEqual(metrics["monthly_target_hours"], 198.0)

    def test_apply_cap_scales_hours(self):
        metrics = apply_universal_working_days_cap(
            {"target_working_days": 23.0, "monthly_target_hours": 207.0},
            [],
            universal_days=22,
            daily_full_hours=9.0,
        )
        self.assertEqual(metrics["target_working_days"], 22.0)
        self.assertEqual(metrics["monthly_target_hours"], 198.0)


if __name__ == "__main__":
    unittest.main()

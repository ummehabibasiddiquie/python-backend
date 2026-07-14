"""
Verification tests for roster generation business rules (Phase 1).
Run: python -m unittest tests.test_roster_verification
"""

import unittest
from datetime import date

from utils.roster_helpers import (
    FULL_DAY_HOURS,
    HALF_DAY_HOURS,
    build_default_day,
    compute_roster_metrics,
    count_weekdays_in_range,
    derive_daily_full_hours_from_tracker,
    generate_roster_days_for_employee,
    is_holiday_on_scheduled_week_off,
    resolve_roster_period,
    working_hours_for_day,
)


class RosterScenarioVerification(unittest.TestCase):
    def setUp(self):
        self.holidays = {
            date(2026, 3, 26): {
                "holiday_id": 1,
                "holiday_name": "Republic Day",
                "holiday_date": date(2026, 3, 26),
            },
            date(2026, 3, 29): {
                "holiday_id": 2,
                "holiday_name": "Sunday Holiday Sample",
                "holiday_date": date(2026, 3, 29),
            },
        }
        self.employee = {
            "user_id": 1,
            "role_name": "agent",
            "joining_date": date(2026, 3, 1),
        }

    def test_normal_working_day(self):
        d = date(2026, 3, 2)  # Monday
        day = build_default_day(d, "agent", self.holidays)
        self.assertEqual(day["day_type"], "Working")
        self.assertEqual(day["working_type"], "Full")
        self.assertEqual(working_hours_for_day(day), FULL_DAY_HOURS)
        self.assertIsNone(day["holiday_id"])

    def test_week_off(self):
        d = date(2026, 3, 7)  # Saturday
        day = build_default_day(d, "agent", self.holidays)
        self.assertEqual(day["day_type"], "WeekOff")
        self.assertEqual(working_hours_for_day(day), 0.0)
        self.assertFalse(is_holiday_on_scheduled_week_off(day))

    def test_holiday_on_working_day(self):
        d = date(2026, 3, 26)  # Thursday holiday
        day = build_default_day(d, "agent", self.holidays)
        self.assertEqual(day["day_type"], "Holiday")
        self.assertEqual(day["holiday_id"], 1)
        self.assertEqual(working_hours_for_day(day), 0.0)

    def test_holiday_on_week_off(self):
        d = date(2026, 3, 29)  # Sunday + holiday
        day = build_default_day(d, "agent", self.holidays)
        self.assertEqual(day["day_type"], "WeekOff")
        self.assertEqual(day["holiday_id"], 2)
        self.assertTrue(is_holiday_on_scheduled_week_off(day))
        self.assertEqual(working_hours_for_day(day), 0.0)

    def test_holiday_on_week_off_does_not_double_reduce_metrics(self):
        start = date(2026, 3, 1)
        end = date(2026, 3, 31)
        days = generate_roster_days_for_employee(self.employee, start, end, self.holidays)
        metrics = compute_roster_metrics(days)

        without_sunday_holiday = generate_roster_days_for_employee(
            self.employee, start, end, {date(2026, 3, 26): self.holidays[date(2026, 3, 26)]}
        )
        metrics_without_sunday_holiday = compute_roster_metrics(without_sunday_holiday)

        self.assertEqual(
            metrics["monthly_target_hours"],
            metrics_without_sunday_holiday["monthly_target_hours"],
        )

    def test_full_day_metrics(self):
        days = [
            {
                "day_type": "Working",
                "working_type": "Full",
                "working_hours": FULL_DAY_HOURS,
            }
        ]
        metrics = compute_roster_metrics(days)
        self.assertEqual(metrics["calendar_working_days"], 1.0)
        self.assertEqual(metrics["monthly_target_hours"], FULL_DAY_HOURS)

    def test_half_day_metrics(self):
        days = [
            {
                "day_type": "Working",
                "working_type": "Half",
                "working_hours": HALF_DAY_HOURS,
            }
        ]
        metrics = compute_roster_metrics(days)
        self.assertEqual(metrics["calendar_working_days"], 1.0)
        self.assertEqual(metrics["monthly_target_hours"], HALF_DAY_HOURS)
        self.assertEqual(working_hours_for_day(days[0]), HALF_DAY_HOURS)

    def test_mixed_full_and_half_days(self):
        days = [
            {"day_type": "Working", "working_type": "Full", "working_hours": 9.0},
            {"day_type": "Working", "working_type": "Half", "working_hours": 4.5},
            {"day_type": "WeekOff", "working_type": "Full", "working_hours": 9.0},
            {"day_type": "Holiday", "working_type": "Full", "working_hours": 9.0},
        ]
        metrics = compute_roster_metrics(days)
        self.assertEqual(metrics["calendar_working_days"], 2.0)
        self.assertEqual(metrics["monthly_target_hours"], FULL_DAY_HOURS + HALF_DAY_HOURS)

    def test_tracker_daily_hours_used_on_generation(self):
        self.assertEqual(derive_daily_full_hours_from_tracker(180, 20), 9.0)
        self.assertEqual(derive_daily_full_hours_from_tracker(160, 20), 8.0)
        self.assertEqual(derive_daily_full_hours_from_tracker(None, 20), FULL_DAY_HOURS)

        day = build_default_day(date(2026, 3, 2), "agent", {}, daily_full_hours=8.0)
        self.assertEqual(day["working_hours"], 8.0)
        self.assertEqual(working_hours_for_day(day), 8.0)

    def test_mid_month_join_proration(self):
        employee = {
            **self.employee,
            "joining_date": date(2026, 3, 15),
        }
        month_start = date(2026, 3, 1)
        month_end = date(2026, 3, 31)

        roster_start, roster_end, reason = resolve_roster_period(employee, month_start, month_end)
        self.assertIsNone(reason)
        self.assertEqual(roster_start, date(2026, 3, 15))
        self.assertEqual(roster_end, month_end)

        days = generate_roster_days_for_employee(employee, roster_start, roster_end, {})
        self.assertEqual(days[0]["roster_date"], date(2026, 3, 15))
        self.assertTrue(all(d["roster_date"] >= date(2026, 3, 15) for d in days))

        baseline = count_weekdays_in_range(roster_start, roster_end)
        metrics = compute_roster_metrics(days)
        self.assertEqual(metrics["calendar_working_days"], float(baseline))

    def test_display_labels_not_used_in_metrics(self):
        days = [
            {
                "day_type": "WeekOff",
                "holiday_id": 99,
                "working_type": "Full",
                "working_hours": 9.0,
                "display_labels": ["WeekOff", "Holiday"],
            }
        ]
        metrics = compute_roster_metrics(days)
        self.assertEqual(metrics["calendar_working_days"], 0.0)
        self.assertEqual(metrics["monthly_target_hours"], 0.0)


if __name__ == "__main__":
    unittest.main()

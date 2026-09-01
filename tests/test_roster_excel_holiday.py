"""Holiday outranks Week Off; leave/half day cannot land on a holiday."""

import unittest
from datetime import date

from utils.roster_excel import (
    LABEL_AGENT_DAY,
    LABEL_HALF_DAY,
    LABEL_HOLIDAY,
    LABEL_NIGHT,
    LABEL_WEEK_OFF,
    adjust_excel_change_for_holiday,
    day_to_excel_label,
    excel_label_to_change,
)


class RosterExcelHolidayTest(unittest.TestCase):
    def test_holiday_label_roundtrip(self):
        day = {"day_type": "Holiday", "holiday_id": 9}
        self.assertEqual(day_to_excel_label(day), LABEL_HOLIDAY)
        change = excel_label_to_change(LABEL_HOLIDAY, date(2026, 9, 7))
        self.assertEqual(change["change_type"], "DAY_UPDATE")
        self.assertEqual(change["change_payload"]["day_type"], "Holiday")

    def test_weekend_holiday_shows_holiday_not_weekoff(self):
        day = {"day_type": "WeekOff", "holiday_id": 3}
        self.assertEqual(day_to_excel_label(day), LABEL_HOLIDAY)

    def test_working_on_holiday_shows_shift(self):
        day = {
            "day_type": "Working",
            "holiday_id": 3,
            "shift": "NIGHT",
            "working_type": "Full",
        }
        self.assertEqual(day_to_excel_label(day), LABEL_NIGHT)

    def test_weekoff_upload_on_holiday_stays_holiday(self):
        day = {"day_type": "Holiday", "holiday_id": 1}
        change = excel_label_to_change(LABEL_WEEK_OFF, date(2026, 9, 7))
        adjusted = adjust_excel_change_for_holiday(day, change)
        self.assertEqual(adjusted["change_payload"]["day_type"], "Holiday")

    def test_leave_on_holiday_rejected(self):
        day = {"day_type": "Holiday", "holiday_id": 1}
        change = excel_label_to_change(LABEL_HALF_DAY, date(2026, 9, 7))
        with self.assertRaises(ValueError):
            adjust_excel_change_for_holiday(day, change)

    def test_working_day_on_holiday_allowed(self):
        day = {"day_type": "Holiday", "holiday_id": 1}
        change = excel_label_to_change(LABEL_AGENT_DAY, date(2026, 9, 7))
        adjusted = adjust_excel_change_for_holiday(day, change)
        self.assertEqual(adjusted["change_payload"]["day_type"], "Working")


if __name__ == "__main__":
    unittest.main()

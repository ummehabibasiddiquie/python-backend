"""Excel half-day labels: affect target vs not."""

import unittest
from datetime import date

from utils.roster_excel import (
    LABEL_HALF_DAY,
    LABEL_HALF_DAY_AFFECT_TARGET,
    day_to_excel_label,
    excel_label_to_change,
    is_noop_change,
)


class RosterExcelHalfDayTest(unittest.TestCase):
    def test_half_day_does_not_affect_target(self):
        change = excel_label_to_change(LABEL_HALF_DAY, date(2026, 9, 1))
        self.assertEqual(change["change_type"], "LEAVE_ADD")
        self.assertEqual(change["change_payload"]["is_half_day"], 1)
        self.assertEqual(change["change_payload"]["affect_target"], 0)

    def test_half_day_affect_target(self):
        change = excel_label_to_change(LABEL_HALF_DAY_AFFECT_TARGET, date(2026, 9, 1))
        self.assertEqual(change["change_type"], "LEAVE_ADD")
        self.assertEqual(change["change_payload"]["is_half_day"], 1)
        self.assertEqual(change["change_payload"]["affect_target"], 1)

    def test_label_roundtrip_half_leave(self):
        day = {
            "day_type": "Leave",
            "working_type": "Half",
            "leave_is_half_day": 1,
            "leave_affect_target": 0,
        }
        self.assertEqual(day_to_excel_label(day), LABEL_HALF_DAY)
        day["leave_affect_target"] = 1
        self.assertEqual(day_to_excel_label(day), LABEL_HALF_DAY_AFFECT_TARGET)

    def test_noop_same_half_leave(self):
        day = {
            "day_type": "Leave",
            "shift": "DAY",
            "working_type": "Half",
            "leave_is_half_day": 1,
            "leave_affect_target": 0,
        }
        change = excel_label_to_change(LABEL_HALF_DAY, date(2026, 9, 1))
        self.assertTrue(is_noop_change(day, change))
        affect = excel_label_to_change(LABEL_HALF_DAY_AFFECT_TARGET, date(2026, 9, 1))
        self.assertFalse(is_noop_change(day, affect))


if __name__ == "__main__":
    unittest.main()

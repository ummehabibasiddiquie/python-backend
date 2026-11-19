"""Excel leave/half-day labels: roster vs unrostered, plus affect target."""

import unittest
from datetime import date

from utils.roster_excel import (
    LABEL_HALF_DAY,
    LABEL_HALF_DAY_AFFECT_TARGET,
    LABEL_HALF_DAY_ROSTER,
    LABEL_HALF_DAY_ROSTER_AFFECT,
    LABEL_HALF_DAY_UNROSTER_AFFECT,
    LABEL_HALF_DAY_UNROSTERED,
    LABEL_LEAVE_AFFECT_TARGET,
    LABEL_LEAVE_ROSTER,
    LABEL_LEAVE_ROSTER_AFFECT,
    LABEL_LEAVE_UNROSTER_AFFECT,
    LABEL_LEAVE_UNROSTERED,
    day_to_excel_label,
    excel_label_to_change,
    is_noop_change,
)


class RosterExcelLeaveComboTest(unittest.TestCase):
    def _flags(self, label):
        p = excel_label_to_change(label, date(2026, 9, 1))["change_payload"]
        return int(p["is_half_day"]), int(p["is_rostered"]), int(p["affect_target"])

    def test_leave_combos(self):
        self.assertEqual(self._flags(LABEL_LEAVE_ROSTER), (0, 1, 0))
        self.assertEqual(self._flags(LABEL_LEAVE_ROSTER_AFFECT), (0, 1, 1))
        self.assertEqual(self._flags(LABEL_LEAVE_UNROSTERED), (0, 0, 0))
        # Affect target implies it was planned, so this becomes rostered + affect.
        self.assertEqual(self._flags(LABEL_LEAVE_UNROSTER_AFFECT), (0, 1, 1))

    def test_half_day_combos(self):
        self.assertEqual(self._flags(LABEL_HALF_DAY_ROSTER), (1, 1, 0))
        self.assertEqual(self._flags(LABEL_HALF_DAY_ROSTER_AFFECT), (1, 1, 1))
        self.assertEqual(self._flags(LABEL_HALF_DAY_UNROSTERED), (1, 0, 0))
        self.assertEqual(self._flags(LABEL_HALF_DAY_UNROSTER_AFFECT), (1, 1, 1))

    def test_legacy_labels_still_parse(self):
        self.assertEqual(self._flags(LABEL_LEAVE_AFFECT_TARGET), (0, 1, 1))
        self.assertEqual(self._flags(LABEL_HALF_DAY), (1, 1, 0))
        self.assertEqual(self._flags(LABEL_HALF_DAY_AFFECT_TARGET), (1, 1, 1))

    def test_label_roundtrip(self):
        cases = [
            ({"leave_is_rostered": 1, "leave_affect_target": 0}, LABEL_LEAVE_ROSTER),
            ({"leave_is_rostered": 1, "leave_affect_target": 1}, LABEL_LEAVE_ROSTER_AFFECT),
            ({"leave_is_rostered": 0, "leave_affect_target": 0}, LABEL_LEAVE_UNROSTERED),
            ({"leave_is_rostered": 0, "leave_affect_target": 1}, LABEL_LEAVE_ROSTER_AFFECT),
        ]
        for extra, expected in cases:
            day = {"day_type": "Leave", "working_type": "Full", **extra}
            self.assertEqual(day_to_excel_label(day), expected)

    def test_half_leave_roundtrip(self):
        day = {
            "day_type": "Leave",
            "working_type": "Half",
            "leave_is_half_day": 1,
            "leave_is_rostered": 0,
            "leave_affect_target": 1,
        }
        self.assertEqual(day_to_excel_label(day), LABEL_HALF_DAY_ROSTER_AFFECT)
        day["leave_is_rostered"] = 1
        day["leave_affect_target"] = 0
        self.assertEqual(day_to_excel_label(day), LABEL_HALF_DAY_ROSTER)

    def test_noop_same_half_leave(self):
        day = {
            "day_type": "Leave",
            "shift": "DAY",
            "working_type": "Half",
            "leave_is_half_day": 1,
            "leave_is_rostered": 1,
            "leave_affect_target": 0,
        }
        change = excel_label_to_change(LABEL_HALF_DAY_ROSTER, date(2026, 9, 1))
        self.assertTrue(is_noop_change(day, change))
        affect = excel_label_to_change(LABEL_HALF_DAY_ROSTER_AFFECT, date(2026, 9, 1))
        self.assertFalse(is_noop_change(day, affect))
        unroster = excel_label_to_change(LABEL_HALF_DAY_UNROSTERED, date(2026, 9, 1))
        self.assertFalse(is_noop_change(day, unroster))


if __name__ == "__main__":
    unittest.main()

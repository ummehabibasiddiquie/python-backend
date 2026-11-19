from datetime import date
import unittest

from update_agent_tenure import (
    add_months,
    expected_tenure,
    first_of_next_month,
    parse_id_list,
    service_duration_label,
)


class TenureScheduleTest(unittest.TestCase):
    def test_mid_month_join(self):
        joining = date(2024, 10, 15)
        self.assertEqual(add_months(joining, 13), date(2025, 11, 15))
        self.assertEqual(first_of_next_month(date(2025, 11, 15)), date(2025, 12, 1))
        self.assertEqual(expected_tenure(joining, date(2025, 11, 30)), 1.0)
        self.assertEqual(expected_tenure(joining, date(2025, 12, 1)), 1.15)
        self.assertEqual(expected_tenure(joining, date(2026, 11, 30)), 1.15)
        self.assertEqual(expected_tenure(joining, date(2026, 12, 1)), 1.25)
        self.assertEqual(expected_tenure(joining, date(2027, 12, 1)), 1.35)
        self.assertEqual(expected_tenure(joining, date(2028, 12, 1)), 1.45)

    def test_first_of_month_join(self):
        joining = date(2024, 10, 1)
        # +13 months = 2025-11-01, change 1st of next month = 2025-12-01
        self.assertEqual(expected_tenure(joining, date(2025, 11, 1)), 1.0)
        self.assertEqual(expected_tenure(joining, date(2025, 12, 1)), 1.15)

    def test_service_duration_label(self):
        joining = date(2024, 10, 15)
        self.assertEqual(service_duration_label(joining, date(2024, 10, 20)), "less than 1 month")
        self.assertEqual(service_duration_label(joining, date(2025, 11, 15)), "1 year 1 month")
        self.assertEqual(service_duration_label(joining, date(2026, 10, 15)), "2 years")

    def test_parse_id_list(self):
        self.assertEqual(parse_id_list("[3, 4]"), [3, 4])
        self.assertEqual(parse_id_list("12"), [12])
        self.assertEqual(parse_id_list(None), [])


if __name__ == "__main__":
    unittest.main()

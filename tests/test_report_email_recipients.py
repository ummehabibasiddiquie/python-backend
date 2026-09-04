import unittest

from report_email_recipients import (
    is_valid_email,
    lists_from_rows,
    normalize_email,
    normalize_type,
)


class TestReportEmailHelpers(unittest.TestCase):
    def test_normalize_email(self):
        self.assertEqual(normalize_email("  A@B.com "), "a@b.com")
        self.assertEqual(normalize_email("Same.User@TransformSolution.net"), "same.user@transformsolution.net")

    def test_valid_email(self):
        self.assertTrue(is_valid_email("user@transformsolution.net"))
        self.assertFalse(is_valid_email("not-an-email"))
        self.assertFalse(is_valid_email(""))

    def test_lists_from_rows(self):
        to_list, cc_list = lists_from_rows(
            [
                {"email": "a@x.com", "recipient_type": "to"},
                {"email": "b@x.com", "recipient_type": "cc"},
                {"email": "A@x.com", "recipient_type": "to"},
            ]
        )
        self.assertEqual(to_list, ["a@x.com"])
        self.assertEqual(cc_list, ["b@x.com"])

    def test_seema_billable_only(self):
        rows = [
            {
                "email": "seema@transformsolution.com",
                "recipient_type": "cc",
                "send_billable": 1,
                "send_tracker": 0,
                "send_tracker_full": 0,
            },
            {
                "email": "ashfaq@transformsolution.com",
                "recipient_type": "cc",
                "send_billable": 1,
                "send_tracker": 1,
                "send_tracker_full": 1,
            },
        ]
        _, billable_cc = lists_from_rows(rows, "billable")
        _, tracker_cc = lists_from_rows(rows, "tracker")
        _, full_cc = lists_from_rows(rows, "tracker_full")
        self.assertIn("seema@transformsolution.com", billable_cc)
        self.assertNotIn("seema@transformsolution.com", tracker_cc)
        self.assertNotIn("seema@transformsolution.com", full_cc)
        self.assertIn("ashfaq@transformsolution.com", tracker_cc)

    def test_empty_db_rows_return_empty_lists(self):
        to_list, cc_list = lists_from_rows([], "billable")
        self.assertEqual(to_list, [])
        self.assertEqual(cc_list, [])


if __name__ == "__main__":
    unittest.main()

import unittest

from utils.qc_auto_score import is_manual_qc_only_day, should_auto_qc_100


class TestShouldAutoQc100(unittest.TestCase):
    def test_zero_production_no_file(self):
        self.assertTrue(
            should_auto_qc_100(tracker_count=1, total_production=0, file_count=0)
        )
        self.assertTrue(
            should_auto_qc_100(tracker_count=2, total_production=0.0, file_count=0)
        )

    def test_has_production(self):
        self.assertFalse(
            should_auto_qc_100(tracker_count=1, total_production=10, file_count=0)
        )

    def test_has_file(self):
        self.assertFalse(
            should_auto_qc_100(tracker_count=1, total_production=0, file_count=1)
        )

    def test_no_trackers(self):
        self.assertFalse(
            should_auto_qc_100(tracker_count=0, total_production=0, file_count=0)
        )


class TestManualQcOnlyDay(unittest.TestCase):
    def test_only_manual_projects(self):
        self.assertTrue(
            is_manual_qc_only_day(tracker_count=1, other_project_count=0)
        )
        self.assertTrue(
            is_manual_qc_only_day(tracker_count=3, other_project_count=0)
        )

    def test_mixed_projects(self):
        self.assertFalse(
            is_manual_qc_only_day(tracker_count=2, other_project_count=1)
        )

    def test_no_trackers(self):
        self.assertFalse(
            is_manual_qc_only_day(tracker_count=0, other_project_count=0)
        )


if __name__ == "__main__":
    unittest.main()

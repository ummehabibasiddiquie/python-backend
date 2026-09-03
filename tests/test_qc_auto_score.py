import unittest

from utils.qc_auto_score import (
    AUTO_QC_DAYS_SQL,
    AUTO_QC_EFFECTIVE_FROM_SQL,
    MANUAL_QC_DAYS_SQL,
    day_allows_manual_qc_from_stats,
    is_manual_qc_only_day,
    should_auto_qc_100,
)


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


class TestAutoQcSqlIsPastDaysOnly(unittest.TestCase):
    def test_sql_excludes_today(self):
        self.assertIn("< CURDATE()", AUTO_QC_DAYS_SQL)

    def test_sql_starts_from_effective_date(self):
        self.assertIn(AUTO_QC_EFFECTIVE_FROM_SQL, AUTO_QC_DAYS_SQL)

    def test_manual_sql_includes_any_no_file_day(self):
        self.assertIn("tracker_file", MANUAL_QC_DAYS_SQL)


class TestDayAllowsManualQcFromStats(unittest.TestCase):
    def test_training_sample_only(self):
        self.assertTrue(
            day_allows_manual_qc_from_stats(
                tracker_count=1,
                other_project_count=0,
                file_count=0,
                total_production=0,
                work_date="2026-09-10",
            )
        )

    def test_past_no_file_day(self):
        self.assertTrue(
            day_allows_manual_qc_from_stats(
                tracker_count=1,
                other_project_count=1,
                file_count=0,
                total_production=0,
                work_date="2026-09-02",
            )
        )

    def test_any_project_no_file_allows_manual(self):
        self.assertTrue(
            day_allows_manual_qc_from_stats(
                tracker_count=1,
                other_project_count=1,
                file_count=0,
                total_production=0,
                work_date="2026-09-03",
            )
        )

    def test_production_no_file(self):
        self.assertTrue(
            day_allows_manual_qc_from_stats(
                tracker_count=1,
                other_project_count=1,
                file_count=0,
                total_production=5,
                work_date="2026-09-10",
            )
        )

    def test_has_file_blocks_manual(self):
        self.assertFalse(
            day_allows_manual_qc_from_stats(
                tracker_count=1,
                other_project_count=1,
                file_count=1,
                total_production=0,
                work_date="2026-09-02",
            )
        )


if __name__ == "__main__":
    unittest.main()

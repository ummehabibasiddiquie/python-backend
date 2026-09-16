-- QA Hours report go-live: 16 Sep 2026.
-- Remove tracker rows before today so Daily, Monthly, and Tracker start from today.

DELETE FROM qa_work_tracker
WHERE work_date < '2026-09-16';

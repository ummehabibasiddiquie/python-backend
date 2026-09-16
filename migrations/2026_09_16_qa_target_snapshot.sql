-- Freeze the QA target used when a QC row was first stored.
-- Later task-target edits must not rewrite past days.

ALTER TABLE qa_work_tracker
  ADD COLUMN target_snapshot JSON NULL AFTER hours;

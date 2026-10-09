-- Reset QC records for Tracker 45092 (Allow Re-Fill)
-- Reference: docs/reset-qc-for-tracker.md

-- STEP 1: Verify the records before deletion
SELECT id, tracker_id, qa_user_id, agent_id, qc_score, status, qc_status, created_at, updated_at
FROM qc_records
WHERE tracker_id = 45092;

SELECT tracker_id, user_id, project_id, task_id, qc_status, tracker_file, date_time
FROM task_work_tracker
WHERE tracker_id = 45092;

-- STEP 2: Delete QC records and reset tracker in a safe transaction
START TRANSACTION;

-- 1. Delete audit rows (no FK cascade)
DELETE qa
FROM qc_audit qa
INNER JOIN qc_records qr ON qa.qc_record_id = qr.id
WHERE qr.tracker_id = 45092;

-- 2. Delete rework history rows
DELETE rh
FROM qc_rework_history rh
INNER JOIN qc_records qr ON rh.qc_record_id = qr.id
WHERE qr.tracker_id = 45092;

-- 3. Delete correction history rows
DELETE ch
FROM qc_correction_history ch
INNER JOIN qc_records qr ON ch.qc_record_id = qr.id
WHERE qr.tracker_id = 45092;

-- 4. Delete QC record
DELETE FROM qc_records
WHERE tracker_id = 45092;

-- 5. Reopen tracker for QC (tracker is preserved, status reset to pending)
UPDATE task_work_tracker
SET qc_status = 0
WHERE tracker_id = 45092;

COMMIT;

-- STEP 3: Verify results
SELECT * FROM qc_records WHERE tracker_id = 45092;
-- Expected: Empty set

SELECT tracker_id, qc_status
FROM task_work_tracker
WHERE tracker_id = 45092;
-- Expected: tracker_id 45092, qc_status = 0

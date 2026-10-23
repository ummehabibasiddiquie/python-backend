# Reset QC for a Tracker (Allow Re-Fill)

Use this when a tracker’s QC form must be filled again.

**Do not delete the tracker.** Only delete QC-related rows and set `qc_status = 0`. The tracker file (`tracker_file`) stays as it is.

---

## When to use

- Wrong QC agent filled the form
- QC was submitted by mistake
- Tracker should appear as **QC pending** again so QA can open the form

---

## What gets deleted / kept

| Action | Table / field | Notes |
|--------|----------------|-------|
| Delete | `qc_audit` | Linked to the QC record |
| Delete | `qc_rework_history` | Rework cycles for that QC |
| Delete | `qc_correction_history` | Correction cycles for that QC |
| Delete | `qc_records` | Main QC result for the tracker |
| Keep + reset | `task_work_tracker` | Tracker stays; set `qc_status = 0` |
| Keep | File on Cloudinary / `tracker_file` | Never remove the agent’s uploaded file |

Replace `TRACKER_ID` with the real id (examples used before: `39349`, `48222`, `48567`).

---

## Method 1 — Live DB (phpMyAdmin / MySQL) — preferred for production

Run this on the **live** database only. Local DB often does not have the same tracker ids.

### 1. Confirm the tracker and QC rows

```sql
SELECT tracker_id, user_id, project_id, task_id, qc_status, tracker_file, date_time
FROM task_work_tracker
WHERE tracker_id = TRACKER_ID;

SELECT id, tracker_id, qa_user_id, agent_id, qc_score, status, qc_status, created_at, updated_at
FROM qc_records
WHERE tracker_id = TRACKER_ID;
```

If the tracker row is missing, stop and check the id.

Optional related rows (use `id` from `qc_records` as `QC_RECORD_ID`):

```sql
SELECT * FROM qc_audit WHERE qc_record_id = QC_RECORD_ID;
SELECT * FROM qc_rework_history WHERE qc_record_id = QC_RECORD_ID;
SELECT * FROM qc_correction_history WHERE qc_record_id = QC_RECORD_ID;
```

### 2. Delete QC data and reopen the tracker

```sql
START TRANSACTION;

DELETE qa
FROM qc_audit qa
INNER JOIN qc_records qr ON qa.qc_record_id = qr.id
WHERE qr.tracker_id = TRACKER_ID;

DELETE rh
FROM qc_rework_history rh
INNER JOIN qc_records qr ON rh.qc_record_id = qr.id
WHERE qr.tracker_id = TRACKER_ID;

DELETE ch
FROM qc_correction_history ch
INNER JOIN qc_records qr ON ch.qc_record_id = qr.id
WHERE qr.tracker_id = TRACKER_ID;

DELETE FROM qc_records
WHERE tracker_id = TRACKER_ID;

UPDATE task_work_tracker
SET qc_status = 0
WHERE tracker_id = TRACKER_ID;

COMMIT;
```

`0 rows affected` on audit / rework / correction is normal when none exist.

If something looks wrong before `COMMIT`, run `ROLLBACK;` instead.

### 3. Verify

```sql
SELECT * FROM qc_records WHERE tracker_id = TRACKER_ID;
-- Expected: empty

SELECT tracker_id, qc_status, tracker_file
FROM task_work_tracker
WHERE tracker_id = TRACKER_ID;
-- Expected: tracker still present, qc_status = 0, tracker_file unchanged
```

### 4. After cleanup

Ask the QC agent to **refresh** the QC list. The tracker should show as pending so they can fill the form again.

---

## Method 2 — Python script (local or any MySQL you can reach)

Script path: `backend-api/scripts/reset_qc_tracker.py`

From the `backend-api` folder:

```bash
# Inspect only (no deletes)
python scripts/reset_qc_tracker.py --tracker-id TRACKER_ID --dry-run

# Apply reset (uses .env DB_* by default — usually localhost)
python scripts/reset_qc_tracker.py --tracker-id TRACKER_ID
```

Against another host (only if you have credentials and approval):

```bash
python scripts/reset_qc_tracker.py --tracker-id TRACKER_ID --host HOST --user USER --database DB_NAME --dry-run
python scripts/reset_qc_tracker.py --tracker-id TRACKER_ID --host HOST --user USER --database DB_NAME
```

The script deletes the same four QC-related sets of rows and sets `qc_status = 0`. It does **not** delete the tracker.

**Note:** If dry-run says the tracker was not found, you are on the wrong database (often local while the id only exists on live). Use Method 1 on live instead.

---

## Alternate: API (incomplete alone — do not use by itself)

```http
DELETE /api/v1/qc-records/delete/:id
```

This only deletes from `qc_records`. You must still clear related history if needed and reset:

```sql
UPDATE task_work_tracker SET qc_status = 0 WHERE tracker_id = TRACKER_ID;
```

Prefer Method 1 (full SQL) for a complete reset.

---

## Safety checklist

- [ ] Confirmed correct `tracker_id`
- [ ] Confirmed you are on the correct database (live vs local)
- [ ] Confirmed `qc_records` for that tracker before delete
- [ ] **Not** running `DELETE FROM task_work_tracker`
- [ ] **Not** deleting Cloudinary / tracker files
- [ ] Ran verify queries after cleanup
- [ ] QC agent refreshed the UI

---

## Rollback note

There is no automatic restore. Wrong deletes cannot be recovered without a DB backup. Always confirm `tracker_id` (and run dry-run / SELECTs) before `COMMIT`.

---

## Worked examples

### Tracker 39349 (26 Aug 2026)

| Check | Result |
|-------|--------|
| `qc_records` | id `5377`, status `rework`, score `95.00` |
| `task_work_tracker.qc_status` | `1` before reset |
| `qc_audit` delete | 0 rows |
| `qc_rework_history` delete | 1 row |
| `qc_correction_history` delete | 0 rows |
| `qc_records` delete | 1 row |
| Tracker after | still `39349`, `qc_status = 0` |

### Trackers 48222 / 48567

These ids were requested for live reset. They were **not** present on the local `tfs_hrms` database, so SQL Method 1 was used on live. After reset, QA can fill those trackers again.

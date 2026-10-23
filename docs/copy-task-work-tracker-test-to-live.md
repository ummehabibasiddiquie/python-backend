# Copy `mytfs_test.task_work_tracker` → `mytfs.task_work_tracker`

Use this when you want **live (`mytfs`)** to match **test (`mytfs_test`)** exactly for tracker rows.

## Before you run anything

1. **Backup live first** (required).
2. Run during a **quiet window** — apps using `mytfs` will read old data until copy finishes.
3. If `mytfs` has **QC / rework rows** linked by `tracker_id`, replacing trackers can leave orphan QC records. Check step 2 below.
4. Confirm **both tables have the same columns** (step 1).

---

## Step 1 — Compare schema and row counts

```sql
SHOW CREATE TABLE mytfs_test.task_work_tracker\G
SHOW CREATE TABLE mytfs.task_work_tracker\G

SELECT 'mytfs_test' AS db, COUNT(*) AS rows FROM mytfs_test.task_work_tracker
UNION ALL
SELECT 'mytfs', COUNT(*) FROM mytfs.task_work_tracker;
```

If `SHOW CREATE TABLE` differs, align schemas first (see `backend-api/table changes List.txt` and migrations).

---

## Step 2 — Optional: QC rows linked to trackers (live DB)

```sql
-- Example: adjust table name if your QC schema differs
SELECT COUNT(*) AS qc_rows_on_live
FROM mytfs.qc_records qr
WHERE qr.tracker_id IS NOT NULL
  AND qr.tracker_id NOT IN (SELECT tracker_id FROM mytfs_test.task_work_tracker);
```

If this count is > 0, full replace may break QC links. Resolve or accept before truncating live.

---

## Step 3 — Backup live table

```sql
DROP TABLE IF EXISTS mytfs.task_work_tracker_backup;
CREATE TABLE mytfs.task_work_tracker_backup AS
SELECT * FROM mytfs.task_work_tracker;

SELECT COUNT(*) AS backed_up_rows FROM mytfs.task_work_tracker_backup;
```

---

## Step 4 — Full copy (live becomes identical to test)

```sql
SET FOREIGN_KEY_CHECKS = 0;

TRUNCATE TABLE mytfs.task_work_tracker;

INSERT INTO mytfs.task_work_tracker (
  tracker_id,
  project_id,
  task_id,
  user_id,
  date_time,
  production,
  tenure_target,
  actual_target,
  billable_hours,
  actual_billable_hours,
  tracker_file,
  tracker_note,
  shift,
  qc_status,
  is_active,
  updated_date
)
SELECT
  tracker_id,
  project_id,
  task_id,
  user_id,
  date_time,
  production,
  tenure_target,
  actual_target,
  billable_hours,
  actual_billable_hours,
  tracker_file,
  tracker_note,
  shift,
  qc_status,
  is_active,
  updated_date
FROM mytfs_test.task_work_tracker;

SET @next_ai = (SELECT IFNULL(MAX(tracker_id), 0) + 1 FROM mytfs.task_work_tracker);
SET @sql = CONCAT('ALTER TABLE mytfs.task_work_tracker AUTO_INCREMENT = ', @next_ai);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET FOREIGN_KEY_CHECKS = 1;
```

> If test has a column that live does not (or vice versa), remove/add that column in the `INSERT ... SELECT` list after fixing schema.

---

## Step 5 — Verify

```sql
SELECT 'mytfs_test' AS db, COUNT(*) AS rows FROM mytfs_test.task_work_tracker
UNION ALL
SELECT 'mytfs', COUNT(*) FROM mytfs.task_work_tracker;

-- Should return 0 rows if counts match and IDs align
SELECT t.tracker_id
FROM mytfs_test.task_work_tracker t
LEFT JOIN mytfs.task_work_tracker l ON l.tracker_id = t.tracker_id
WHERE l.tracker_id IS NULL
LIMIT 10;
```

---

## Alternative: mysqldump (same server)

```bash
# Backup live
mysqldump -u USER -p mytfs task_work_tracker > mytfs_task_work_tracker_backup.sql

# Export test data only (no CREATE TABLE)
mysqldump -u USER -p mytfs_test task_work_tracker --no-create-info > test_task_work_tracker_data.sql

# Replace live data
mysql -u USER -p mytfs -e "SET FOREIGN_KEY_CHECKS=0; TRUNCATE task_work_tracker; SET FOREIGN_KEY_CHECKS=1;"
mysql -u USER -p mytfs < test_task_work_tracker_data.sql
```

---

## Rollback (if something goes wrong)

```sql
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE mytfs.task_work_tracker;
INSERT INTO mytfs.task_work_tracker SELECT * FROM mytfs.task_work_tracker_backup;
SET FOREIGN_KEY_CHECKS = 1;
```

---

## Table columns (reference)

| Column | Type |
|--------|------|
| tracker_id | INT PK, AUTO_INCREMENT |
| project_id | INT |
| task_id | INT |
| user_id | INT |
| date_time | TIMESTAMP |
| production | DOUBLE |
| tenure_target | TEXT |
| actual_target | TEXT |
| billable_hours | TEXT |
| actual_billable_hours | TEXT |
| tracker_file | LONGTEXT |
| tracker_note | LONGTEXT |
| shift | ENUM('DAY','NIGHT') |
| qc_status | INT |
| is_active | INT |
| updated_date | TIMESTAMP |

-- Company joining date (org DOJ). Separate from tfs_user.joining_date (Tracker Joining Date).
-- Used for tenure auto-update.
-- Hostinger MySQL does not support ADD COLUMN IF NOT EXISTS.
-- Check first:  SHOW COLUMNS FROM tfs_user LIKE 'company_joining_date';
-- If that returns no row, run the ALTER below. If the column exists, skip it.

ALTER TABLE `tfs_user`
ADD COLUMN `company_joining_date` DATE NULL AFTER `joining_date`;

-- Old joining_date values are the company DOJ. Copy them into company_joining_date.
-- Keep joining_date as Tracker Joining Date (same column name in code/roster).
UPDATE `tfs_user`
SET `company_joining_date` = `joining_date`
WHERE `company_joining_date` IS NULL
  AND `joining_date` IS NOT NULL;

-- QC / Agent Files and QA Agent Audit as per-user flags.
-- Only the QA role keeps these by default. Admin, PM, ATL, AM need the toggle.
-- Hostinger MySQL does not support ADD COLUMN IF NOT EXISTS.
-- Check first, then ALTER only if the column is missing:
--   SHOW COLUMNS FROM user_permission LIKE 'qc_permission';
--   SHOW COLUMNS FROM user_permission LIKE 'audit_permission';
--   SHOW COLUMNS FROM user_permission LIKE 'qc_overview_permission';

ALTER TABLE `user_permission`
ADD COLUMN `qc_permission` INT NOT NULL DEFAULT 0 AFTER `user_creation_permission`;

ALTER TABLE `user_permission`
ADD COLUMN `audit_permission` INT NOT NULL DEFAULT 0 AFTER `qc_permission`;

ALTER TABLE `user_permission`
ADD COLUMN `qc_overview_permission` INT NOT NULL DEFAULT 0 AFTER `audit_permission`;

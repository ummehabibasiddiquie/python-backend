-- Roster Management Module - Phase 2
-- Versioning, approval workflow extensions, reviewer comments.

-- ---------------------------------------------------------------------------
-- roster_month: versioning and workflow metadata
-- ---------------------------------------------------------------------------
ALTER TABLE `roster_month`
  ADD COLUMN `roster_version` INT NOT NULL DEFAULT 1 AFTER `status`,
  ADD COLUMN `submitted_by` INT NULL AFTER `approved_date`,
  ADD COLUMN `submitted_date` DATETIME NULL AFTER `submitted_by`,
  ADD COLUMN `locked_by` INT NULL AFTER `submitted_date`,
  ADD COLUMN `locked_date` DATETIME NULL AFTER `locked_by`,
  ADD COLUMN `production_synced_at` DATETIME NULL AFTER `locked_date`,
  ADD COLUMN `last_approved_by` INT NULL AFTER `production_synced_at`,
  ADD COLUMN `last_approved_date` DATETIME NULL AFTER `last_approved_by`;

-- ---------------------------------------------------------------------------
-- roster_version_snapshot: immutable approved versions
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `roster_version_snapshot` (
  `version_id` INT NOT NULL AUTO_INCREMENT,
  `roster_month_id` INT NOT NULL,
  `roster_version` INT NOT NULL,
  `snapshot_json` JSON NOT NULL,
  `approved_by` INT NOT NULL,
  `approved_date` DATETIME NOT NULL,
  `reviewer_comment` TEXT,
  `production_synced_at` DATETIME NULL,
  `created_date` DATETIME NOT NULL,
  PRIMARY KEY (`version_id`),
  UNIQUE KEY `uk_roster_month_version` (`roster_month_id`, `roster_version`),
  CONSTRAINT `fk_roster_version_month` FOREIGN KEY (`roster_month_id`) REFERENCES `roster_month` (`roster_month_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ---------------------------------------------------------------------------
-- roster_change_request: batch workflow + reviewer comments
-- ---------------------------------------------------------------------------
ALTER TABLE `roster_change_request`
  ADD COLUMN `batch_id` VARCHAR(64) NULL AFTER `change_payload`,
  ADD COLUMN `reviewer_comment` TEXT NULL AFTER `rejection_reason`,
  ADD COLUMN `applied_at` DATETIME NULL AFTER `reviewer_comment`,
  ADD COLUMN `roster_version_applied` INT NULL AFTER `applied_at`;

ALTER TABLE `roster_change_request`
  MODIFY COLUMN `status` ENUM(
    'Pending',
    'Approved',
    'Rejected',
    'Cancelled due to Regeneration',
    'Cancelled due to Withdrawal'
  ) NOT NULL DEFAULT 'Pending';

ALTER TABLE `roster_change_request`
  ADD KEY `idx_roster_change_batch` (`batch_id`, `status`);

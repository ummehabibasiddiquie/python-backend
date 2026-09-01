-- Additive roster schema for LIVE tfs_hrms.
-- Does NOT drop tables or overwrite users/projects/trackers.
-- Skip any statement that fails because the object already exists.
-- Prefer: python scripts/sync_roster_schema.py  (idempotent).

-- 1) Existing users: joining date only (nullable). Do not update rows.
--    Run only if SHOW COLUMNS FROM tfs_user LIKE 'joining_date' is empty.
-- ALTER TABLE tfs_user ADD COLUMN joining_date DATE NULL AFTER created_date;
-- ALTER TABLE tfs_user ADD COLUMN deactivated_at DATETIME NULL;

CREATE TABLE IF NOT EXISTS `org_holiday` (
  `holiday_id` INT NOT NULL AUTO_INCREMENT,
  `holiday_date` DATE NOT NULL,
  `holiday_name` VARCHAR(255) NOT NULL,
  `calendar_year` INT NOT NULL,
  `is_active` TINYINT NOT NULL DEFAULT 1,
  `created_by` INT DEFAULT NULL,
  `created_date` DATETIME NOT NULL,
  `updated_date` DATETIME NOT NULL,
  PRIMARY KEY (`holiday_id`),
  UNIQUE KEY `uk_org_holiday_date_year` (`holiday_date`, `calendar_year`),
  KEY `idx_org_holiday_year_active` (`calendar_year`, `is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `roster_month` (
  `roster_month_id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL,
  `month_year` VARCHAR(20) NOT NULL,
  `status` ENUM('Draft','Pending Approval','Approved','Locked') NOT NULL DEFAULT 'Draft',
  `roster_version` INT NOT NULL DEFAULT 1,
  `roster_start_date` DATE NOT NULL,
  `roster_end_date` DATE NOT NULL,
  `baseline_target_days` DECIMAL(10,2) NOT NULL DEFAULT 0,
  `calendar_working_days` DECIMAL(10,2) NOT NULL DEFAULT 0,
  `target_working_days` DECIMAL(10,2) NOT NULL DEFAULT 0,
  `monthly_target_hours` DECIMAL(10,2) NOT NULL DEFAULT 0,
  `extra_assigned_hours` DECIMAL(10,2) NOT NULL DEFAULT 0,
  `is_active` TINYINT NOT NULL DEFAULT 1,
  `created_by` INT DEFAULT NULL,
  `created_date` DATETIME NOT NULL,
  `approved_by` INT DEFAULT NULL,
  `approved_date` DATETIME DEFAULT NULL,
  `submitted_by` INT NULL,
  `submitted_date` DATETIME NULL,
  `locked_by` INT NULL,
  `locked_date` DATETIME NULL,
  `production_synced_at` DATETIME NULL,
  `last_approved_by` INT NULL,
  `last_approved_date` DATETIME NULL,
  `updated_date` DATETIME NOT NULL,
  PRIMARY KEY (`roster_month_id`),
  KEY `idx_roster_month_user` (`user_id`, `month_year`, `is_active`),
  KEY `idx_roster_month_status` (`month_year`, `status`, `is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `roster_day` (
  `roster_day_id` INT NOT NULL AUTO_INCREMENT,
  `roster_month_id` INT NOT NULL,
  `roster_date` DATE NOT NULL,
  `day_type` ENUM('Working','WeekOff','Holiday','Leave','PreJoin','Left') NOT NULL DEFAULT 'Working',
  `shift` ENUM('DAY','NIGHT') NOT NULL DEFAULT 'DAY',
  `shift_start` TIME DEFAULT NULL,
  `shift_end` TIME DEFAULT NULL,
  `working_type` ENUM('Full','Half') NOT NULL DEFAULT 'Full',
  `working_hours` DECIMAL(4,2) NOT NULL DEFAULT 9.00,
  `holiday_id` INT DEFAULT NULL,
  `leave_id` INT DEFAULT NULL,
  `is_active` TINYINT NOT NULL DEFAULT 1,
  `created_date` DATETIME NOT NULL,
  `updated_date` DATETIME NOT NULL,
  PRIMARY KEY (`roster_day_id`),
  UNIQUE KEY `uk_roster_day_month_date` (`roster_month_id`, `roster_date`),
  KEY `idx_roster_day_date` (`roster_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `roster_leave` (
  `leave_id` INT NOT NULL AUTO_INCREMENT,
  `roster_month_id` INT NOT NULL,
  `leave_type` VARCHAR(100) NOT NULL,
  `start_date` DATE NOT NULL,
  `end_date` DATE NOT NULL,
  `reason` TEXT,
  `is_rostered` TINYINT NOT NULL DEFAULT 1,
  `affect_target` TINYINT NOT NULL DEFAULT 0,
  `is_half_day` TINYINT NOT NULL DEFAULT 0,
  `is_active` TINYINT NOT NULL DEFAULT 1,
  `created_by` INT DEFAULT NULL,
  `created_date` DATETIME NOT NULL,
  `updated_date` DATETIME NOT NULL,
  PRIMARY KEY (`leave_id`),
  KEY `idx_roster_leave_month` (`roster_month_id`, `is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `roster_change_request` (
  `request_id` INT NOT NULL AUTO_INCREMENT,
  `roster_month_id` INT NOT NULL,
  `user_id` INT NOT NULL,
  `change_type` VARCHAR(50) NOT NULL,
  `change_payload` JSON NOT NULL,
  `batch_id` VARCHAR(64) NULL,
  `status` ENUM(
    'Pending','Approved','Rejected',
    'Cancelled due to Regeneration',
    'Cancelled due to Withdrawal'
  ) NOT NULL DEFAULT 'Pending',
  `submitted_by` INT NOT NULL,
  `submitted_date` DATETIME NOT NULL,
  `reviewed_by` INT DEFAULT NULL,
  `reviewed_date` DATETIME DEFAULT NULL,
  `rejection_reason` TEXT,
  `reviewer_comment` TEXT NULL,
  `applied_at` DATETIME NULL,
  `roster_version_applied` INT NULL,
  `is_active` TINYINT NOT NULL DEFAULT 1,
  PRIMARY KEY (`request_id`),
  KEY `idx_roster_change_month_status` (`roster_month_id`, `status`),
  KEY `idx_roster_change_batch` (`batch_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `roster_audit_log` (
  `audit_id` INT NOT NULL AUTO_INCREMENT,
  `roster_month_id` INT DEFAULT NULL,
  `user_id` INT DEFAULT NULL,
  `action` VARCHAR(100) NOT NULL,
  `entity_type` VARCHAR(50) NOT NULL,
  `entity_id` INT DEFAULT NULL,
  `old_value` JSON DEFAULT NULL,
  `new_value` JSON DEFAULT NULL,
  `performed_by` INT NOT NULL,
  `performed_date` DATETIME NOT NULL,
  `approval_status` VARCHAR(50) DEFAULT NULL,
  `notes` TEXT,
  PRIMARY KEY (`audit_id`),
  KEY `idx_roster_audit_month` (`roster_month_id`),
  KEY `idx_roster_audit_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

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
  UNIQUE KEY `uk_roster_month_version` (`roster_month_id`, `roster_version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `roster_week_lock` (
  `week_lock_id` INT NOT NULL AUTO_INCREMENT,
  `month_year` VARCHAR(16) NOT NULL,
  `week_number` INT NOT NULL,
  `week_start` DATE NOT NULL,
  `week_end` DATE NOT NULL,
  `locked_by` INT NOT NULL,
  `locked_date` DATETIME NOT NULL,
  PRIMARY KEY (`week_lock_id`),
  UNIQUE KEY `uq_roster_week_lock` (`month_year`, `week_number`),
  KEY `idx_roster_week_lock_month` (`month_year`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

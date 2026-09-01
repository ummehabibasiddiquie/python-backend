-- Roster Management Module - Phase 1
-- Run against the HRMS database before using roster/holiday APIs.

-- ---------------------------------------------------------------------------
-- Employee joining date (official date of joining; not account creation date)
-- ---------------------------------------------------------------------------
ALTER TABLE `tfs_user`
ADD COLUMN `joining_date` DATE NULL AFTER `created_date`;

-- ---------------------------------------------------------------------------
-- Holiday Master (organization-wide; Super Admin managed)
-- ---------------------------------------------------------------------------
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

-- ---------------------------------------------------------------------------
-- Roster month (one record per employee per month)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `roster_month` (
  `roster_month_id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL,
  `month_year` VARCHAR(20) NOT NULL,
  `status` ENUM('Draft','Pending Approval','Approved','Locked') NOT NULL DEFAULT 'Draft',
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
  `updated_date` DATETIME NOT NULL,
  PRIMARY KEY (`roster_month_id`),
  KEY `idx_roster_month_user` (`user_id`, `month_year`, `is_active`),
  KEY `idx_roster_month_status` (`month_year`, `status`, `is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ---------------------------------------------------------------------------
-- Roster day (one record per employee per date within a roster month)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `roster_day` (
  `roster_day_id` INT NOT NULL AUTO_INCREMENT,
  `roster_month_id` INT NOT NULL,
  `roster_date` DATE NOT NULL,
  `day_type` ENUM('Working','WeekOff','Holiday','Leave','PreJoin') NOT NULL DEFAULT 'Working',
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
  KEY `idx_roster_day_date` (`roster_date`),
  CONSTRAINT `fk_roster_day_month` FOREIGN KEY (`roster_month_id`) REFERENCES `roster_month` (`roster_month_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ---------------------------------------------------------------------------
-- Roster leave (schema for later phases; KRA fields included from day one)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `roster_leave` (
  `leave_id` INT NOT NULL AUTO_INCREMENT,
  `roster_month_id` INT NOT NULL,
  `leave_type` VARCHAR(100) NOT NULL,
  `start_date` DATE NOT NULL,
  `end_date` DATE NOT NULL,
  `reason` TEXT,
  `is_rostered` TINYINT NOT NULL DEFAULT 1 COMMENT '1=Rostered, 0=Unrostered (KRA)',
  `affect_target` TINYINT NOT NULL DEFAULT 0 COMMENT '1=reduces target hours',
  `is_half_day` TINYINT NOT NULL DEFAULT 0,
  `is_active` TINYINT NOT NULL DEFAULT 1,
  `created_by` INT DEFAULT NULL,
  `created_date` DATETIME NOT NULL,
  `updated_date` DATETIME NOT NULL,
  PRIMARY KEY (`leave_id`),
  KEY `idx_roster_leave_month` (`roster_month_id`, `is_active`),
  CONSTRAINT `fk_roster_leave_month` FOREIGN KEY (`roster_month_id`) REFERENCES `roster_month` (`roster_month_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ---------------------------------------------------------------------------
-- Roster change requests (approval workflow - Phase 2+)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `roster_change_request` (
  `request_id` INT NOT NULL AUTO_INCREMENT,
  `roster_month_id` INT NOT NULL,
  `user_id` INT NOT NULL,
  `change_type` VARCHAR(50) NOT NULL,
  `change_payload` JSON NOT NULL,
  `status` ENUM('Pending','Approved','Rejected','Cancelled due to Regeneration') NOT NULL DEFAULT 'Pending',
  `submitted_by` INT NOT NULL,
  `submitted_date` DATETIME NOT NULL,
  `reviewed_by` INT DEFAULT NULL,
  `reviewed_date` DATETIME DEFAULT NULL,
  `rejection_reason` TEXT,
  `is_active` TINYINT NOT NULL DEFAULT 1,
  PRIMARY KEY (`request_id`),
  KEY `idx_roster_change_month_status` (`roster_month_id`, `status`),
  CONSTRAINT `fk_roster_change_month` FOREIGN KEY (`roster_month_id`) REFERENCES `roster_month` (`roster_month_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ---------------------------------------------------------------------------
-- Roster audit log (immutable history)
-- ---------------------------------------------------------------------------
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

-- Weekly roster lock: a Mon–Sun week locks after admin approval of that week's changes.
-- Managers/asst managers cannot edit locked weeks until admin unlocks.

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

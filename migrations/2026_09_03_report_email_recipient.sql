-- Additive only. Does not DROP or alter existing tables.
CREATE TABLE IF NOT EXISTS `report_email_recipient` (
    `recipient_id` INT AUTO_INCREMENT PRIMARY KEY,
    `email` VARCHAR(255) NOT NULL,
    `recipient_type` VARCHAR(8) NOT NULL DEFAULT 'to',
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `created_date` DATETIME NULL,
    `updated_date` DATETIME NULL
);

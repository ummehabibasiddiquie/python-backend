-- Additive only. Does not DROP existing tables.
ALTER TABLE `report_email_recipient`
    ADD COLUMN `send_billable` TINYINT(1) NOT NULL DEFAULT 1,
    ADD COLUMN `send_tracker` TINYINT(1) NOT NULL DEFAULT 1,
    ADD COLUMN `send_tracker_full` TINYINT(1) NOT NULL DEFAULT 1;

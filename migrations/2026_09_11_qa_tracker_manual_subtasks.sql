-- Additive. Subtasks for Feedback/Training and Reporting/Other on QA hours tracker.
ALTER TABLE `qa_work_tracker`
  ADD COLUMN `sub_activity` VARCHAR(32) DEFAULT NULL AFTER `activity_type`,
  ADD COLUMN `agent_id` INT DEFAULT NULL AFTER `task_id`,
  ADD KEY `idx_qa_agent` (`agent_id`);

-- Additive. Assign users to an Assistant Team Leader (same pattern as asst_manager_id).
ALTER TABLE `tfs_user`
  ADD COLUMN `team_leader_id` TEXT NULL AFTER `asst_manager_id`;

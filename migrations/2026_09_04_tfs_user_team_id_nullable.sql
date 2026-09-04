-- Additive. Does not DROP tables or overwrite user data.
-- Super Admin / Admin users are org-wide and do not belong to a team.
-- Makes tfs_user.team_id nullable so registration can store NULL instead of a fake team.

ALTER TABLE `tfs_user`
    MODIFY COLUMN `team_id` INT NULL;

-- Operations role (role_id 8): same app access as Project Manager, but
-- not listed as a Project Manager on Add User, and not on auto group mails
-- (weekly goal, weekly roster). Roster accept/reject stays Admin only.

INSERT INTO `user_role` (`role_id`, `role_name`, `is_active`, `created_date`)
SELECT 8, 'operations', 1, DATE_FORMAT(NOW(), '%d/%m/%Y %H:%i:%s')
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM `user_role`
  WHERE `role_id` = 8
     OR LOWER(TRIM(`role_name`)) = 'operations'
);

UPDATE `tfs_user`
SET `role_id` = 8
WHERE `user_id` = 170
  AND LOWER(TRIM(`user_email`)) = 'shirin.gafoor@transformsolution.net';

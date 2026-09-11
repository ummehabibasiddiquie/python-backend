-- Additive / idempotent. Role display name: Assistant Team Leader (role_id = 7).
-- Prefer this name over legacy "team leader".

INSERT INTO `user_role` (`role_id`, `role_name`, `is_active`, `created_date`)
SELECT 7, 'assistant team leader', 1, DATE_FORMAT(NOW(), '%d/%m/%Y %H:%i:%s')
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM `user_role`
  WHERE `role_id` = 7
     OR LOWER(TRIM(`role_name`)) IN ('assistant team leader', 'team leader')
);

-- Rename legacy row if it already exists as "team leader"
UPDATE `user_role`
SET `role_name` = 'assistant team leader'
WHERE `role_id` = 7
   OR LOWER(TRIM(`role_name`)) = 'team leader';

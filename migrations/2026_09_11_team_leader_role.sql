-- Additive. Team Leader is view-only (same visibility as Assistant Manager, no add/edit).
INSERT INTO `user_role` (`role_id`, `role_name`, `is_active`, `created_date`)
SELECT 7, 'team leader', 1, DATE_FORMAT(NOW(), '%d/%m/%Y %H:%i:%s')
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM `user_role` WHERE `role_id` = 7 OR LOWER(TRIM(`role_name`)) = 'team leader'
);

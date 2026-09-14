-- Additive / idempotent. Designation for Assistant Team Leader users.
-- Table: user_designation (UI dropdown "Designation" on Add/Edit User).

INSERT INTO `user_designation` (`designation`, `is_active`, `created_date`)
SELECT 'Assistant Team Leader', 1, CURDATE()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM `user_designation`
  WHERE LOWER(TRIM(`designation`)) = 'assistant team leader'
);

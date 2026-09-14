-- Deploy step: assign Assistant Team Leaders by team (agents only)
-- Prerequisites:
--   1) team_leader_id column exists
--   2) ATL users 192 (Team A) and 193 (Team B) already created
--
-- Mapping (by user_id — no name lookup):
--   Team A agents → [192]
--   Team B agents → [193]

-- Team A agents → user_id 192
UPDATE tfs_user u
INNER JOIN user_role r ON r.role_id = u.role_id
INNER JOIN team t ON t.team_id = u.team_id AND LOWER(TRIM(t.team_name)) = 'a'
INNER JOIN (
  SELECT user_id FROM tfs_user WHERE user_id = 192 AND is_delete = 1
) tl ON tl.user_id = 192
SET u.team_leader_id = '[192]'
WHERE u.is_delete = 1
  AND LOWER(TRIM(r.role_name)) = 'agent';

-- Team B agents → user_id 193
UPDATE tfs_user u
INNER JOIN user_role r ON r.role_id = u.role_id
INNER JOIN team t ON t.team_id = u.team_id AND LOWER(TRIM(t.team_name)) = 'b'
INNER JOIN (
  SELECT user_id FROM tfs_user WHERE user_id = 193 AND is_delete = 1
) tl ON tl.user_id = 193
SET u.team_leader_id = '[193]'
WHERE u.is_delete = 1
  AND LOWER(TRIM(r.role_name)) = 'agent';

-- Verify:
-- SELECT u.user_id, u.user_name, t.team_name, u.team_leader_id
-- FROM tfs_user u
-- JOIN user_role r ON r.role_id = u.role_id
-- LEFT JOIN team t ON t.team_id = u.team_id
-- WHERE u.is_delete = 1
--   AND LOWER(TRIM(r.role_name)) = 'agent'
--   AND LOWER(TRIM(t.team_name)) IN ('a', 'b')
-- ORDER BY t.team_name, u.user_name;

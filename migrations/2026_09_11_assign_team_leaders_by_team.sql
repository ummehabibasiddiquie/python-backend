-- Deploy step: assign Assistant Team Leaders by team (agents only)
-- Prerequisites (run first if not already applied):
--   1) migrations/2026_09_11_team_leader_role.sql
--   2) migrations/2026_09_11_tfs_user_team_leader_id.sql
--
-- Mapping:
--   Team A (team_name = 'A' / team_id = 1) → Anchal Yadav
--   Team B (team_name = 'B' / team_id = 2) → Chaitanya Bhanarkar
--
-- Uses user_name lookup so it works even if user_id differs on server.
-- Adjust names below if server spelling differs.

-- Team A agents → Anchal Yadav
UPDATE tfs_user u
JOIN user_role r ON r.role_id = u.role_id
SET u.team_leader_id = CONCAT(
  '[',
  (SELECT tl.user_id FROM tfs_user tl WHERE LOWER(TRIM(tl.user_name)) = 'anchal yadav' AND tl.is_delete = 1 LIMIT 1),
  ']'
)
WHERE u.is_delete = 1
  AND u.team_id = (SELECT t.team_id FROM team t WHERE LOWER(TRIM(t.team_name)) = 'a' LIMIT 1)
  AND LOWER(TRIM(r.role_name)) = 'agent'
  AND EXISTS (
    SELECT 1 FROM tfs_user tl
    WHERE LOWER(TRIM(tl.user_name)) = 'anchal yadav' AND tl.is_delete = 1
  );

-- Team B agents → Chaitanya Bhanarkar
UPDATE tfs_user u
JOIN user_role r ON r.role_id = u.role_id
SET u.team_leader_id = CONCAT(
  '[',
  (SELECT tl.user_id FROM tfs_user tl WHERE LOWER(TRIM(tl.user_name)) = 'chaitanya bhanarkar' AND tl.is_delete = 1 LIMIT 1),
  ']'
)
WHERE u.is_delete = 1
  AND u.team_id = (SELECT t.team_id FROM team t WHERE LOWER(TRIM(t.team_name)) = 'b' LIMIT 1)
  AND LOWER(TRIM(r.role_name)) = 'agent'
  AND EXISTS (
    SELECT 1 FROM tfs_user tl
    WHERE LOWER(TRIM(tl.user_name)) = 'chaitanya bhanarkar' AND tl.is_delete = 1
  );

-- Verify after deploy:
-- SELECT u.user_id, u.user_name, t.team_name, u.team_leader_id, r.role_name
-- FROM tfs_user u
-- JOIN user_role r ON r.role_id = u.role_id
-- LEFT JOIN team t ON t.team_id = u.team_id
-- WHERE u.is_delete = 1
--   AND LOWER(TRIM(r.role_name)) = 'agent'
--   AND LOWER(TRIM(t.team_name)) IN ('a', 'b')
-- ORDER BY t.team_name, u.user_name;

# Deploy: QA Tracker + Assistant Team Leader

**Server DB:** `mytfs`  
**Backend branch:** `main`  
**Frontend branch:** `live`  
**Date prepared:** 2026-09-11

Use this from home when you have time. Do steps in order. Take a DB backup before SQL.

---

## 0. Prep

1. Backup database `mytfs`.
2. Pull latest code on the server (or deploy from GitHub):
   - Backend: `main` (includes commits for QA tracker + Assistant Team Leader)
   - Frontend: `live`
3. Confirm you can run SQL against `mytfs` (phpMyAdmin / MySQL CLI).

```bash
# Backend (example)
cd /path/to/backend-api
git pull origin main

# Frontend (example)
cd /path/to/hrms-frontend-live
git pull origin live
```

---

## 1. Database — run in this exact order on `mytfs`

All files are under `backend-api/migrations/`.

### 1A. QA work tracker table (skip if `qa_work_tracker` already exists)

File: `2026_09_09_qa_work_tracker.sql`

```sql
-- Creates table qa_work_tracker
```

Check first:

```sql
USE mytfs;
SHOW TABLES LIKE 'qa_work_tracker';
```

### 1B. QA Feedback / Reporting subtasks

File: `2026_09_11_qa_tracker_manual_subtasks.sql`

Adds columns on `qa_work_tracker`:

- `sub_activity`
- `agent_id`

Check:

```sql
USE mytfs;
SHOW COLUMNS FROM qa_work_tracker LIKE 'sub_activity';
SHOW COLUMNS FROM qa_work_tracker LIKE 'agent_id';
```

### 1C. Assistant Team Leader role (role_id = 7)

File: `2026_09_11_team_leader_role.sql`

- Inserts role if missing
- Renames legacy `team leader` → `assistant team leader`

Check:

```sql
USE mytfs;
SELECT role_id, role_name, is_active FROM user_role WHERE role_id = 7 OR LOWER(role_name) LIKE '%team leader%';
-- Expect: role_name = 'assistant team leader'
```

### 1D. `team_leader_id` column on users

File: `2026_09_11_tfs_user_team_leader_id.sql`

```sql
-- ADD COLUMN team_leader_id TEXT NULL AFTER asst_manager_id
```

Check:

```sql
USE mytfs;
SHOW COLUMNS FROM tfs_user LIKE 'team_leader_id';
```

### 1E. Bulk assign agents to Assistant Team Leaders (optional but recommended)

File: `2026_09_11_assign_team_leaders_by_team.sql`

- Team **A** agents → **Anchal Yadav**
- Team **B** agents → **Chaitanya Bhanarkar**

Uses name lookup (works if user_ids differ from local).  
**Before running:** confirm names on server:

```sql
USE mytfs;
SELECT user_id, user_name, role_id FROM tfs_user
WHERE LOWER(user_name) IN ('anchal yadav', 'chaitanya bhanarkar') AND is_delete = 1;

SELECT team_id, team_name FROM team WHERE LOWER(TRIM(team_name)) IN ('a', 'b');
```

If names/spelling differ, edit the SQL file before running.

Verify after:

```sql
USE mytfs;
SELECT u.team_id, t.team_name, u.team_leader_id, COUNT(*) AS agents
FROM tfs_user u
JOIN user_role r ON r.role_id = u.role_id
LEFT JOIN team t ON t.team_id = u.team_id
WHERE u.is_delete = 1 AND LOWER(TRIM(r.role_name)) = 'agent' AND u.team_id IN (1, 2)
GROUP BY u.team_id, t.team_name, u.team_leader_id;
```

---

## 2. Backend deploy

1. Ensure code on server is latest `main`.
2. Confirm `qa_tracker` blueprint is registered (`app.py` → `/qa_tracker`).
3. **Restart** Flask / Gunicorn / Windows service / PM2 (whatever runs the API).  
   Important if `use_reloader=False`.

```bash
# example — use your real restart method
# systemctl restart hrms-api
# OR: stop python app.py and start again
```

---

## 3. Frontend deploy

1. Pull latest `live`.
2. Install deps if needed: `npm ci` or `npm install`.
3. Build: `npm run build`.
4. Deploy `dist` / build output to the web host.
5. Restart nginx / IIS / static host if required.
6. Hard-refresh browser (Ctrl+F5) or clear cache.

---

## 4. Smoke test checklist

### QA Tracker
- [ ] QA user can open QA hours / QA Report
- [ ] Can add **Feedback**, **Training**, **Reporting**, **Other**
- [ ] Feedback/Training show agent dropdown; Reporting shows project; Other free text
- [ ] Daily / monthly expand shows Feedback & Reporting hours

### Assistant Team Leader
- [ ] Role dropdown shows **Assistant Team Leader** (not “Team Leader”)
- [ ] Add/Edit Agent/QA shows **Assistant Team Leader** multi-select
- [ ] Anchal / Chaitanya (or assigned ATLs) can log in
- [ ] Billable report shows their team agents
- [ ] Roster: ATL can edit / submit change requests
- [ ] Roster: Approve / reject only for **Admin / Super Admin**
- [ ] No QA Report tab for ATL
- [ ] Project Monthly Report: view only (no Add/Edit/Delete)
- [ ] After roster approval, weekly email recipients include Assistant Team Leaders

---

## 5. Quick troubleshooting

| Issue | Likely cause |
|-------|----------------|
| 500 on QA add / list | Step 1A or 1B not run (`sub_activity` / table missing) |
| Role missing in dropdown | Step 1C not run |
| Cannot save Assistant Team Leader on user | Step 1D not run (`team_leader_id` missing) |
| ATL sees empty billable / roster | Step 1E not run, or wrong names in assign SQL |
| Old UI / old API behavior | Code not pulled or backend not restarted |
| Role still shows “Team Leader” | Re-run 1C rename SQL; hard-refresh frontend |

---

## Migration file list (copy-paste order)

```text
1. migrations/2026_09_09_qa_work_tracker.sql          # if needed
2. migrations/2026_09_11_qa_tracker_manual_subtasks.sql
3. migrations/2026_09_11_team_leader_role.sql
4. migrations/2026_09_11_tfs_user_team_leader_id.sql
5. migrations/2026_09_11_assign_team_leaders_by_team.sql
```

Then: **pull code → restart backend → build/deploy frontend → smoke test**.

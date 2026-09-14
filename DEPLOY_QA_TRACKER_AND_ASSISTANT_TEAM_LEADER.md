# Deploy: QA Tracker + Assistant Team Leader + Roster / Tenure fixes

**Server DB:** `mytfs`  
**Backend branch:** `main`  
**Frontend branch:** `live`  
**Updated:** 2026-09-14

Includes:

1. QA work tracker (Feedback / Training / Reporting / Other)
2. Assistant Team Leader role (`role_id = 7`)
3. Roster fixes: fractional tenure on Add User (`0.5`), Reset Employee syncs monthly goal, Tracker Joining Date (default today, past/future allowed)

Do steps in order. **Backup `mytfs` before any SQL.**

---

## 0. From your PC — commit & push (if not already on GitHub)

Local changes must be on GitHub before the server can pull them.

```powershell
# Backend
cd c:\Users\UmmehabibaSiddiquie\Desktop\Hrms_live\backend-api
git add routes/auth.py routes/roster.py routes/roster_workflow.py utils/roster_helpers.py DEPLOY_QA_TRACKER_AND_ASSISTANT_TEAM_LEADER.md
git status
git commit -m "Fix fractional tenure on add user, reset syncs monthly goal, tracker joining date labels."
git push origin main

# Frontend
cd c:\Users\UmmehabibaSiddiquie\Desktop\Hrms_live\hrms-frontend-live
git add src/components/dashboard/manage/user/AddUserFormModal.jsx src/components/dashboard/manage/user/EditUserFormModal.jsx src/components/dashboard/manage/user/UsersManagement.jsx src/components/roster/RosterCalendar.jsx src/components/roster/RosterManagement.jsx
git status
git commit -m "Tracker Joining Date default today; blank empty roster cells; reset toast shows tenure."
git push origin live
```

---

## 1. Prep on server

1. Backup database `mytfs`.
2. Confirm SQL access (phpMyAdmin / MySQL CLI).

```bash
# Backend
cd /path/to/backend-api
git pull origin main

# Frontend
cd /path/to/hrms-frontend-live
git pull origin live
```

---

## 2. Database — run in this exact order on `mytfs`

All files are under `backend-api/migrations/`.

**No new SQL for the 2026-09-14 tenure / joining-date UI fixes** — those are code-only.  
DB steps below are still required if not already applied for QA Tracker + Assistant Team Leader.

### 2A. QA work tracker table (skip if already exists)

File: `2026_09_09_qa_work_tracker.sql`

```sql
USE mytfs;
SHOW TABLES LIKE 'qa_work_tracker';
```

If empty → run the migration file.

### 2B. QA Feedback / Reporting subtasks

File: `2026_09_11_qa_tracker_manual_subtasks.sql`

Adds: `sub_activity`, `agent_id` on `qa_work_tracker`.

```sql
USE mytfs;
SHOW COLUMNS FROM qa_work_tracker LIKE 'sub_activity';
SHOW COLUMNS FROM qa_work_tracker LIKE 'agent_id';
```

### 2C. Assistant Team Leader role (role_id = 7)

File: `2026_09_11_team_leader_role.sql`

- Inserts role if missing  
- Renames legacy `team leader` → `assistant team leader`

```sql
USE mytfs;
SELECT role_id, role_name, is_active FROM user_role
WHERE role_id = 7 OR LOWER(role_name) LIKE '%team leader%';
-- Expect: role_name = 'assistant team leader'
```

### 2D. `team_leader_id` on users

File: `2026_09_11_tfs_user_team_leader_id.sql`

```sql
USE mytfs;
SHOW COLUMNS FROM tfs_user LIKE 'team_leader_id';
```

### 2E. Bulk assign agents to Assistant Team Leaders (optional)

File: `2026_09_11_assign_team_leaders_by_team.sql`

- Team **A** → **Anchal Yadav**  
- Team **B** → **Chaitanya Bhanarkar**

Confirm names first:

```sql
USE mytfs;
SELECT user_id, user_name, role_id FROM tfs_user
WHERE LOWER(user_name) IN ('anchal yadav', 'chaitanya bhanarkar') AND is_delete = 1;

SELECT team_id, team_name FROM team WHERE LOWER(TRIM(team_name)) IN ('a', 'b');
```

Edit the SQL file if spelling differs, then run it.

### 2F. Fix already-broken fractional tenure users (optional data fix)

If agents/QA were added with tenure `0.5` / `0.75` but roster used full 9h, their `user_tenure` may be `NULL` (old Add User bug). After deploy:

1. **Edit User** → set Tenure again (`0.5`) and confirm **Tracker Joining Date**  
2. **Admin → Reset Employee** for that person/month  

Or set tenure in SQL (example):

```sql
USE mytfs;
-- Inspect
SELECT user_id, user_name, user_tenure, joining_date
FROM tfs_user
WHERE is_delete = 1 AND is_active = 1
  AND (user_tenure IS NULL OR TRIM(user_tenure) = '');

-- Then fix specific users manually, e.g.:
-- UPDATE tfs_user SET user_tenure = '0.5' WHERE user_id IN (...);
```

Then **Reset Employee** in the UI (Admin only) so roster + monthly goal recalculate.

---

## 3. Backend deploy

1. `git pull origin main`
2. Confirm `qa_tracker` is registered in `app.py`
3. **Restart** the API (Gunicorn / service / `python app.py`)

```bash
# example — use your real method
# systemctl restart hrms-api
```

---

## 4. Frontend deploy

1. `git pull origin live`
2. `npm ci` or `npm install` (if needed)
3. `npm run build`
4. Deploy `dist` to the web host
5. Restart nginx / IIS if required
6. Hard-refresh browser (Ctrl+F5)

---

## 5. Smoke test checklist

### QA Tracker
- [ ] QA Report / My Hours opens
- [ ] Add **Feedback**, **Training**, **Reporting**, **Other**
- [ ] Feedback/Training → agent dropdown; Reporting → project; Other → free text
- [ ] Daily / monthly expand shows Feedback & Reporting

### Assistant Team Leader
- [ ] Role dropdown: **Assistant Team Leader**
- [ ] Add/Edit Agent/QA: Assistant Team Leader multi-select
- [ ] ATL sees team billable / roster; can submit roster changes
- [ ] Approvals / week locks: Admin / Super Admin only
- [ ] No QA Report tab for ATL
- [ ] Project Monthly Report: view only

### Roster / tenure / Tracker Joining Date
- [ ] Add User shows **Tracker Joining Date** defaulting to **today**
- [ ] Can pick past or future date
- [ ] Add Agent with tenure `0.5` → save → Edit User still shows `0.5` (not blank)
- [ ] Reset Employee (Admin): toast shows start date, working days, tenure → daily hours
- [ ] Mid-month joiner: roster starts from tracker joining date; empty cells are blank
- [ ] Locked weeks do **not** block Admin Reset Employee

---

## 6. Troubleshooting

| Issue | Likely cause |
|-------|----------------|
| 500 on QA add / list | 2A/2B not run |
| Role missing / still “Team Leader” | 2C not run; hard-refresh FE |
| Cannot save ATL on user | 2D not run |
| ATL empty billable | 2E / wrong names |
| Tenure `0.5` becomes blank after Add | Old backend still running — restart API after pull |
| Reset still 21 days / 189h | Fix `user_tenure` + `joining_date` on user, then Reset Employee again |
| Old UI | Frontend not rebuilt / cache |

---

## Migration file list (copy-paste order)

```text
1. migrations/2026_09_09_qa_work_tracker.sql                 # if needed
2. migrations/2026_09_11_qa_tracker_manual_subtasks.sql
3. migrations/2026_09_11_team_leader_role.sql
4. migrations/2026_09_11_tfs_user_team_leader_id.sql
5. migrations/2026_09_11_assign_team_leaders_by_team.sql      # optional
```

Then: **push from PC → pull on server → SQL → restart API → build FE → smoke test**.

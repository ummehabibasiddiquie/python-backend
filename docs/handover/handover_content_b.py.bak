"""Handover documents 03-04: technical reference, support and known issues."""

TECHNICAL_REFERENCE = {
    "number": "03",
    "title": "Technical Reference",
    "audience": "Developers and anyone answering user questions",
    "blocks": [
        ("p", "Section 1 holds the business rules, section 2 the codebase guide and section 3 the database "
              "reference."),

        # ---------------------------------------------------------------- business rules
        ("h", "1. Business rules and core logic"),
        ("p", "These rules are what users rely on. Change them only when the business asks, and update the SOPs."),

        ("h2", "1.1 Tracker and billable hours (Flask routes/tracker.py)"),
        ("bullets", [
            "Each task has task_target (records per hour). Each user has user_tenure (for example 1, 0.75, 0.5).",
            "On add: tenure_target = task_target x tenure (tenure counted as at least 1). billable_hours = "
            "production / tenure_target.",
            "Night shift: an entry added before 09:00 on a NIGHT shift is dated to the previous day.",
            "Future dates are rejected. Users who have left can add entries up to their leaving day only.",
            "Agents can delete their own entry only on the same day, or a night entry dated yesterday until 09:00 "
            "today. Managers can delete any time. Delete is soft (is_active = 0) and removes the Cloudinary file.",
            "Editing an entry keeps its original targets unless new ones are sent; to pick up a changed task target, "
            "delete and add the entry again.",
            "Duplicate check (Node /tracker/process-excel): rows are hashed on the task's important_columns; a file "
            "with a row already uploaded for the same task is rejected when the project has duplicate check on.",
        ]),

        ("h2", "1.2 Assigned hours and goals"),
        ("bullets", [
            "The roster sets each day: Working (full or half), WeekOff, Holiday, Leave, PreJoin, Left.",
            "Daily assigned hours = 9 x tenure (capped at 9); half day = 4.5 x tenure; other day types = 0. The "
            "08:00 job (01, Daily automatic jobs) writes them to temp_qc.assigned_hours.",
            "Monthly Goal = Monthly Target + Extra Assign Hours (user_monthly_tracker). Managers can edit it; once "
            "edited it is not overwritten by roster generation (goal_locked).",
        ]),

        ("h2", "1.3 QC (Node qc-backend and the QC form)"),
        ("bullets", [
            "Sample size = ceil(rows x QC % / 100); QC % comes from the task (default 10). Rows are picked at random "
            "and shown in file order. For a rework check the sample is taken from the agent's latest rework file.",
            "Scoring is done in the browser (QCFormPage.jsx): each category starts at 100 minus its error points; "
            "a record's score is the average of its categories; any error worth 100+ points makes that record 0; "
            "the file score is the average of the sampled records.",
            "Result is fixed by the score, QA cannot override: 100 = Regular, 98 to under 100 = Correction, under "
            "98 = Rework. The backend stores what it is sent.",
            "Correction: the agent fixes the marked sample rows and uploads; QA reviews with Completed or Correction "
            "and Save Status. Rework: the agent fixes the whole file; QA runs a new QC Form on it. Cycles can "
            "repeat; history is in qc_correction_history and qc_rework_history.",
            "Each save emails the agent the result (Node, nodemailer).",
            "Error codes and points come from the AFD linked to the project's category (qc_afd).",
            "QC deadline: 24 working hours after the file is submitted (48 for night trackers), not counting "
            "weekends and holidays; late QC is flagged (Flask utils/qc_sla.py, from 1 Sep 2026).",
            "Automatic 100% QC: a day with 0 production and no file gets QC 100 automatically (from 3 Sep 2026, "
            "14-day look-back; Training/Sample projects 7 and 8 are excluded).",
        ]),

        ("h2", "1.4 QA hours (Flask routes/qa_tracker.py, from 16 Sep 2026)"),
        ("bullets", [
            "QC hours come from the task's QA target. A task uses exactly one mode: object ranges (count from a "
            "column), minutes per file, or minutes per record.",
            "First-time QC counts as QC hours; rework QC counts only after the agent returns the file.",
            "QA add Feedback, Training, Reporting and Other entries themselves (delete allowed within 24 hours).",
            "Expected day: QC 4.5 h, Feedback 1.5 h, Rework QC 1.5 h, Reporting 1.5 h (9 h).",
        ]),

        ("h2", "1.5 Roster (Flask routes/roster.py, routes/roster_workflow.py, utils/roster_*.py)"),
        ("bullets", [
            "Next month's roster can be generated in the last week of the month. Mid-month joiners start from their "
            "Tracker Joining Date.",
            "Managers and Assistant Team Leaders change days; each change is a draft change request. Only one draft "
            "per person per day is kept: a newer draft cancels the older one.",
            "Submit sends the drafts as a batch to Admin / Super Admin (email). Approval applies the change; bulk "
            "approval runs oldest first so the latest change for a day wins.",
            "Admins lock weeks (Monday to Sunday). A locked week cannot be changed by anyone, admins included, until "
            "it is unlocked. Lock Month is available from the last day of the month.",
            "Reset All regenerates the whole month and clears that month's request history; Reset Employee does it "
            "for one person.",
            "Excel Upload applies the changes and submits them in one step.",
            "After approval the weekly roster email can be sent from the week tab.",
        ]),

        ("h2", "1.6 KRA (Flask utils/kra.py, from Sep 2026)"),
        ("table", ["Part", "Weight"], [
            ["Productivity (billable vs goal)", "33%"],
            ["Quality (QC score)", "33%"],
            ["Schedule / roster adherence", "10%"],
            ["Reporting", "14%"],
            ["Timeliness", "10%"],
        ]),
        ("p", "Half-day roster days and unrostered leave count as half a working day. Managers can add a note per day."),

        ("h2", "1.7 Task EOD Report (Flask /tracker/eod-report/*)"),
        ("bullets", [
            "Lists tasks that have important_columns set and entries with a file and a target.",
            "Generate downloads all valid files for one task and day, joins them, removes rows duplicated on the "
            "important columns and returns one Excel (sheets Consolidated Report and Tracker List).",
            "If any file cannot be downloaded from Cloudinary, nothing is generated and the missing trackers are "
            "listed. Not available to agents.",
        ]),

        ("h2", "1.8 Permissions"),
        ("bullets", [
            "User Creation and Project Creation flags (user_permission) are set by Super Admin in User Permission. "
            "The website uses them to show Add User / Add Project, and the API checks the same rule when a user or "
            "project is created.",
            "SOP library: Admin, Super Admin and Project Manager manage it from Manage > SOPs; everyone else views "
            "it from the top menu.",
            "Assistant Team Leader does QC like a QA when picked as an agent's QA: QC screens send scope = 'qc' so "
            "the backend filters by qa_id / project_qa_id instead of the team (routes/dropdown.py, tracker.py, "
            "user.py, qc_history_user_based.py). The Node QC backend also sends scope = 'qc' when it fetches the "
            "tracker for the QC sample (controllers/qc-records.controller.ts). Other screens stay team-based and "
            "view only.",
            "Billable exports include Tenure only for roles 1 to 4.",
        ]),

        ("h2", "1.9 Weekly goal report (weekly_goal_report.py)"),
        ("bullets", [
            "Covers last week, Monday to Sunday, for agents of teams A and B (team rows such as \"A\" are skipped). "
            "Agents deactivated during or after that week are still included; agents who left before it are not.",
            "Week goal = the monthly-target rule (utils/roster_metrics.py) applied to that week: Mon-Fri days that "
            "are not holidays at the agent's daily hours (9 x tenure), minus half working days, \"Left\" days and "
            "leave that affects the target. Leave that does not affect the target is not deducted. Example: 45 h; "
            "36 h with one full-day leave that affects the target or one holiday.",
            "Achieved = production / tenure target of that week's tracker entries (same as the daily billable "
            "report). An agent with no roster that week falls back to their daily assigned hours (temp_qc).",
            "Recipients by role: Admin and Project Manager get all agents; an Assistant Manager / Team Lead gets the "
            "agents whose asst_manager_id / team_leader_id contains them. Nobody missed: an \"all achieved\" email.",
            "% achieved colours: below 75 red, 75 to 89 orange, 90 and above green.",
        ]),

        # ---------------------------------------------------------------- codebase
        ("h", "2. Codebase guide"),
        ("h2", "2.1 Flask API (backend-api)"),
        ("table", ["Path", "What is there"], [
            ["app.py", "Creates the app, registers 26 blueprints, CORS (all origins), /health, starts the 08:00 "
                       "scheduler, runs on 0.0.0.0:5000."],
            ["config.py", "Loads .env, get_db_connection() (new MySQL connection per call), Cloudinary setup, "
                          "upload folders, reset-password settings."],
            ["routes/", "One file per module (table below)."],
            ["utils/", "Shared logic: roster_*.py, qc_sla.py, qc_auto_score.py, qa_targets.py, kra.py, "
                       "cloudinary_utils.py, email_utils.py, security.py (password encryption), response.py "
                       "(api_response), user_status.py (leavers)."],
            ["scheduler.py", "APScheduler job that calls /qc/assign-daily-hours at 08:00."],
            ["billable_report_autosend.py, send_tracker_report.py, send_tracker_report_full_day.py",
             "Report email scripts run by cron."],
            ["weekly_goal_report.py", "Monday weekly goal email (cron); --dry-run, --test-to, --week-start, --to "
                                      "(02, section 11.4; rules in 1.9)."],
            ["report_email_recipients.py", "Reads recipients per report from report_email_recipient."],
            ["scripts/", "Support scripts: reset_qc_tracker.py, repair / restore QC score scripts, roster schema "
                         "check and sync."],
            ["migrations/", "Dated SQL files for schema changes."],
            ["tests/", "unittest tests (python -m unittest)."],
        ]),
        ("p", "Every endpoint answers {status, message, data} through utils/response.api_response. Most are POST "
              "with a JSON body (multipart for uploads) and expect logged_in_user_id. Every endpoint with its "
              "request and access is in 07, API Reference."),
        ("table", ["Blueprint (prefix)", "Main endpoints"], [
            ["/auth", "POST /auth/user: login (JSON) and create user (multipart)."],
            ["/password_reset", "forgot-password, verify-reset-token, reset-password."],
            ["/user, /permission", "User list, update, soft delete; permission flags."],
            ["/dropdown", "POST /dropdown/get with dropdown_type (roles, teams, users by role, projects with tasks)."],
            ["/project, /task, /project_category, /qc_afd", "Projects (create, update, list, sop_links, delete), "
                                                            "tasks, categories, AFD error lists."],
            ["/tracker", "add, update, delete, view, view_daily, eod-report/list, trackers, generate."],
            ["/dashboard", "POST /dashboard/filter for the Overview."],
            ["/user_monthly_tracker, /user_monthly_report, /project_monthly_tracker", "Monthly goals and reports."],
            ["/kra", "users, report, save_notes, export."],
            ["/qc, /qc_audit, /qc_rework, /qc_history_user", "Assign daily hours, temp QC, audits, QC history, "
                                                             "consolidated QC report, annotated download."],
            ["/qa_tracker", "QA hours: sync, entries, day, list, monthly."],
            ["/roster (roster.py + roster_workflow.py)", "Generate, reset, change requests, submit, approve, reject, "
                                                         "locks, emails, versions, audit, Excel template/preview/apply."],
            ["/holiday", "Holiday master (Admin / Super Admin)."],
            ["/sop", "SOP library topics and items."],
            ["/report_email", "Report email recipients (Super Admin)."],
        ]),

        ("h2", "2.2 Node QC API (qc-backend)"),
        ("table", ["Path", "What is there"], [
            ["index.ts", "Express app, JSON limit 50 MB, CORS all, all routes under /api/v1, port from PORT."],
            ["config/env.ts", "Loads .env from the project root even when running from dist."],
            ["controllers/qc-records.controller.ts", "Sample generation and download, row lookup, annotated error "
                                                     "file, agent re-upload, generic list/view/update/delete."],
            ["controllers/qc-regular | qc-correction | qc-rework.controller.ts", "The three QC save endpoints used "
                                                                                 "by the QC form."],
            ["services/qc-workflow.service.ts", "Correction and rework cycle logic: open, close, closePendingCycle, "
                                                "recordAgentUpload, syncQcRecordDecision."],
            ["controllers/mail.controller.ts, constants/email-temp.ts", "QC result emails to agents."],
            ["controllers/tracker-process.controller.ts", "Excel duplicate check and tracker_records insert."],
            ["controllers/ai-evaluation.controller.ts, gemini-key.controller.ts", "Gemini AI evaluation of agent "
                                                                                  "files; per-user Gemini key."],
            ["utils/qc-helpers.ts", "Error list parsing, QC codes, annotated worksheet, sample upload."],
            ["database/db.ts", "New MySQL connection per request."],
        ]),
        ("p", "Endpoints used most: POST /qc-records/generate-sample, POST /qc-records/lookup-row, "
              "GET /qc-records/download-annotated/:id, POST /qc-records/agent-upload, POST /qc-regular/save, "
              "POST /qc-correction/save, POST /qc-rework/save, POST /qc-rework/save-regular, POST /ai/evaluate, "
              "POST /ai/duplicate-check, POST /tracker/process-excel."),
        ("note", "Several files in utils/ and queries/ are not used (scoring-calculator.ts, connection-pool.ts, "
                 "ai-service-queue.ts and others). Scoring is done in the website, not here."),

        ("h2", "2.3 Website (hrms-frontend-live)"),
        ("table", ["Path", "What is there"], [
            ["src/config/environment.js", "Reads the VITE_* variables; API base URLs."],
            ["src/services/api.js, nodeApi.js", "axios clients for Flask and Node."],
            ["src/services/*.js", "Feature services (auth, project, roster, kra, qc, qaTracker, holiday, ...)."],
            ["src/routes/AppRoutes.jsx, paths.js", "Routes, role home pages, tab constants."],
            ["src/context/AuthContext.jsx", "Logged-in user (sessionStorage), login, logout, permission flags."],
            ["src/pages/DashboardPage.jsx", "Picks the dashboard and tab per role; renders the Manage panel."],
            ["src/pages/QCFormPage.jsx", "The QC form, scoring and result buttons."],
            ["src/components/header/Header.jsx", "Top menu per role."],
            ["src/components/AgentDashboard/", "Agent Tracker, AI Evaluation, billable and QC report."],
            ["src/components/QAAgentDashboard/", "QA dashboard and My Report hours."],
            ["src/components/dashboard/", "Admin and Assistant Manager dashboards, reports, QC overview, audit, "
                                          "Task EOD Report."],
            ["src/components/dashboard/manage/", "Users, projects and tasks, AFD, categories, report emails."],
            ["src/components/roster/", "Roster management, approvals, holidays, Excel upload, My Roster."],
            ["src/components/sop/SopLibrary.jsx", "SOP library."],
            ["src/hooks/useRoutedDashboardTab.js", "Keeps ?tab= and ?subtab= in the address bar."],
        ]),
        ("p", "Screens are opened by URL: /dashboard?tab=<tab>&subtab=<sub>, and Manage tabs with "
              "&adminTab=<users|projects|afd|category|permissions|roster|sops>. Agents use /agent for the tracker."),
        ("note", "Role flags are worked out in more than one place (AuthContext, DashboardPage, Header, "
                 "useRosterRoles). When you change who can see a screen, check all of them."),

        # ---------------------------------------------------------------- database
        ("h", "3. Database reference"),
        ("p", "Live database: mytfs (MySQL 8 on the VPS). Local copy: tfs_hrms. Both APIs share it. This section "
              "covers the main tables; every table and column is in 08, Database Schema."),
        ("note", "Soft delete: in tfs_user and the sop_* tables, is_delete = 1 means the row is LIVE and 0 means "
                 "deleted. Most other tables use is_active (1 active, 0 removed)."),

        ("h2", "3.1 People and setup"),
        ("table", ["Table", "Holds", "Key columns"], [
            ["tfs_user", "Every user", "user_id, role_id, team_id, project_manager_id / asst_manager_id / "
                                       "team_leader_id / qa_id (ID lists like [192]), user_tenure, user_password "
                                       "(encrypted), is_active, is_delete, deactivated_at (leaving day), joining_date"],
            ["user_role", "Roles 1-7", "role_id, role_name"],
            ["user_designation, team", "Designations; teams A, B, Quality, Marketing", ""],
            ["user_permission", "Creation flags per user", "user_creation_permission, project_creation_permission"],
            ["project", "Projects", "project_code, project_category_id, project_manager_id, project_team_id / "
                                    "project_qa_id (JSON), ai_evaluation, duplicate_check, project_pprt (files JSON), "
                                    "project_sop_links (JSON), is_active"],
            ["task", "Tasks", "project_id, task_team_id (JSON), task_target, qc_percentage, important_columns (JSON), "
                              "qa_count_column, qa_target_ranges, qa_minutes_per_file, qa_minutes_per_record"],
            ["project_category, afd, qc_afd", "QC error lists", "category -> afd; qc_afd holds categories, errors "
                                                                "and points"],
        ]),

        ("h2", "3.2 Production"),
        ("table", ["Table", "Holds", "Key columns"], [
            ["task_work_tracker", "One row per tracker entry", "tracker_id, user_id, project_id, task_id, date_time, "
                                                               "shift, production, actual_target, tenure_target, "
                                                               "billable_hours, tracker_file (Cloudinary URL), "
                                                               "qc_status (0 = not QC'd), is_active"],
            ["tracker_records", "Row hashes from tracker files", "Used for the duplicate check"],
            ["temp_qc", "One row per agent per day", "assigned_hours, qc_score (daily)"],
            ["user_monthly_tracker", "Monthly goal per user", "month_year, monthly_target, extra_assigned_hours, "
                                                              "working_days, goal_locked"],
            ["project_monthly_tracker", "Monthly target per project", ""],
            ["api_call_logs", "Tracker add / delete audit", ""],
        ]),

        ("h2", "3.3 QC and QA"),
        ("table", ["Table", "Holds", "Key columns"], [
            ["qc_records", "One QC per tracker", "id, tracker_id, qa_user_id, agent_id, qc_score, error_list (JSON), "
                                                 "status (regular / correction / rework), qc_status, qc_file_path "
                                                 "(sample), whole_file_path, file_record_count, qc_generated_count"],
            ["qc_correction_history", "Correction cycles", "qc_record_id, correction_count, qc_file_path, "
                                                           "correction_file_path, correction_file_qc_status, "
                                                           "correction_error_list"],
            ["qc_rework_history", "Rework cycles", "qc_record_id, rework_count, rework_file_path, "
                                                   "rework_file_qc_status, rework_qc_score, rework_error_list"],
            ["qc_audit", "Manager audits of QA work", "qc_record_id, audit score, file"],
            ["qa_work_tracker", "QA hours", "activity_type, sub_activity, hours, target_snapshot"],
        ]),

        ("h2", "3.4 Roster"),
        ("table", ["Table", "Holds"], [
            ["roster_month", "One per person per month; status Draft / Pending Approval / Approved / Locked."],
            ["roster_day", "One per person per day; day_type, shift, working_type, working_hours."],
            ["roster_leave", "Leaves (rostered, half day, affects target)."],
            ["roster_change_request", "Draft, pending, approved, rejected, cancelled changes; batch_id when submitted."],
            ["roster_week_lock", "Locked Monday-Sunday weeks."],
            ["roster_version_snapshot, roster_audit_log", "History of approvals and every roster action."],
            ["org_holiday", "Holiday master."],
        ]),

        ("h2", "3.5 Other"),
        ("table", ["Table", "Holds"], [
            ["sop_topic, sop_item", "SOP library (created by the code)."],
            ["report_email_recipient", "Report email recipients and which reports each gets."],
            ["kra_day_note", "KRA notes per user per day."],
        ]),

        ("h2", "3.6 Useful queries"),
        ("code", """-- A user and their role
SELECT u.user_id, u.user_name, u.user_email, r.role_name, u.user_tenure, u.is_active
FROM tfs_user u JOIN user_role r ON r.role_id = u.role_id
WHERE u.user_email = 'name@transformsolution.net';

-- A tracker and its QC
SELECT tracker_id, user_id, project_id, task_id, date_time, shift, production, qc_status, is_active
FROM task_work_tracker WHERE tracker_id = 12345;
SELECT id, qc_score, status, qc_status, created_at, updated_at FROM qc_records WHERE tracker_id = 12345;

-- One person's day
SELECT * FROM temp_qc WHERE user_id = 123 AND date = '2026-10-21';
SELECT rd.* FROM roster_day rd
JOIN roster_month rm ON rm.roster_month_id = rd.roster_month_id
WHERE rm.user_id = 123 AND rm.is_active = 1 AND rd.roster_date = '2026-10-21';"""),
        ("note", "Check column names with SHOW COLUMNS FROM <table>; before running a query you wrote yourself."),
    ],
}


SUPPORT_AND_ISSUES = {
    "number": "04",
    "title": "Support and Known Issues",
    "audience": "Developers on support duty and the lead",
    "blocks": [
        ("p", "Section 1 holds the step-by-step fixes. Sections 2 to 5 cover recent changes, what to check before "
              "you start, known issues and risks, and pending work."),

        ("h", "1. Support runbook"),
        ("p", "Follow the golden rules in 01 for every fix that changes data: back up first, SELECT first, then "
              "change inside START TRANSACTION, check, then COMMIT (or ROLLBACK). Run the SQL on the server or in "
              "phpMyAdmin against mytfs."),

        ("h2", "1.1 QC was filled by mistake: let QA fill it again"),
        ("p", "Full guide with worked examples: docs/reset-qc-for-tracker.md. Do not delete the tracker or its file."),
        ("code", """SELECT id FROM qc_records WHERE tracker_id = TRACKER_ID;   -- confirm

START TRANSACTION;
DELETE qa FROM qc_audit qa JOIN qc_records qr ON qa.qc_record_id = qr.id WHERE qr.tracker_id = TRACKER_ID;
DELETE rh FROM qc_rework_history rh JOIN qc_records qr ON rh.qc_record_id = qr.id WHERE qr.tracker_id = TRACKER_ID;
DELETE ch FROM qc_correction_history ch JOIN qc_records qr ON ch.qc_record_id = qr.id WHERE qr.tracker_id = TRACKER_ID;
DELETE FROM qc_records WHERE tracker_id = TRACKER_ID;
UPDATE task_work_tracker SET qc_status = 0 WHERE tracker_id = TRACKER_ID;
COMMIT;"""),
        ("p", "Or on the server: python scripts/reset_qc_tracker.py --tracker-id TRACKER_ID --dry-run, then without "
              "--dry-run."),

        ("h2", "1.2 QA gets \"Could not save QC\" when saving QC"),
        ("steps", [
            "Ask for the tracker ID, the time and the full message on screen: after \"Could not save QC:\" it shows "
            "the real reason (older versions only said \"Internal server error\").",
            "pm2 logs node-backend --lines 300 and find the error at that time for the full detail.",
            "Common causes: a column value rejected by MySQL, a cycle in an unexpected state, the agent's file "
            "missing on Cloudinary.",
            "The whole save is rolled back, so nothing is half-saved; QA can retry after the fix.",
        ]),

        ("h2", "1.3 A QC score shows 0% or blank with no errors"),
        ("p", "Records whose qc_score / error_list were wiped by the old correction save (fixed 12 Oct 2026) were "
              "repaired on 19 Oct. If more appear: backend-api/scripts/repair_qc_null_scores.py rebuilds them from "
              "the sample files (dry run by default, --apply to write), and restore_qc_scores_from_backup.py copies "
              "them from a restored backup database."),

        ("h2", "1.4 Agent cannot delete a tracker"),
        ("p", "Agents can delete only same-day entries (or a night entry dated yesterday, until 09:00). Older "
              "entries: a manager deletes it from Tracker Report."),

        ("h2", "1.5 Billable or assigned hours look wrong for a day"),
        ("steps", [
            "Check the roster day (day type, half day, shift) for that person and date.",
            "Check temp_qc.assigned_hours for the date; the 08:00 job writes it.",
            "Check user_tenure; tenure changes do not change old days by themselves.",
            "Check the tracker entries (production, targets). Fix the roster or entries, not the report.",
        ]),

        ("h2", "1.6 Roster change not applied"),
        ("bullets", [
            "Was it submitted? Drafts are not sent until Submit.",
            "Is the week locked? Locked weeks reject changes; Admin unlocks the week.",
            "Was another change made for the same day? Only the latest draft is kept.",
            "Is it still Pending Approval? Admin approves in Roster Management > Approval Queue.",
        ]),

        ("h2", "1.7 Someone did not get a report email"),
        ("bullets", [
            "Super Admin > Report emails: the person is listed with that report switched on.",
            "crontab -l on the server: the job is scheduled; the log file shows a [SUCCESS] line for the day.",
            "SMTP settings in the backend .env are valid (test with test_mail.py).",
            "Weekly goal report: it has no recipient list. Check the person is an active Admin or Project Manager, "
            "or is set as Assistant Manager / Team Lead on the agents (Edit User). tail weekly_goal_report.log shows "
            "every address it was sent to.",
            "To send a missed week again: venv/bin/python weekly_goal_report.py --week-start <any date in that "
            "week>, adding --to <email> for one person only (02, section 11.4).",
        ]),

        ("h2", "1.8 User cannot log in"),
        ("bullets", [
            "is_active = 1 and is_delete = 1 on tfs_user; deactivated_at not in the past.",
            "Forgot Password sends a link valid for RESET_TOKEN_TTL_SECONDS (default 5 minutes).",
            "Admin can set a new password from Edit User.",
        ]),

        ("h2", "1.9 A task is missing in Task EOD Report"),
        ("p", "Set the task's Important Columns (Edit Task) and check the entries have a file and a target."),

        ("h2", "1.10 New user setup"),
        ("steps", [
            "Admin > User Management > Add User: role, team, reporting lines, QA (agents), tenure, Tracker Joining "
            "Date.",
            "Add the agent to the task's team (Projects and Tasks > Edit Task) so the task appears in their Tracker.",
            "Generate or reset their roster for the month (Roster Management).",
        ]),

        ("h", "2. Recent changes (Sep - Oct 2026)"),
        ("table", ["Date", "Area", "Change"], [
            ["16-17 Sep", "QA hours", "QA hours from 16 Sep 2026 with task QA target modes; night trackers get 48 "
                                      "QC hours."],
            ["18-24 Sep", "KRA", "Monthly KRA report, Excel export and KRA tab."],
            ["23 Sep", "Roster", "Edit unlocked weeks while other weeks are pending approval."],
            ["6-7 Oct", "QC", "Annotated QC downloads with highlighted errors; QC emails fixed (SMTP from dist)."],
            ["7 Oct", "Goals / KRA", "Manager goal edits kept after roster generate; leave split in KRA."],
            ["12 Oct", "SOP library", "SOP topics and document uploads."],
            ["12-13 Oct", "QC", "Correction kept as correction; rework sample from latest agent file; QA can add a "
                                "missed row."],
            ["14 Oct", "QC Report Overview", "Agent / QC / project / task filters, QC file download, Error Report "
                                             "export (errors per type per file)."],
            ["14 Oct", "Tasks", "Only one QC target type per task."],
            ["16 Oct", "QC", "Date and percent cells keep their format in QC files."],
            ["20 Oct", "Tracker / roster / reports", "Night tracker delete next morning; one draft per roster day, "
                                                     "oldest-first approval; Tenure in billable exports."],
            ["21 Oct", "QC", "Correction save no longer fails when a rework file is pending (node-backend 5a488f3)."],
            ["22 Oct", "Overview / projects", "Overview shows task names; shared-drive SOP links on projects; "
                                              "managers can manage the SOP library."],
        ]),

        ("h", "3. Check before you start"),
        ("bullets", [
            "Run git status and git log origin/<branch>..<branch> in each repository to see anything not pushed.",
            "Compare git log -1 on the server with the latest commit on main / live, so you know what is live.",
        ]),

        ("h", "4. Known issues and risks"),
        ("table", ["Issue", "Impact", "Suggested fix"], [
            ["Passwords are encrypted, not hashed, and /user/list returns them decrypted", "Passwords readable by "
             "admins and from the API", "Hash with bcrypt; stop returning passwords."],
            ["Node reads ENCRYPTION_SECRET but .env has ENCRYPTION_KEY", "Gemini keys encrypted with the default "
             "secret in the code", "Set ENCRYPTION_SECRET only together with asking agents to save their Gemini "
             "keys again (the saved ones become unreadable)."],
            ["scheduler.py calls /qc/assign-daily-hours without the CRON_SECRET header", "The 08:00 job would be "
             "refused if CRON_SECRET were set", "Send the header, or leave CRON_SECRET unset."],
            ["Files removed in Edit Project stay in Cloudinary", "Unused files use storage", "Delete them on save if "
             "storage becomes a concern."],
            ["Task EOD Report lists every project's tasks for any non-agent", "Assistant Managers / QA see other "
             "teams' tasks", "Scope the list by role if the business wants that."],
            ["New MySQL connection per request in both APIs", "Slow under load", "Use a connection pool."],
        ]),

        ("h", "5. Pending work and ideas"),
        ("table", ["Item", "Status"], [
            ["Upload the Word SOPs to the SOP library (one topic per role)", "To do"],
            ["Add SOP links to each project (Add / Edit Project > SOP Links)", "To do after deploy"],
            ["Other security items in section 4", "Not started; agree priority with the lead"],
        ]),
    ],
}

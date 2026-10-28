"""Handover document 07: API Reference (Flask API and Node QC API) for developers.

Built from a read-only pass over backend-api (Flask), qc-backend (Node/Express) and the
frontend call sites in hrms-frontend-live/src. No secret values are copied here.
"""

HEADERS = ["Endpoint", "Purpose", "Request", "Access", "Response", "Used by"]

# ---- Access wording shared by many rows -------------------------------------------------
A_NONE = "None - no check"
A_ANY = "Any logged-in user (no role check)"
A_ATL = "Any role except Asst Team Leader (blocked only if logged_in_user_id is sent)"
A_ROSTER = "Super Admin, Admin, PM, Asst Manager, Asst Team Leader"
A_ADMIN = "Admin, Super Admin"
A_NOAGENT = "All roles except Agent"
A_SCOPED = "Any logged-in user; data limited to the caller's reporting scope"
A_ROSTER_SCOPED = "Any logged-in user; Agent and QA see only their own roster"

RS = "rosterService.js (Roster Management)"


def table(rows):
    return ("table", HEADERS, [list(r) for r in rows])


# =========================================================================================
# 1. CONVENTIONS
# =========================================================================================
ROLE_TABLE = ("table", ["Role id", "Role name"], [
    ["1", "Super Admin"],
    ["2", "Admin"],
    ["3", "Project Manager (PM)"],
    ["4", "Assistant Manager (AM)"],
    ["5", "QA"],
    ["6", "Agent"],
    ["7", "Assistant Team Leader (ATL)"],
])

CONVENTIONS = [
    ("h", "1. Conventions"),
    ("h2", "Base URLs"),
    ("table", ["Service", "Live", "Local"], [
        ["Flask API (backend-api)", "https://tfshrms.cloud/python", "http://127.0.0.1:5000"],
        ["Node QC API (qc-backend)", "https://tfshrms.cloud/api/v1", "http://127.0.0.1:8000/api/v1"],
    ]),
    ("p", "In the tables below Flask paths are written relative to the Flask base URL (for example "
          "POST /tracker/add) and Node paths include the /api/v1 prefix (for example "
          "POST /api/v1/qc-regular/save). The frontend picks the URL from VITE_API_BASE_URL (Flask) and "
          "VITE_API_NODE_BASE_URL (Node); in dev mode Node calls go through the Vite proxy at /api/v1."),
    ("h2", "Request rules"),
    ("bullets", [
        "Almost every Flask endpoint is POST with a JSON body. Exceptions: PUT /user/delete_user, PUT /task/delete, "
        "PUT /qc_afd/update, DELETE /qc_afd/delete, a few GET endpoints, and POST /tracker/update which also accepts PUT.",
        "Uploads use multipart/form-data (file field names are given per endpoint). Endpoints that create or edit "
        "users, projects, tasks and trackers are multipart even when there is no file.",
        "Almost every Flask endpoint expects logged_in_user_id in the body (a few older ones use user_id for the "
        "acting user). Fields marked * in the Request column are required.",
        "There is NO auth token check. The frontend sends 'Authorization: Bearer <token>' but neither backend "
        "validates it. The API trusts whatever logged_in_user_id the caller sends, and role checks are made from "
        "that id. Several role checks run only when logged_in_user_id is present.",
        "The only secret-protected endpoints are /qc/assign-daily-hours and /qc/send-billable-report: when the "
        "CRON_SECRET environment variable is set they require 'Authorization: Bearer <CRON_SECRET>'.",
        "CORS is open to all origins on both services.",
        "Date formats: dates are YYYY-MM-DD; date-times are YYYY-MM-DD HH:MM:SS; months are MONYYYY such as "
        "SEP2026 or JAN2026 (the QA tracker also accepts YYYY-MM). Times are IST.",
    ]),
    ("h2", "Response envelopes"),
    ("bullets", [
        "Flask: {status, message, data}. status is the HTTP code as a number (200, 201, 400, 403, 404, 500); data is "
        "left out when empty. Built by utils/response.api_response and mirrored in the HTTP status.",
        "Flask exceptions: routes/qc.py (/qc/*) returns {status: true/false, message, data} with a boolean status; "
        "routes/qc_audit.py builds {status, message[, data]} directly with jsonify.",
        "Flask file downloads (Excel) return the file itself (send_file), not JSON; errors come back as JSON.",
        "Node: {success: true/false, message, data}. Failures add an 'error' text for 500s. A few endpoints return "
        "extra top-level keys (hasKey, processedFiles). Node downloads return the Excel file with a "
        "Content-Disposition header.",
        "Validation failures are 400 with a message such as 'tracker_id is required'. Permission failures are 403.",
    ]),
    ("h2", "Role ids used in the Access column"),
    ROLE_TABLE,
    ("p", "Role names in the code are compared in lower case (for example 'super admin', 'assistant team leader'). "
          "'Admin-level' in the code means Admin, Super Admin and Project Manager. 'Read-only guard' means the "
          "Assistant Team Leader is rejected with 403 'Assistant Team Leader has view-only access'. 'scope: qc' (sent "
          "by the QC and My Report screens) makes the backend treat an Assistant Team Leader like a QA: they see the "
          "agents and projects where they are the QA instead of their team."),
    ("h2", "Example request"),
    ("p", "Fetch trackers for a user (Flask, JSON body):"),
    ("code",
     "POST https://tfshrms.cloud/python/tracker/view\n"
     "Content-Type: application/json\n"
     "\n"
     "{\n"
     "  \"logged_in_user_id\": 12,\n"
     "  \"date_from\": \"2026-09-01\",\n"
     "  \"date_to\": \"2026-09-30\",\n"
     "  \"project_id\": 3,\n"
     "  \"page\": 1,\n"
     "  \"page_size\": 20\n"
     "}\n"
     "\n"
     "200 OK\n"
     "{\n"
     "  \"status\": 200,\n"
     "  \"message\": \"Trackers fetched successfully\",\n"
     "  \"data\": { \"trackers\": [ ... ], \"pagination\": { ... } }\n"
     "}"),
    ("p", "Save a QC record (Node, JSON body):"),
    ("code",
     "POST https://tfshrms.cloud/api/v1/qc-regular/save\n"
     "Content-Type: application/json\n"
     "\n"
     "{ \"logged_in_user_id\": 21, \"tracker_id\": 456, \"qa_user_id\": 21, \"agent_id\": 12,\n"
     "  \"project_id\": 3, \"task_id\": 9, \"qc_score\": 96, \"error_list\": [ ... ] }\n"
     "\n"
     "200 OK\n"
     "{ \"success\": true, \"message\": \"Regular QC record saved successfully\" }"),
    ("note", "Node and Flask are separate processes that share the same MySQL database. Node calls Flask "
             "POST /tracker/view (PYTHON_URL) to read tracker rows; see section 4."),
]

# =========================================================================================
# 2. FLASK API
# =========================================================================================
FLASK_GROUPS = []


def group(title, intro, rows):
    FLASK_GROUPS.append((title, intro, rows))


group("Service health", None, [
    ["GET /", "Banner check", "-", A_NONE, "Plain text 'Flask Auth API is running!'", "-"],
    ["GET /health", "Liveness check", "-", A_NONE, "Plain text 'OK' (200)", "- (monitoring)"],
])

group("Auth and password reset", None, [
    ["POST /auth/user", "Login (JSON body)",
     "user_email*, user_password*, device_id*, device_type* (exactly these four keys, otherwise 400)",
     "None - public",
     "User record without password, profile picture URL, project/user creation permission flags",
     "authService.js (Login)"],
    ["POST /auth/user", "Create user (multipart form)",
     "multipart: user_name*, user_email*, user_password*, role_id*, designation_id, team, user_tenure, user_number, "
     "user_address, joining_date, project_manager, assistant_manager, team_leader, qa, profile_picture (file), "
     "logged_in_user_id",
     "Super Admin, Admin, PM, or anyone with user_creation_permission = 1 (never Asst Team Leader); "
     "checked only if logged_in_user_id is sent",
     "201 message 'User registered successfully'",
     "authService.js (Users Management - add user)"],
    ["POST /password_reset/forgot-password", "Email a reset link (always answers the same message)",
     "user_email*", "None - public", "Generic message; the link is sent by email",
     "authService.js (Forgot Password)"],
    ["POST /password_reset/verify-reset-token", "Check a reset token is still valid",
     "token*", "None - public", "user_id when the token is valid", "authService.js (Reset Password)"],
    ["POST /password_reset/reset-password", "Set a new password from a token",
     "token*, new_password*", "None - public", "Success message", "authService.js (Reset Password)"],
])

group("Users and permissions", None, [
    ["POST /user/list", "List users the caller may see",
     "user_id* (acting user), month_year, date_from, date_to, is_active, scope ('qc')",
     "All roles except Agent (Agent gets an empty list)",
     "List of users with role, team, designation and reporting names (includes the decrypted password - see 04)",
     "authService.js, userService.js (Users Management), QAAgentList.jsx"],
    ["POST /user/update_user", "Edit a user or activate/deactivate",
     "multipart: user_id*, user_name, user_number, user_address, role_id, designation_id, user_tenure, team_id, "
     "project_manager_id, asst_manager_id, team_leader_id, qa_id, joining_date, is_active, user_password, "
     "profile_picture (file), logged_in_user_id",
     A_ATL, "Success message", "authService.js, userService.js (Users Management)"],
    ["PUT /user/delete_user", "Soft-delete a user (is_delete = 0, is_active = 0)",
     "JSON: user_id*, logged_in_user_id", A_ATL, "Success message", "authService.js (Users Management)"],
    ["POST /permission/user_list", "List users with project/user creation permission flags",
     "logged_in_user_id*, role",
     "Super Admin, Admin, PM, Asst Manager (QA, Agent and Asst Team Leader get 403)",
     "{users: [...]} with permission flags", "UserTrackingView.jsx"],
    ["POST /permission/update", "Grant or remove project/user creation permission",
     "user_id* (acting user), target_user_id*, project_creation_permission, user_creation_permission",
     "Every role except QA and Agent (the hierarchy check is commented out in the code)",
     "Success message", "UserTrackingView.jsx"],
])

group("Dropdowns", None, [
    ["POST /dropdown/get", "One endpoint for all dropdown lists",
     "dropdown_type* (designations, user roles, teams, project categories, afd, a role name such as agent / qa / "
     "assistant manager / admin, projects with tasks), project_id, team_id, logged_in_user_id, user_id, date_from, "
     "month_year, scope ('qc' = Asst Team Leader filtered like a QA)",
     "None for most types. 'agent' needs logged_in_user_id and a role of Admin, Super Admin, PM, Asst Manager, "
     "Asst Team Leader or QA (else 403); 'projects with tasks' needs logged_in_user_id or user_id",
     "List of {id, label} items (agents also carry user_tenure)",
     "dropdownService.js, dropdownApi.js, userService.js, Tracker.jsx, QATrackerReport.jsx, BillableReport.jsx, "
     "AdminDashboard.jsx and about 10 other screens"],
])

group("Projects, tasks, categories, AFD", None, [
    ["POST /project/create", "Create a project",
     "multipart: project_name*, project_code*, project_description, project_manager_id, asst_project_manager_id, "
     "project_team_id, project_qa_id, project_category_id, requires_ai_evaluation, requires_duplicate_check, "
     "sop_links, files (instruction files), logged_in_user_id",
     "Super Admin, Admin, PM, Asst Manager, or anyone with project_creation_permission = 1 (never Asst Team Leader); "
     "checked only if logged_in_user_id is sent",
     "201 'Project created successfully' (body fields unverified)", "projectService.js (Manage - Projects)"],
    ["POST /project/update", "Edit a project, its files, SOP links or active flag",
     "multipart: project_id*, any project field above, existing_files, is_active, files, logged_in_user_id",
     A_ATL, "Success message", "projectService.js"],
    ["POST /project/list", "List projects",
     "include_inactive", A_NONE, "List of projects with managers, team, QA, flags and SOP links",
     "projectService.js, ProjectMonthlyReport.jsx"],
    ["POST /project/sop_links", "Get the SOP links of one project", "project_id*", A_NONE,
     "SOP links list", "ProjectSopLinks.jsx"],
    ["POST /project/my_projects", "View-only Projects tab: caller's active projects with files, SOP links and tasks",
     "logged_in_user_id*",
     "Agent: projects and tasks assigned to them (project_team_id / task_team_id). QA: projects where they are "
     "in the team or Project QA. Asst Team Leader: same as QA plus their team's projects. Others: all active",
     "List of projects with project_manager, assistant_managers, qa (names), project_files, sop_links and tasks "
     "(task_target, qc_target, qc_percentage, important_columns, sample_file). Agents get only project_files and "
     "task_name / task_target (no SOP links or QC fields)", "MyProjects.jsx"],
    ["POST /project/delete", "Delete a project", "project_id*, logged_in_user_id", A_ATL,
     "Success message", "projectService.js"],
    ["POST /task/add", "Create a task under a project",
     "multipart: project_id*, task_name*, task_team_id* (JSON list), task_description, task_target, is_active, "
     "qc_percentage, qa_count_column, qa_minutes_per_file, qa_minutes_per_record, task_file (file)",
     A_NONE, "201 with the new task", "projectService.js (Manage - Tasks)"],
    ["POST /task/update", "Edit a task",
     "multipart: task_id*, project_id, task_team_id, task_name, task_description, task_target, important_columns, "
     "is_active, qc_percentage, qa_count_column, qa_target_ranges, qa_minutes_per_file, qa_minutes_per_record, "
     "task_file (file), remove_task_file",
     A_NONE, "Updated task", "projectService.js"],
    ["PUT /task/delete", "Delete a task", "JSON: task_id*", A_NONE, "Success message", "projectService.js"],
    ["POST /task/list", "List tasks", "project_id, include_inactive, month_year", A_NONE,
     "List of tasks with targets and QC settings", "projectService.js, ProjectMonthlyReport.jsx"],
    ["POST /project_category/create", "Create a project category", "project_category_name*, afd_id", A_NONE,
     "201 with the new category", "ProjectCategory.jsx"],
    ["POST /project_category/update", "Edit a project category",
     "project_category_id*, project_category_name*, afd_id", A_NONE, "Success message", "ProjectCategory.jsx"],
    ["POST /project_category/delete", "Delete a project category", "project_category_id*", A_NONE,
     "Success message", "ProjectCategory.jsx"],
    ["POST /project_category/list", "List categories with their AFD",
     "project_category_id", A_NONE, "List of categories", "ProjectCategory.jsx, qcService.js (QC form)"],
    ["POST /qc_afd/add", "Add an AFD master with categories and sub-categories (QC error definitions)",
     "master_afd_name*, categories* [{afd_name*, afd_points*, subcategories [{afd_name*, afd_points*}]}]",
     A_NONE, "Success message", "AFDManagement.jsx (Manage - AFD)"],
    ["PUT /qc_afd/update", "Update an AFD master tree",
     "master_afd_id*, master_afd_name, categories", A_NONE, "Success message", "AFDManagement.jsx"],
    ["DELETE /qc_afd/delete", "Delete AFD rows (JSON body on a DELETE)",
     "afd_ids or qc_afd_ids*", A_NONE, "Success message", "AFDManagement.jsx"],
    ["POST /qc_afd/list", "List AFD definitions as a tree",
     "project_category_id", A_NONE, "AFD masters with categories and sub-categories",
     "AFDManagement.jsx, QCFormPage.jsx"],
    ["POST /qc_afd/list_by_category", "List all AFD rows grouped as category with sub-categories", "-", A_NONE,
     "Categories with sub-categories", "-"],
])

group("Tracker and Task EOD", None, [
    ["POST /tracker/add", "Add a daily tracker entry",
     "multipart: user_id*, project_id*, task_id*, production*, tenure_target*, date, shift (DAY/NIGHT), "
     "tracker_note, tracker_file (file), logged_in_user_id, device_id, device_type",
     A_ATL + "; future dates and users who have left are rejected",
     "201 with tracker_id", "Tracker.jsx, QATrackerReport.jsx"],
    ["POST /tracker/update (also PUT)", "Edit a tracker entry",
     "multipart: tracker_id*, date_time, production, project_id, task_id, base_target, shift, tracker_note, "
     "tracker_file (file), remove_file, logged_in_user_id",
     A_ATL + "; future dates and users who have left are rejected",
     "Success message", "QATrackerReport.jsx"],
    ["POST /tracker/delete", "Delete a tracker entry",
     "JSON: tracker_id*, logged_in_user_id, device_id, device_type",
     A_ATL + "; an Agent can delete their own entry only on the day it was added (a night entry dated yesterday until 09:00)",
     "Success message", "Tracker.jsx, QATrackerReport.jsx"],
    ["POST /tracker/view", "List trackers with filters and totals",
     "logged_in_user_id*, tracker_id, user_id, team_id, project_id, shift, date_from, date_to, is_active, "
     "qc_pending, page, page_size (or limit), scope ('qc')",
     "Any logged-in user. Admin, Super Admin, PM see all; Asst Team Leader by team (by QA assignment with "
     "scope = qc); others by assignment. "
     "A user_id filter is applied as sent (unverified for every role combination)",
     "{trackers, totals..., pagination when paged}",
     "Tracker.jsx, QATrackerReport.jsx, QAAgentList.jsx, BillableReport.jsx, OverviewTab.jsx; also called by Node"],
    ["POST /tracker/view_daily", "Daily aggregated trackers and monthly summary (billable report)",
     "logged_in_user_id*, month_year, date_from, date_to, team_id, project_id, user_id, shift, is_active",
     A_SCOPED + " (Admin-level sees all)",
     "{count, month_year, trackers (per day), month_summary}",
     "BillableReport.jsx, AgentBillableReport.jsx, billableReportService.js"],
    ["POST /tracker/eod-report/list", "Tasks that can be reported for a date range (Task EOD report)",
     "logged_in_user_id*, from_date, to_date",
     A_NOAGENT + " (the 403 text says AM, PM and Admin only, but the code only blocks Agent)",
     "Task list with counts for the range", "projectService.js (Task EOD Report)"],
    ["POST /tracker/eod-report/trackers", "Valid and invalid tracker files for one task and day",
     "logged_in_user_id*, task_id*, project_id*, date*", A_NOAGENT,
     "{total_all, total_valid, total_invalid, valid_trackers, invalid_trackers}", "projectService.js"],
    ["POST /tracker/eod-report/generate", "Merge the day's tracker files into one report",
     "logged_in_user_id*, task_id*, project_id*, date*", A_NOAGENT,
     "Excel file download (400 with failed_files if a file is unreachable)", "projectService.js"],
])

group("Dashboard", None, [
    ["POST /dashboard/filter", "Dashboard summary for the caller's scope",
     "logged_in_user_id*, device_id*, device_type*, user_id, project_id, task_id, date, date_from, date_to",
     A_SCOPED + " (Admin-level sees all); a user_id outside the scope is refused",
     "{logged_in_role, filters_applied, summary, users, projects, tasks, tracker}",
     "AdminDashboard.jsx, AssistantManagerDashboard.jsx, OverviewTab.jsx, QAAgentDashboard.jsx"],
])

group("Monthly goals and reports", None, [
    ["POST /project_monthly_tracker/add", "Add monthly target(s) for a project",
     "project_id*, month_year*, monthly_target*, created_date, logged_in_user_id (object or list of objects)",
     A_ATL, "{project_monthly_tracker_ids, skipped_count, skipped}", "ProjectMonthlyReport.jsx"],
    ["POST /project_monthly_tracker/update", "Edit a project monthly target",
     "project_monthly_tracker_id*, project_id, month_year, monthly_target, created_date, is_active, "
     "logged_in_user_id", A_ATL, "Success message", "ProjectMonthlyReport.jsx"],
    ["POST /project_monthly_tracker/delete", "Delete a project monthly target",
     "project_monthly_tracker_id*, logged_in_user_id", A_ATL, "Success message", "ProjectMonthlyReport.jsx"],
    ["POST /project_monthly_tracker/list", "Project targets with achieved production",
     "project_monthly_tracker_id, project_id, month_year, project_name, task_id, user_id, date_from, date_to, "
     "limit, offset", A_NONE, "Records with targets and totals", "ProjectMonthlyReport.jsx"],
    ["GET/POST /project_monthly_tracker/tasks", "Tasks planned for a project and month",
     "project_id*, month_year* (JSON body)", A_NONE, "{tasks: [...]}", "-"],
    ["POST /user_monthly_tracker/add", "Add monthly goals for agents",
     "user_id*, month_year*, monthly_target*, working_days*, extra_assigned_hours, created_date, "
     "logged_in_user_id (object or list)",
     "Super Admin, Admin, PM, Asst Manager (Asst Team Leader blocked); checked only if logged_in_user_id is sent",
     "Inserted ids and skipped rows", "-"],
    ["POST /user_monthly_tracker/update", "Edit an agent's monthly goal",
     "user_monthly_tracker_id*, user_id, month_year, monthly_target, extra_assigned_hours, logged_in_user_id", A_ROSTER + "; checked only if logged_in_user_id is sent",
     "Success message", "UserMonthlyReport.jsx"],
    ["POST /user_monthly_tracker/delete", "Delete an agent's monthly goal",
     "user_monthly_tracker_id*", A_NONE, "Success message", "UserMonthlyReport.jsx"],
    ["POST /user_monthly_tracker/list", "Monthly goals with progress for agents in scope",
     "logged_in_user_id*, month_year, user_id, team_id",
     "Any logged-in user; Admin-level all, Agent self, Asst Team Leader by team, others by assignment",
     "List of agents with goal, extra hours and achievement", "UserMonthlyReport.jsx"],
    ["POST /user_monthly_report/list_users", "Agents that appear in the monthly report",
     "logged_in_user_id*, month_year, team_id", "Same scope rules as user_monthly_tracker/list",
     "List of users", "UserMonthlyReport.jsx"],
    ["POST /user_monthly_report/list", "Monthly report rows per agent",
     "logged_in_user_id*, month_year, user_id, team_id", "Same scope rules as user_monthly_tracker/list",
     "Monthly report rows", "billableReportService.js"],
])

group("KRA", None, [
    ["POST /kra/users", "Agents whose KRA the caller can open",
     "logged_in_user_id*, month_year*",
     "Any role; Agent sees self, Asst Manager and QA their agents, Admin-level all",
     "{users: [...]}", "kraService.js (KRA screen)"],
    ["POST /kra/report", "KRA score card for one agent and month",
     "logged_in_user_id*, user_id (defaults to caller), month_year* (SEP2026 or later)",
     "Same scope as kra/users; otherwise 403", "KRA report", "kraService.js"],
    ["POST /kra/save_notes", "Save reviewer notes on a KRA",
     "logged_in_user_id*, user_id, month_year*, notes", "Same scope as kra/users; otherwise 403",
     "Updated KRA report", "kraService.js"],
    ["POST /kra/export", "Export the KRA to Excel",
     "logged_in_user_id*, user_id, month_year*", "Same scope as kra/users; otherwise 403",
     "Excel file download", "kraService.js"],
])

group("QC (Python side: qc, qc_audit, qc_rework, qc_history_user)", None, [
    ["GET/POST /qc/assign-daily-hours", "Daily job: assign hours per agent from roster and tenure; auto QC 100%",
     "none (Authorization: Bearer CRON_SECRET when that variable is set)",
     "CRON_SECRET bearer token when configured, otherwise none",
     "{status: true, message, data: {date, month_year, assigned_count, auto_qc_count, ...}}",
     "- (scheduler.py, assign_daily_hours.py, Vercel cron; see section 4)"],
    ["GET/POST /qc/send-billable-report", "Email yesterday's billable hours report (manual only)",
     "none (Authorization: Bearer CRON_SECRET when that variable is set)",
     "CRON_SECRET bearer token when configured, otherwise none",
     "{status: true, message, data: result of the report run}", "-"],
    ["POST /qc/temp-qc", "Save a day's QC score or assigned hours for an agent",
     "user_id*, date* (YYYY-MM-DD), logged_in_user_id*, qc_score, assigned_hours (one of the last two)",
     "qc_score: QA or Asst Team Leader. assigned_hours: Admin, Super Admin, PM, Asst Manager",
     "{status, message, data} (boolean status)", "qcService.js (Billable report - Add/Edit QC)"],
    ["POST /qc_audit/add", "Record a QC audit of a QC record",
     "multipart: qc_record_id*, qc_score*, error_notes, qc_checked_file (file)", A_NONE,
     "201 'QC audit created'", "QAAgentAudit.jsx"],
    ["GET /qc_audit/test", "Deployment smoke test", "-", A_NONE, "{status, message, timestamp}", "-"],
    ["POST /qc_audit/report", "QC audit report rows",
     "logged_in_user_id, start_date, end_date, qc_start_date, qc_end_date (default: current month)",
     "Any caller; QA and Asst Team Leader get only audits on their own QC (qr.qa_user_id)",
     "{count, records}", "QAAgentAudit.jsx, QAIndividualAuditReport.jsx"],
    ["GET /qc_audit/download_annotated/<qc_id>", "Download the QC sample with errors marked",
     "qc_id in the URL", A_NONE, "Excel file download", "QAAgentAudit.jsx (fallback to the Node route)"],
    ["POST /qc_rework/add_rework_file", "Agent uploads a fixed (rework) file",
     "multipart: qc_record_id*, rework_file_path* (file)", A_NONE,
     "{rework_file_path: URL}", "AgentQCReport.jsx"],
    ["POST /qc_rework/view_all_qc_history", "Full QC history with rework and correction rounds",
     "none", A_NONE, "{count, records} (each with qc_rework and qc_correction)", "QAAgentQCFormReport.jsx"],
    ["POST /qc_rework/view_pending_qc_files", "QC files still pending review (dashboard)",
     "none", A_NONE, "{count, record: [...]}", "QAAgentList.jsx"],
    ["POST /qc_history_user/view_qc_history_user_based", "QC history limited to the caller's scope",
     "logged_in_user_id*", "Any logged-in user; Admin-level all, QA, Asst Manager, Team Leader by scope (with scope = qc, Asst Team Leader like a QA)",
     "{count, records}", "ManagerQCReportsOverview.jsx, AgentQCReportPage.jsx"],
    ["POST /qc_history_user/consolidated_qc_report", "Consolidated QC report for a date range",
     "logged_in_user_id*, start_date, end_date", "Same scope rules as above", "{count, records}",
     "ManagerQCReportsOverview.jsx, QAAgentQCFormReport.jsx"],
])

group("QA hours", None, [
    ["POST /qa_tracker/sync", "Rebuild a QA's hours from QC activity for a day",
     "logged_in_user_id*, work_date, qa_user_id",
     "Any logged-in user for self; managers (Admin-level, AM, ATL) for another QA",
     "{synced_rows, work_date, qa_user_id}", "-"],
    ["POST /qa_tracker/rebuild_hours", "Rebuild all QA hours from the go-live date",
     "logged_in_user_id*", "Super Admin, Admin, PM, Asst Manager", "{pairs, start_date}", "-"],
    ["POST /qa_tracker/add_entry", "Add manual QA hours (Feedback, Training, Reporting, Other)",
     "logged_in_user_id*, hours*, sub_activity or activity_type* (feedback, training, reporting, other), work_date, "
     "agent_id, project_id, notes, qa_user_id",
     "QA or Asst Team Leader for self (today only); Super Admin, Admin, PM, Asst Manager for any QA",
     "Entry and updated day", "qaTrackerService.js (QA Tracker)"],
    ["POST /qa_tracker/save", "Alias of add_entry", "Same as add_entry", "Same as add_entry", "Same as add_entry", "-"],
    ["POST /qa_tracker/update_entry", "Edit a manual QA entry",
     "logged_in_user_id*, qa_tracker_id*, work_date, hours, notes, agent_id, project_id",
     "Super Admin, Admin, PM, Asst Manager", "Updated entry", "qaTrackerService.js"],
    ["POST /qa_tracker/delete_entry", "Delete a manual QA entry",
     "logged_in_user_id*, qa_tracker_id*",
     "Owner within 24 hours; Super Admin, Admin, PM, Asst Manager any time", "Updated day", "qaTrackerService.js"],
    ["POST /qa_tracker/entries", "List manual QA entries",
     "logged_in_user_id*, start_date, end_date, qa_user_id, activity_type",
     "Self; managers and Asst Team Leader for other QAs", "List of entries", "qaTrackerService.js"],
    ["POST /qa_tracker/day", "One QA's day view with hours by activity",
     "logged_in_user_id*, work_date, qa_user_id", "Self; managers and Asst Team Leader for other QAs",
     "Day payload", "qaTrackerService.js"],
    ["POST /qa_tracker/list", "QA hours for a day, range or month",
     "logged_in_user_id*, month_year, start_date, end_date, qa_user_id",
     "Self; managers and Asst Team Leader for other QAs", "List of QA rows with hours", "qaTrackerService.js"],
    ["POST /qa_tracker/monthly", "Monthly QA hours summary",
     "logged_in_user_id*, month_year*, start_date, end_date, qa_user_id",
     "Self; managers and Asst Team Leader for other QAs", "Monthly summary", "qaTrackerService.js"],
])

group("Holidays", None, [
    ["POST /holiday/list", "List holidays", "logged_in_user_id*, calendar_year, include_inactive",
     "Any user that exists (view-only for all roles)", "List of holidays", "holidayService.js (Holiday Master)"],
    ["POST /holiday/add", "Add a holiday", "logged_in_user_id*, holiday_date*, holiday_name*, calendar_year",
     A_ADMIN, "201 with holiday_id", "holidayService.js"],
    ["POST /holiday/update", "Edit a holiday",
     "logged_in_user_id*, holiday_id*, holiday_date, holiday_name, calendar_year, is_active", A_ADMIN,
     "Success message", "holidayService.js"],
    ["POST /holiday/delete", "Deactivate a holiday", "logged_in_user_id*, holiday_id*", A_ADMIN,
     "Success message", "holidayService.js"],
    ["POST /holiday/upload", "Bulk upload holidays from Excel",
     "multipart: logged_in_user_id*, calendar_year*, file* (or holiday_file)", A_ADMIN,
     "{inserted, updated, skipped}", "holidayService.js"],
])

group("Roster", None, [
    ["POST /roster/can_generate", "Check whether a roster can be generated now",
     "logged_in_user_id*, month_year", A_ROSTER, "Availability flags", RS],
    ["POST /roster/generate", "Generate rosters for employees in scope that have none (without month_year only "
     "allowed in the last week of the month)",
     "logged_in_user_id*, month_year", A_ROSTER, "Generation summary", RS],
    ["POST /roster/generate_employee", "Generate the roster for one employee",
     "logged_in_user_id*, user_id*, month_year*", A_ROSTER + "; only for employees in scope",
     "Employee roster result", RS],
    ["POST /roster/reset_regenerate", "Delete and regenerate a whole roster month",
     "logged_in_user_id*, month_year*, confirm_reset* (true)", A_ADMIN, "Reset and regeneration summary", RS],
    ["POST /roster/reset_regenerate_employee", "Delete and regenerate one employee's roster",
     "logged_in_user_id*, user_id*, month_year*, confirm_reset* (true)", A_ADMIN, "Reset and regeneration result", RS],
    ["POST /roster/list_employees", "Employees in the caller's roster scope",
     "logged_in_user_id*, month_year*, team_id", "All roles except Agent and QA", "{employees: [...]}", RS],
    ["POST /roster/list", "Roster months (optionally with day rows)",
     "logged_in_user_id*, month_year*, user_id, include_days", A_ROSTER_SCOPED + "; Admin-level sees all",
     "Rosters with days, leaves, metrics and read_only flag", RS],
])

group("Roster workflow (approval, locks, emails, Excel)",
      "These routes are added to the /roster blueprint from routes/roster_workflow.py, which app.py imports "
      "before registering the blueprint. All need logged_in_user_id*.", [
    ["POST /roster/weekoff/swap_preview", "Preview a week-off swap",
     "logged_in_user_id*, roster_month_id*, week_off_dates", A_ROSTER + "; for employees in scope",
     "Preview of changes", RS],
    ["POST /roster/change_request/create", "Create a draft roster change (leave, week-off, half day...)",
     "logged_in_user_id*, roster_month_id*, change_type*, change_payload (start_date, end_date...)",
     A_ROSTER + "; for employees in scope", "201 with request_id", RS],
    ["POST /roster/change_request/withdraw_draft", "Withdraw a draft change",
     "logged_in_user_id*, request_id*, withdraw_comment", A_ROSTER + "; own drafts (Admin-level any)",
     "Success message", RS],
    ["POST /roster/submit", "Submit draft changes for approval as one batch",
     "logged_in_user_id*, month_year*, week_number, submitter_comment", A_ROSTER, "Batch id and counts", RS],
    ["POST /roster/withdraw", "Withdraw a submitted batch back to Draft",
     "logged_in_user_id*, batch_id or month_year*, withdraw_comment", A_ROSTER,
     "{cancelled_requests}", RS],
    ["POST /roster/requests/approve", "Approve one change request",
     "logged_in_user_id*, request_id*, reviewer_comment", A_ADMIN, "Success message", RS],
    ["POST /roster/requests/approve_bulk", "Approve many requests or a whole month",
     "logged_in_user_id*, request_ids, approve_all, month_year (needed with approve_all), reviewer_comment",
     A_ADMIN, "Approved counts", RS],
    ["POST /roster/requests/reject", "Reject one change request",
     "logged_in_user_id*, request_id*, reviewer_comment*", A_ADMIN, "Success message", RS],
    ["POST /roster/requests/list", "List change requests",
     "logged_in_user_id*, status, batch_id, month_year", "Any logged-in user; Agent and QA own only, "
     "managers in scope, Admin-level all", "List of requests", RS],
    ["POST /roster/leave/list", "Leaves of a roster month",
     "logged_in_user_id*, roster_month_id*", "Agent and QA own only; managers in scope; Admin-level all",
     "List of leaves", RS],
    ["POST /roster/lock", "Lock a whole month calendar", "logged_in_user_id*, month_year*", A_ADMIN,
     "Success message", RS],
    ["POST /roster/unlock", "Unlock a month",
     "logged_in_user_id*, month_year or roster_month_id*", A_ADMIN, "Success message with restored status", RS],
    ["POST /roster/week/lock", "Lock one week", "logged_in_user_id*, month_year*, week_number*", A_ADMIN,
     "Success message", RS],
    ["POST /roster/week/unlock", "Unlock one week", "logged_in_user_id*, month_year*, week_number*", A_ADMIN,
     "Success message", RS],
    ["POST /roster/week/locks", "List week locks of a month", "logged_in_user_id*, month_year*",
     "Roster managers, Admin-level, Agent, QA (everyone)", "{week_locks: [...]}", "-"],
    ["POST /roster/notify_approval", "Email the approval notification for a week",
     "logged_in_user_id*, month_year*, week_number", "Super Admin only", "Email result", RS],
    ["POST /roster/week/email", "Send the weekly roster email",
     "logged_in_user_id*, month_year*, week_number*", A_ADMIN + ", PM", "{weekly_roster_emails: [...]}", RS],
    ["POST /roster/versions/list", "Version history of a roster month",
     "logged_in_user_id*, roster_month_id*", "Agent and QA own only; others no check", "List of versions", "-"],
    ["POST /roster/versions/detail", "One version snapshot", "logged_in_user_id*, version_id*", A_NONE,
     "Snapshot JSON", "-"],
    ["POST /roster/audit/list", "Roster audit log", "logged_in_user_id*, roster_month_id",
     "Any logged-in user; Agent and QA see own rows only", "Audit rows", RS],
    ["POST /roster/recalculate", "Recalculate roster metrics (preview)", "logged_in_user_id*, roster_month_id*",
     A_NONE, "Metrics", RS],
    ["POST /roster/excel/weeks", "Weeks available for the Excel template",
     "logged_in_user_id*, month_year*", A_ROSTER, "List of weeks", RS],
    ["POST /roster/excel/template", "Download a roster Excel template",
     "logged_in_user_id*, month_year, week_number, all_weeks, week_start, team_id, prefill", A_ROSTER,
     "Excel file download", RS],
    ["POST /roster/excel/preview", "Preview an uploaded roster Excel",
     "multipart: logged_in_user_id*, file* (or roster_file), team_id", A_ROSTER, "Preview of changes", RS],
    ["POST /roster/excel/apply", "Apply an Excel (or JSON changes) as draft change requests",
     "multipart: logged_in_user_id*, file* (or roster_file), team_id; or JSON: changes*", A_ROSTER,
     "Created change counts", RS],
])

group("SOP library", None, [
    ["POST /sop/list", "Load the SOP library (topics and items)", "logged_in_user_id*", "Any logged-in user",
     "{topics, can_manage}", "SopLibrary.jsx (SOP Library)"],
    ["POST /sop/topic/save", "Add or rename an SOP topic",
     "logged_in_user_id*, title*, description, sop_topic_id (to edit)", "Super Admin, Admin, PM",
     "{topics: [...]}", "SopLibrary.jsx"],
    ["POST /sop/topic/delete", "Remove a topic", "logged_in_user_id*, sop_topic_id*",
     "Super Admin, Admin, PM", "{topics: [...]}", "SopLibrary.jsx"],
    ["POST /sop/item/save", "Add or edit an SOP link or file",
     "JSON or multipart: logged_in_user_id*, title*, sop_topic_id*, item_type* (link/file), link_url, file (file), "
     "sop_item_id (to edit)", "Super Admin, Admin, PM", "{topics: [...]}", "SopLibrary.jsx"],
    ["POST /sop/item/delete", "Remove an SOP item", "logged_in_user_id*, sop_item_id*",
     "Super Admin, Admin, PM", "{topics: [...]}", "SopLibrary.jsx"],
])

group("Report emails", None, [
    ["POST /report_email/list", "List report email recipients", "logged_in_user_id*", "Super Admin only",
     "List of recipients with send flags", "ReportEmails.jsx (Manage - Report Emails)"],
    ["POST /report_email/add", "Add a recipient",
     "logged_in_user_id*, email*, recipient_type (or type), send_billable, send_tracker, send_tracker_full",
     "Super Admin only", "Created recipient", "ReportEmails.jsx"],
    ["POST /report_email/update", "Edit a recipient",
     "logged_in_user_id*, recipient_id*, email*, recipient_type, send_billable, send_tracker, send_tracker_full",
     "Super Admin only", "Updated recipient", "ReportEmails.jsx"],
    ["POST /report_email/delete", "Remove a recipient", "logged_in_user_id*, recipient_id*", "Super Admin only",
     "Success message", "ReportEmails.jsx"],
])

group("API logs", None, [
    ["POST /api_log_list/logs", "List API call logs (tracker and monthly-goal actions)", "none", A_NONE,
     "All rows of api_call_logs with a readable action text", "-"],
])


def _flask_blocks():
    blocks = [
        ("h", "2. Flask API"),
        ("p", "Registered in backend-api/app.py: 25 blueprints under the url prefixes shown in the paths "
              "(/auth, /user, /project, /project_category, /dropdown, /task, /tracker, /permission, /dashboard, "
              "/project_monthly_tracker, /user_monthly_tracker, /api_log_list, /password_reset, /qc, /qc_afd, "
              "/qc_audit, /qc_rework, /qc_history_user, /user_monthly_report, /holiday, /roster, /report_email, "
              "/qa_tracker, /kra, /sop) plus / and /health. Access is described as the code enforces it; most "
              "checks depend on the caller sending a truthful logged_in_user_id."),
    ]
    for title, intro, rows in FLASK_GROUPS:
        blocks.append(("h2", title))
        if intro:
            blocks.append(("p", intro))
        blocks.append(table(rows))
    return blocks


# =========================================================================================
# 3. NODE QC API
# =========================================================================================
NODE_GROUPS = []


def ngroup(title, intro, rows):
    NODE_GROUPS.append((title, intro, rows))


NODE_SAVE_FIELDS = ("logged_in_user_id, tracker_id*, qa_user_id*, project_id*, task_id*, agent_id, "
                    "assistant_manager_id, whole_file_path, qc_file_path, date_of_file_submission, qc_score, "
                    "file_record_count, qc_generated_count, qc_file_records, error_list, error_score, comments")

ngroup("Health and users", None, [
    ["GET /api/v1", "Banner check", "-", A_NONE, "Plain text 'Hello, TFS QC Eval Backend!'", "-"],
    ["GET /api/v1/health", "Liveness check", "-", A_NONE, "{status: 'ok', timestamp, uptime}", "-"],
])

ngroup("Tracker processing and duplicate check", None, [
    ["GET /api/v1/tracker/view", "Fetch trackers via Flask POST /tracker/view and attach each task's important columns",
     "JSON body even though it is a GET: user_id or logged_in_user_id, plus the /tracker/view filters", A_NONE,
     "{success, data: tracker data, processedFiles}", "- (the frontend calls Flask /tracker/view directly)"],
    ["POST /api/v1/tracker/process-excel", "Read an uploaded .xlsx, hash rows and store them in tracker_records",
     "multipart: file* (.xlsx), project_id*, task_id*, user_id*, file_path, validate_only, duplicate_check. "
     "Without multipart it processes the files of trackers returned by Flask", A_NONE,
     "{success, data: {recordsInserted, duplicatesSkipped, validRecords, validationMode}}", "Tracker.jsx"],
])

ngroup("AI evaluation and Gemini key", None, [
    ["POST /api/v1/ai/evaluate", "Evaluate an Excel file with Gemini in batches of 50 rows",
     "multipart: file* (.xlsx or .xls, max 10 MB), user_id*, project_id*, task_id*, gemini_api_key",
     "Any existing user with a designation (the 403 text says Agents only)",
     "{success, message, data: aggregated AI result}", "Tracker.jsx, AIEvaluation.jsx"],
    ["POST /api/v1/ai/duplicate-check", "Check a file's rows against all stored hashes",
     "multipart: file* (max 10 MB), user_id*, project_id*, task_id*",
     "Any existing user with a designation (the 403 text says Agents only)",
     "{success, data: {hasDuplicates, duplicateCount, duplicates (first 10), totalRecords, uniqueRecords}}",
     "Tracker.jsx, AIEvaluation.jsx"],
    ["POST /api/v1/gemini-key/save", "Store the user's Gemini key (encrypted)", "user_id*, gemini_api_key*",
     A_NONE, "Success message", "agentService.js"],
    ["POST /api/v1/gemini-key/get", "Fetch the user's Gemini key", "user_id*", A_NONE,
     "{success, hasKey, gemini_api_key} - the key is returned decrypted", "agentService.js"],
    ["POST /api/v1/gemini-key/delete", "Remove the user's Gemini key", "user_id*", A_NONE,
     "Success message", "agentService.js"],
])

ngroup("QC records and samples", None, [
    ["POST /api/v1/qc-records/generate-sample", "Build the QC sample (percentage of rows) from the tracker file",
     "tracker_id*, logged_in_user_id, sampling_percentage", A_NONE,
     "{data: {total_records, sampling_percentage, sample_size, sample_data, remaining_data}}",
     "qcService.js (QCFormPage.jsx, QAAgentList.jsx)"],
    ["POST /api/v1/qc-records/lookup-row", "Load one extra row that is not in the sample",
     "tracker_id*, logged_in_user_id, excel_row or qc_code", A_NONE,
     "{data: {excel_row, record, used_rework_file}}", "qcService.js (QC form)"],
    ["GET /api/v1/qc-records/download-sample/:tracker_id", "Download the QC sample as Excel",
     "tracker_id in the URL; query: logged_in_user_id, sampling_percentage", A_NONE, "Excel file download",
     "QCFormPage.jsx (direct URL)"],
    ["GET /api/v1/qc-records/download-annotated/:id", "Download the QC sample with errors marked",
     "id (qc record) in the URL", A_NONE, "Excel file download", "QAAgentAudit.jsx"],
    ["POST /api/v1/qc-records/save", "Generic QC save (older route, handles regular and rework)",
     NODE_SAVE_FIELDS + ", status, qc_status, sampling_percentage", A_NONE,
     "{success, message}; emails the agent", "-"],
    ["GET /api/v1/qc-records/list", "QC records, one per QA per day, excluding audited days",
     "query: logged_in_user_id (limits to that agent)", A_NONE, "{success, data: list of records}",
     "AgentQCReport.jsx, QAAgentAudit.jsx, qcService.js (QCFormReportView.jsx)"],
    ["GET /api/v1/qc-records/view/:id", "One QC record", "id in the URL", A_NONE, "{success, data: record}", "-"],
    ["PUT /api/v1/qc-records/update/:id", "Edit score, status or errors of a record",
     "id in the URL; body: qc_score, status, error_score, error_list", A_NONE, "Success message", "-"],
    ["POST /api/v1/qc-records/agent-upload", "Agent uploads the fixed file for a rework or correction",
     "multipart: file*, qcId*, type* (rework or correction), logged_in_user_id", A_NONE,
     "{data: {fileUrl}} (stored in Cloudinary)", "AgentQCReportPage.jsx"],
])

ngroup("QC save - regular / correction / rework", None, [
    ["POST /api/v1/qc-regular/save", "Save the first QC of a tracker (also closes an active rework or correction round)",
     NODE_SAVE_FIELDS, A_NONE,
     "{success, message}; 400 if a record exists with no active round; emails the agent",
     "qcService.js (QCFormPage.jsx), QAAgentList.jsx"],
    ["GET /api/v1/qc-regular/list", "List regular QC records",
     "query: logged_in_user_id (limits to that agent)", A_NONE, "{success, data: rows}", "-"],
    ["POST /api/v1/qc-correction/save", "Save a correction round",
     "logged_in_user_id*, tracker_id*, qa_user_id*, project_id*, task_id*, plus the QC fields above and "
     "status (correction by default; completed or regular closes it)", A_NONE,
     "{success, message}; emails the agent", "qcService.js, QAAgentList.jsx"],
    ["GET /api/v1/qc-correction/list", "List correction QC records",
     "query: logged_in_user_id", A_NONE, "{success, data: rows}", "-"],
    ["POST /api/v1/qc-rework/save", "Save a rework round (QC found errors in the fixed file)",
     "logged_in_user_id*, tracker_id*, qa_user_id*, project_id*, task_id*, plus the QC fields above", A_NONE,
     "{success, message}; emails the agent", "qcService.js, QAAgentList.jsx"],
    ["POST /api/v1/qc-rework/save-regular", "Close an active rework round (the fixed file passed QC)",
     "logged_in_user_id*, tracker_id*, qa_user_id*, project_id*, task_id*, plus the QC fields above", A_NONE,
     "{success, message}; 400 if no QC record or no active rework round", "-"],
    ["GET /api/v1/qc-rework/list", "List rework QC records", "query: logged_in_user_id", A_NONE,
     "{success, data: rows}", "-"],
])

ngroup("Mail", None, [
    ["POST /api/v1/mail/send-rework", "Send a QC notification email to an agent",
     "agent_email*, subject, message, status, agent_name, project_name, task_name, qc_agent_name, qc_score, "
     "error_count, error_list, comments", A_NONE, "{success, message}", "-"],
])


def _node_blocks():
    blocks = [
        ("h", "3. Node QC API"),
        ("p", "Express app in qc-backend/index.ts. All routers are mounted under /api/v1 (users, tracker, "
              "ai-evaluation, gemini-key, qc-records, qc-regular, qc-correction, qc-rework, mail). Files are "
              "kept in memory (multer) and QC samples are stored in Cloudinary. There is no auth middleware. "
              "Responses use {success, message, data}."),
    ]
    for title, intro, rows in NODE_GROUPS:
        blocks.append(("h2", title))
        if intro:
            blocks.append(("p", intro))
        blocks.append(table(rows))
    return blocks


# =========================================================================================
# 4. BACKGROUND JOBS
# =========================================================================================
JOBS = [
    ("h", "4. Background jobs that call the API"),
    ("p", "Only one endpoint is called by schedulers. /qc/assign-daily-hours writes the day's assigned hours "
          "from the roster and tenure and writes the automatic 100% QC score for yesterday. If CRON_SECRET is set "
          "in the Flask environment, callers must send 'Authorization: Bearer <CRON_SECRET>' (the value is in the "
          "Credentials Register, not here)."),
    ("table", ["Caller", "When", "Calls", "Auth", "Notes"], [
        ["scheduler.py (APScheduler inside the Flask process)", "Daily 08:00 (server time)",
         "POST {API_BASE_URL}/qc/assign-daily-hours",
         "Sends no Authorization header",
         "Started only when app.py is run directly (python app.py). If CRON_SECRET is set this call gets 401. "
         "API_BASE_URL defaults to http://127.0.0.1:5000."],
        ["assign_daily_hours.py (system cron)", "Suggested: 0 8 * * * (08:00 IST)",
         "GET {API_BASE_URL}/qc/assign-daily-hours",
         "Bearer CRON_SECRET when the variable is set",
         "Run from backend-api with API_BASE_URL set. Prints status and response."],
        ["vercel.json cron (backend-api)", "30 2 * * * UTC (08:00 IST)",
         "GET /qc/assign-daily-hours",
         "Vercel sends Bearer CRON_SECRET",
         "Only relevant if the Flask API is deployed on Vercel."],
        ["Manual trigger", "On demand",
         "GET or POST /qc/send-billable-report",
         "Bearer CRON_SECRET when the variable is set",
         "Runs billable_report_autosend.run_billable_report and emails the previous day's report. No schedule."],
        ["send_tracker_report.py, send_tracker_report_full_day.py, billable_report_autosend.py",
         "Run by cron or by hand on the server",
         "No API call",
         "n/a",
         "Standalone scripts: read MySQL directly and send email. Recipients come from the report_email table "
         "(managed by /report_email/*)."],
        ["qc-backend (Node) calling Flask", "On each request",
         "POST {PYTHON_URL}/tracker/view",
         "None",
         "Used by GET /tracker/view, POST /tracker/process-excel (without a file), /qc-records/generate-sample, "
         "/qc-records/lookup-row and /qc-records/download-sample. PYTHON_URL is set in the Node .env."],
    ]),
]

# =========================================================================================
# 5. UNREGISTERED OR UNUSED
# =========================================================================================
UNUSED = [
    ("h", "5. Unregistered or unused endpoints"),
    ("h2", "Not registered in app.py"),
    ("note", "routes/afd_master.py (blueprint prefix /qc/afd-master: create, update, delete, list) and "
             "routes/api_log.py (/log_api_call) are not imported or registered in app.py, so they are not "
             "reachable. AFD management uses /qc_afd/*; API call logging is written by utils/api_log_utils.py "
             "directly from the tracker and monthly-goal routes."),
    ("h2", "Flask endpoints the frontend never calls"),
    ("bullets", [
        "/ and /health (health checks).",
        "/qc/assign-daily-hours and /qc/send-billable-report (cron or manual only).",
        "/api_log_list/logs (no screen uses it yet).",
        "/project_monthly_tracker/tasks.",
        "/user_monthly_tracker/add (the screen only edits and deletes goals).",
        "/qa_tracker/sync, /qa_tracker/rebuild_hours and /qa_tracker/save (save is an alias of add_entry).",
        "/qc_afd/list_by_category and /qc_audit/test.",
        "/roster/week/locks, /roster/versions/list and /roster/versions/detail.",
    ]),
    ("h2", "Node endpoints the frontend never calls"),
    ("bullets", [
        "GET /api/v1, GET /api/v1/health and GET /api/v1/tracker/view.",
        "POST /api/v1/qc-records/save, GET /api/v1/qc-records/view/:id and PUT /api/v1/qc-records/update/:id "
        "(the frontend uses the three specific save routes instead).",
        "Removed on 23 Oct 2026 because nothing used them and they had no check: GET /api/v1/users (returned "
        "whole user rows) and DELETE /api/v1/qc-records/delete/:id.",
        "GET /api/v1/qc-regular/list, /qc-correction/list and /qc-rework/list.",
        "POST /api/v1/qc-rework/save-regular (the frontend sends rework screens to /qc-rework/save).",
        "POST /api/v1/mail/send-rework (emails are sent internally by the save routes).",
    ]),
    ("h2", "Frontend calls to routes that do not exist"),
    ("bullets", [
        "services/qcService.js defines functions that call Node routes which are not in qc-backend: "
        "/qc-afd/list, /qc-records/agent/:id, /qc-records/qa-agent/:id, /qc-records/pending-review/:id, "
        "/qc-records/upload-rework, /qc-records/upload-correction, /qc-records/all, /qc-records/statistics, "
        "/qc-records/review-rework and /qc-records/review-correction.",
        "None of those functions (fetchQCAFDList, getAgentQCRecords, getQAAgentQCRecords, getPendingReviews, "
        "uploadReworkFile, uploadCorrectionFile, getAllQCRecords, getQCStatistics, submitReworkQC, "
        "submitCorrectionQC) is used by any screen, so nothing breaks today. Treat them as dead code.",
    ]),
    ("h2", "Endpoints with no access check worth reviewing"),
    ("bullets", [
        "Node POST /gemini-key/get returns a user's Gemini key decrypted to anyone who sends the user_id (only "
        "a login token can fix this).",
        "Flask POST /user/list returns each user's decrypted password to every caller except Agent.",
        "Flask POST /api_log_list/logs, /task/add, /task/update, /task/delete and /user_monthly_tracker/delete "
        "have no role check at all.",
    ]),
]

# =========================================================================================
# ASSEMBLY
# =========================================================================================
API_REFERENCE = {
    "number": "07",
    "title": "API Reference",
    "audience": "Developers",
    "blocks": CONVENTIONS + _flask_blocks() + _node_blocks() + JOBS + UNUSED,
}


def _count(groups):
    seen = set()
    for _title, _intro, rows in groups:
        for row in rows:
            seen.add(row[0])
    return len(seen)


FLASK_ENDPOINT_COUNT = _count(FLASK_GROUPS)
NODE_ENDPOINT_COUNT = _count(NODE_GROUPS)

if __name__ == "__main__":
    print("blocks:", len(API_REFERENCE["blocks"]))
    print("Flask endpoints documented:", FLASK_ENDPOINT_COUNT)
    print("Node endpoints documented:", NODE_ENDPOINT_COUNT)

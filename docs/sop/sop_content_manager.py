"""Detailed SOP content for managers. Block format: see sop_content_qc_roster.py."""

PROJECTS_TASKS = {
    "file": "SOP - Manager - Projects and Tasks",
    "title": "Projects & Targets (Projects and Tasks)",
    "roles": "Project Manager, Assistant Manager, Admin, Super Admin",
    "blocks": [
        ("h", "1. Purpose"),
        ("p", "Projects and tasks decide who works on what, the hourly target per task, how much of each file QA "
              "checks, how QA hours are counted, and which SOP links agents and QA can open."),

        ("h", "2. Screen guide - Projects & Targets"),
        ("img", "proj_02_project_tasks", "Project Management"),
        ("table", ["Part", "What it does"], [
            ["Add Project", "Create a new project."],
            ["Search Project / Status", "Find a project by name; show All, Active or Inactive."],
            ["Projects list (left)", "Each project with its number of tasks and Active / Inactive. Click to open it."],
            ["Files", "Project files and SOP links (download / open)."],
            ["Edit", "Change project details, people and SOP links."],
            ["Status switch", "Make the project Active or Inactive. Inactive projects disappear from agents' lists."],
            ["Delete", "Removes a project that was never used. Projects with tracker history are deactivated instead."],
            ["Add Task", "Create a task in this project."],
            ["Task table", "Task Name, Target / Hr, QC Target (QA hour criteria, e.g. '10 min / file'), Description, "
                           "Status switch and Actions (edit, delete)."],
        ]),
        ("img", "proj_03_files_dropdown", "Files - project files and SOP links"),

        ("h", "3. Procedure - Create or edit a project"),
        ("steps", [
            ("Click Add Project (or Edit on a project).", "proj_01_add_project", "Create New Project"),
            "Fill Project Name and Project Code (required) and an optional Description.",
            "Project Category decides the QC error list (AFD) QA uses. Pick the right one.",
            "Choose the Project Manager, Assistant Project Manager(s) (required), Quality Analyst(s) (required; QA or Assistant Team Leader) and "
            "Agent(s) (required). Only these agents see the project in their tracker; only these QAs get its files.",
            "Requires AI Evaluation: agents must run AI Evaluation on the file before submitting. Requires Duplicate "
            "Check: rows already submitted are rejected.",
            "Project Files: attach reference files (on Add Project).",
            ("SOP Links (shared drive): type a title, paste the link and click Add link. Share the file on the drive as "
             "Viewer first. Agents see it under Project Name on Add Tracker; QA sees it on the QC form.",
             "mgr_03_edit_project", "Edit Project - SOP Links"),
            "Click Create Project / Update Project.",
        ]),

        ("h", "4. Procedure - Add or edit a task"),
        ("steps", [
            ("Open the project and click Add Task (or the edit icon on a task).", "proj_04_add_task", "Add Task"),
            "Task Name and Target (units per hour at tenure 1.0) are required. Add an optional Task Description.",
            "Generate Data for QC: the percentage of each file QA checks (for example 10%).",
            "Sample File (Excel only): upload an example file. Its column names fill Important Columns.",
            ("QA hour criteria: set only ONE type - 1. Minutes per QC record, 2. Minutes per file, or 3. Object count "
             "ranges (a count column summed over the file, then minutes per min-max range). Entering one type clears "
             "the others; the type in use shows 'IN USE'. Leave all blank if QA hours should not be counted for "
             "this task.", "proj_07_edit_task_bottom", "Edit Task - QA hour criteria in use, Important Columns, Team"),
            "Important Columns: the columns QA sees on the QC form (pick from the sample file's columns).",
            "Team (Agents) (required): the agents who can log this task.",
            ("Click Submit (Add) or Save Changes (Edit).", "proj_05_add_task_bottom", "Add Task - bottom of the form"),
        ]),

        ("h", "5. Rules to remember"),
        ("bullets", [
            "An agent's target = task Target x the agent's tenure (from User Management).",
            "QC % decides how many rows QA checks: rows x QC %, rounded up.",
            "Only one QA hour criteria type can be active for a task.",
            "Deactivate a task or project instead of deleting it once it has been used.",
        ]),

        ("h", "6. Common problems"),
        ("table", ["Problem", "What to do"], [
            ["Agent cannot see the project or task", "Check they are in Agent(s) and the task's Team, and both are Active."],
            ["QA sees no files", "Check the QA is in Quality Analyst(s)."],
            ["QA sees no errors to choose", "Set the Project Category; it must be linked to an AFD."],
            ["Important Columns says 'Upload Excel file first'", "Upload the Sample File."],
            ["SOP link opens 'Request access'", "Share the drive file with the team as Viewer."],
        ]),
    ],
}


MANAGER_REPORTS = {
    "file": "SOP - Manager - Reports",
    "title": "Analytics and Reports (Managers, Admin and Super Admin)",
    "roles": "Project Manager, Assistant Manager, Admin, Super Admin",
    "blocks": [
        ("h", "1. Purpose"),
        ("p", "Analytics shows the team's billable hours, monthly goals, QA hours and KRA. Managers also correct "
              "tracker entries and monthly goals here."),

        ("h", "2. Overview"),
        ("p", "Analytics opens on Overview. It is a quick health check of the selected dates: how many people "
              "worked, how many hours they billed against the hours they were given, and the latest files uploaded."),
        ("img", "mgr_01_overview", "Overview - date filter and summary cards"),
        ("h2", "2.1 Date Range Filter"),
        ("steps", [
            "Overview opens on today (From and To are both today's date).",
            "Pick a From and a To date to see a longer period, for example the whole week or month. The cards and the "
            "file list reload straight away.",
            "Click Reset to Today to go back to today.",
        ]),
        ("h2", "2.2 The cards"),
        ("table", ["Card", "What it shows", "How it is worked out"], [
            ["Total Active Agents", "How many people worked in the selected dates.",
             "Counts each person who added at least one tracker entry in those dates (each person once). People "
             "on leave or with no tracker entry are not counted, so on a holiday it can be low."],
            ["Total Billable Hours", "Billable hours / Assigned hours, for example 51.21 / 216.00.",
             "Billable = total billable hours from the tracker entries in those dates. Assigned = total assigned "
             "hours of those people on the days they worked (the same assigned hours shown in the Billable Report)."],
        ]),
        ("bullets", [
            "A big gap between billable and assigned hours means trackers are missing or production is low. Open "
            "Billable Report > Daily Report to see which agent and which day.",
            "Assigned hours come from the roster and the daily assigned hours. If a person shows the wrong assigned "
            "hours, check their roster day first.",
        ]),
        ("h2", "2.3 Latest QC Files"),
        ("img", "rep_11_overview_qc_files", "Latest QC Files"),
        ("p", "The five most recent tracker entries in the selected dates that have a file attached, newest first. "
              "Each row shows:"),
        ("table", ["Column", "Meaning"], [
            ["Date/Time", "When the agent added the tracker entry."],
            ["Agent", "Who uploaded the file."],
            ["Project / Task", "The project and task of the entry."],
            ["File - Download", "Downloads the agent's uploaded file so you can open it."],
        ]),
        ("note", "This list shows the latest uploaded files, whether or not QA has checked them yet. To see QC "
                 "results and scores use QC Report Overview (see SOP - Manager - QC Report Overview and QA Audit)."),
        ("h2", "2.4 What each role sees"),
        ("table", ["Role", "People included"], [
            ["Admin, Super Admin, Project Manager", "All active users."],
            ["Assistant Manager / Assistant Team Leader", "Only the people assigned to you (your team)."],
        ]),

        ("h", "3. Billable Report"),
        ("h2", "3.1 Daily Report"),
        ("img", "rep_04_billable_agent_daily", "Daily Report - agent list and the selected agent's days"),
        ("steps", [
            "Filter with Search Agent, From / To, Select Month and Team. Reset Filters clears them; the download icon "
            "exports all agents' days (with Tenure for admins and managers).",
            "Click an agent on the left (hours, QC and tracker count shown) to see their days: Day Status, Assign "
            "Hours, Worked Hours, QC Score, Tracker Count and Daily Required Hours. Export downloads that agent.",
            ("To correct a day's assigned hours click the edit icon, change Assign Hours and click Update Entry.",
             "rep_10_billable_day_edit", "Edit Daily Entry"),
        ]),
        ("h2", "3.2 Monthly Report"),
        ("img", "mgr_05_billable_monthly", "Monthly Report"),
        ("p", "Per agent: Billable Hour Delivered, Monthly Goal, Pending Target and Avg. QC Score. Export Month "
              "downloads the table (with Tenure for admins and managers)."),

        ("h", "4. QA Report"),
        ("img", "mgr_08_qa_report", "QA Report - Daily Report"),
        ("bullets", [
            "Tracker: QA's non-QC work entries. Daily Report / Monthly Report: QA hours per day / month.",
            "Columns: QC Hours, Rework Hour, Feedback, Reporting, Total / 9H, Files, Late Files (QC done after the "
            "deadline) and QC Record. Filter by dates, month and QA; Export downloads it.",
            "QC hours come from the task's QA hour criteria (see SOP - Manager - Projects and Tasks).",
        ]),

        ("h", "5. User Monthly Goal"),
        ("img", "rep_03_user_monthly_edit", "User Monthly Goal - editing a row"),
        ("steps", [
            "Pick the month (or All Months). Each month lists users with Team, Monthly Target, Extra Assign Hours and "
            "Working Days (from the roster).",
            "Click the pencil to edit Monthly Target and Extra Assign Hours. Use a minus value (for example -18) to "
            "reduce the goal. Save with the green tick or cancel with x.",
            "Search users, filter by team and Export the month.",
        ]),
        ("bullets", ["Monthly Goal = Monthly Target + Extra Assign Hours. It cannot go below 0."]),

        ("h", "6. Project Monthly Report"),
        ("img", "mgr_07_project_monthly_report", "Project Monthly Report"),
        ("p", "Monthly hours and targets by project."),

        ("h", "7. KRA"),
        ("img", "mgr_09_kra", "KRA - choose the person"),
        ("bullets", [
            "Choose the Month and the person. Cards show Productivity 33%, Quality 33%, Roster 10%, Reporting 14% and "
            "the KRA %.",
            "The table lists every day: attendance, billable hours, productivity, QC score, quality, trackers.",
            "Add a note on any day and click Save notes. Excel downloads the KRA.",
        ]),

        ("h", "8. Tracker Report - view and correct entries"),
        ("img", "mgr_10_tracker_report", "Tracker Report"),
        ("steps", [
            "Filter by Agents, Team, Project, Tasks and dates. The table shows every entry with target, production, "
            "billable hours, notes, file and shift. Export downloads the filtered list; Refresh reloads it.",
            ("Edit (pencil): change the date and time, project, task, shift, production, notes or file, then Update "
             "Tracker.", "rep_01_tracker_edit", "Edit Tracker"),
            ("Add Tracker: add an entry for an agent (choose the agent first).", "rep_02_tracker_add_for_agent",
             "Add a tracker for an agent"),
            "Delete (bin): remove a wrong entry. This also removes its file and recalculates the day.",
        ]),

        ("h", "9. Tracker Report - Task EOD Report"),
        ("p", "The Task EOD (end of day) Report joins all agents' files for one task on one day into a single Excel "
              "file, with duplicate rows removed. Use it to send the client one consolidated file per task per day "
              "instead of collecting each agent's file."),
        ("p", "Everyone except agents can open it: Admin, Super Admin, Project Manager, Assistant Manager, Assistant "
              "Team Leader and QA. It lists every project's tasks, not only your team's."),
        ("img", "rep_12_eod_task_list", "Task EOD Report - Task List"),
        ("h2", "9.1 Find the task and day"),
        ("steps", [
            "Open Tracker Report and click the Task EOD Report tab (next to Tracker Entries).",
            "The Task List loads by itself for this month (1st of the month to today). Change From and To to look at "
            "other dates; Reset goes back to this month. The number of tasks found is shown on the right.",
            "Each row is one task on one day: Date (Saturdays and Sundays are shown in red), Project (with its code), "
            "Task, Entries (how many tracker entries that day) and Generate.",
        ]),
        ("h2", "9.2 Check the entries before generating"),
        ("steps", [
            ("Click the green Entries number. The Tracker List opens for that task and day and shows Total, Valid "
             "and Excluded counts.", "rep_13_eod_tracker_list", "Tracker List - Valid entries"),
            "Valid: entries whose files will go into the report. Each row shows Tracker ID, User, Work Date, Shift, "
            "Production and the File (Open shows the agent's file).",
            ("Excluded: entries that will NOT go into the report, with the Reason. Fix these before generating if "
             "they should be included.", "rep_14_eod_excluded", "Tracker List - Excluded entries and reasons"),
            "Click Close to go back to the Task List.",
        ]),
        ("table", ["Reason shown", "What it means / what to do"], [
            ["Tracker file missing", "The agent added the entry without a file. Ask the agent to add the file, or add "
                                     "it from Tracker Entries > Edit."],
            ["Inactive", "The entry was deleted. Nothing to do unless it was deleted by mistake."],
            ["Actual target missing / Tenure target missing / Tenure target is 0",
             "The task had no target when the entry was added. Set the task's target in Projects and Tasks, then "
             "delete the entry and add it again (Tracker Entries > Add Tracker) so the target is picked up."],
            ["File not found on Cloudinary / File unreachable on Cloudinary",
             "The file link is broken. Ask the agent to upload the file again."],
        ]),
        ("h2", "9.3 Generate the report"),
        ("steps", [
            "Click Generate on the row. The button shows Generating... while the files are joined.",
            "The Excel file downloads as EOD_Report_<task name>_<date>.xlsx. It has two sheets: Consolidated Report "
            "(all valid files joined, with user_id, user_name and work_date added to each row) and Tracker List "
            "(every entry with a file, marked accepted or rejected with the reason).",
            "Rows that are the same in all of the task's Important Columns are kept only once, so the same record "
            "uploaded twice (even by the same agent) appears once.",
        ]),
        ("bullets", [
            "A task appears in the list only when it has Important Columns set (Projects and Tasks > Edit Task) and at "
            "least one entry with a file and a target.",
            "If any valid file cannot be downloaded, no report is made. A message lists the tracker IDs and agents "
            "whose files are missing; ask them to upload again and click Generate again.",
            "The report is made each time you click Generate and is not saved in the HRMS. Generate it again after any "
            "tracker is corrected.",
        ]),

        ("h", "10. Weekly goal email (every Monday)"),
        ("p", "Every Monday at 11:00 the HRMS emails last week's (Monday to Sunday) agents of teams A and B who did "
              "not reach their weekly goal. Nothing has to be opened in the HRMS; it arrives in your mailbox."),
        ("table", ["You are", "You receive"], [
            ["Admin or Project Manager", "All agents of teams A and B."],
            ["Assistant Manager or Team Lead", "Only the agents assigned to you (Assistant Manager / Team Lead in the "
                                               "agent's profile). No agents assigned: no email."],
        ]),
        ("bullets", [
            "Week goal = Monday to Friday working days at the agent's daily hours (9 h x tenure), minus holidays, "
            "half days and leave that affects the target. Leave that does not affect the target still counts in "
            "the goal. Example: 45 h; 36 h with one full-day leave that affects the target.",
            "Achieved = billable hours from the agent's tracker entries that week (same as the Billable Report).",
            "For each agent who missed: week goal, achieved, shortfall and % achieved. Red below 75%, orange 75 to "
            "89%, green 90% and above.",
            "If every agent reached the goal you get an \"all achieved\" email instead.",
            "Agents who left during the week are still included for that week.",
        ]),

        ("h", "11. Rules to remember"),
        ("bullets", [
            "Billable report exports include a Tenure column for Admin, Super Admin, Project Manager and Assistant Manager.",
            "Working days come from the approved roster; change the roster, not the report, for attendance.",
        ]),

        ("h", "12. Common problems"),
        ("table", ["Problem", "What to do"], [
            ["Numbers look wrong for a day", "Check the roster for that day and the agent's tracker entries."],
            ["Edit icons not shown", "Your role can view only."],
            ["Goal is wrong", "Edit Monthly Target / Extra Assign Hours in User Monthly Goal."],
            ["Total Active Agents looks low", "It counts only people with a tracker entry in the dates. Widen the dates "
                                              "or check who has not added trackers."],
            ["A task is missing from Task EOD Report", "Set its Important Columns, and check the entries have a file "
                                                      "and a target."],
            ["Generate says files were not found", "Ask the listed agents to upload their files again, then Generate "
                                                   "again."],
            ["No weekly goal email on Monday", "Check Junk / Other. Team Leads and Assistant Managers get it only if "
                                               "agents are assigned to them. Ask the HRMS team to resend that week."],
            ["An agent's week goal looks wrong", "Check that week in the roster: leave marked as affecting the target, "
                                                 "half days and holidays reduce the goal."],
        ]),
    ],
}


QC_OVERVIEW_AUDIT = {
    "file": "SOP - Manager - QC Report Overview and QA Audit",
    "title": "QC Report Overview and QA Agent Audit",
    "roles": "Project Manager, Assistant Manager, Admin, Super Admin",
    "blocks": [
        ("h", "1. Purpose"),
        ("p", "QC Report Overview shows every QC result with its errors, files and correction / rework history. QA "
              "Agent Audit lets managers re-check QA work and record an audit score."),

        ("h", "2. QC Report Overview"),
        ("img", "mgr_11_qc_report_overview", "QC Report Overview"),
        ("table", ["Part", "What it shows / does"], [
            ["Agent / QC / Project / Task / Work Date", "Filters. Work Date is the agent's file date (current month to "
                                                        "today by default). Reset clears them."],
            ["Eval Date / Work Date", "When QC was done / the file's work date."],
            ["QA / Agent / Project / Task", "Who checked, whose file, and for what."],
            ["Records / QC / Errors / Score", "Rows in the file, rows checked, errors found, QC score."],
            ["Error Type", "The error names; View lists each error with its QC code and points."],
            ["Action - download", "The QC file QA checked: sample plus added rows, error rows highlighted, errors in "
                                  "the last column."],
            ["Action - arrow", "Opens Rework & Correction History."],
        ]),
        ("img", "rep_06_qco_view_errors", "View - the errors of a QC"),
        ("img", "rep_07_qco_history", "Rework & Correction History of a file"),
        ("h2", "2.1 Exports"),
        ("table", ["Button", "What you get"], [
            ["Export Excel", "The table as shown (filters applied)."],
            ["Export History", "Every rework and correction cycle."],
            ["Consolidated Export", "One summary row per file for the dates."],
            ["Error Report", "Only files with errors: each error type with how many times it appears in each file."],
        ]),

        ("h", "3. QA Agent Audit"),
        ("h2", "3.1 Audit a QA's work"),
        ("steps", [
            ("Open QA Agent Audit > QA Agent Audit Form. Each QA shows their records, total QC records and average "
             "score. Search a QA and filter by worked date and QC date.", "mgr_12_qa_agent_audit_form",
             "QA Agent Audit Form"),
            ("Open a QA with the arrow to list their QC records (worked date, QC date, agent, project, task, QC file, "
             "file record count, error list, QC score).", "rep_08_audit_expanded", "A QA's QC records"),
            ("Click the green button on a record. Enter the audit QC Score (0-100), attach the QC checked file if any, "
             "add Error Notes and click Submit Score.", "rep_09_audit_form", "Add QC Score (audit)"),
        ]),
        ("h2", "3.2 Audit report"),
        ("img", "mgr_13_qa_agent_audit_report", "QA Agent Audit Report"),
        ("p", "All audits done, to compare the QA's score with the audit score."),

        ("h", "4. Common problems"),
        ("table", ["Problem", "What to do"], [
            ["Score shows 0% with no errors", "Report it to the HRMS team with the tracker number."],
            ["File not in the list", "Check the Work Date range - it is the agent's file date, not the QC date."],
            ["Download gives an old-format file", "Files saved before the update keep the old layout."],
        ]),
    ],
}

MANAGER_SOPS = [PROJECTS_TASKS, MANAGER_REPORTS, QC_OVERVIEW_AUDIT]

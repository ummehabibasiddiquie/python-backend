"""Detailed SOP content for agents. Block format: see sop_content_qc_roster.py."""

AGENT_TRACKER = {
    "file": "SOP - Agent - Production Tracker",
    "title": "Production Tracker (Agents)",
    "roles": "Agent",
    "blocks": [
        ("h", "1. Purpose"),
        ("p", "Agents record every piece of work in the Production Tracker: the project, task, shift, production and "
              "the output Excel file. Billable hours, QC, targets and KRA are all calculated from these entries, so "
              "each one must be added on the day the work is done and with the right file."),

        ("h", "2. Screen guide - Tracker page"),
        ("p", "After login agents land on Tracker. The top menu has Analytics, My Roster, Tracker, AI Evaluation and "
              "SOPs."),
        ("img", "agent_01_tracker", "Production Tracker"),
        ("table", ["Part of the screen", "What it does"], [
            ["Add Tracker", "Opens the form to add a new entry."],
            ["Export", "Downloads the entries shown in the table."],
            ["From / To", "Date range of the entries shown (today by default)."],
            ["Project / Task", "Show only one project, then one of its tasks."],
            ["Reset Filters / Refresh", "Clear the filters / reload the list."],
            ["Table", "Date/Time, Project, Task, Shift (Day/Night), Per Hour Target, Production, Billable Hours, "
                      "Notes, Task File (download) and Action (delete, when allowed)."],
            ["Summary Totals", "Below the table: total Per Hour Target, Production and Billable Hours for the "
                               "entries shown."],
        ]),
        ("img", "agent_t04_summary_totals", "Summary Totals"),

        ("h", "3. Procedure - Add a tracker entry"),
        ("steps", [
            ("Click Add Tracker. The form shows today's date at the top.", "agent_02_add_tracker", "Add New Tracker"),
            ("Choose Project Name, then Task Name (only that project's tasks are listed). Choose the Shift (Day or "
             "Night). Base Target fills in automatically from the task and cannot be typed.",
             "agent_t02_add_filled", "Project, task and shift chosen - Base Target filled in"),
            "Enter Production: the quantity you completed (a number, 0 or more).",
            "Notes (optional, up to 200 characters): anything QA or your manager should know.",
            "Project Files: click or drag the output file. Only Excel (.xlsx or .xls), up to 10 MB.",
            "If the project needs checks, a blue box appears after the upload: run 1. AI Evaluation, then 2. "
            "Duplicate Check. Each must show a green 'passed' message before you can submit.",
            "If the project has SOP links, 'Project SOP' links show under Project Name. Click to read the SOP in a new "
            "tab (view only).",
            "Click Submit Entry. With a file, it is processed first ('File processed successfully'), then 'Tracker "
            "added successfully!' appears and the entry is in the table.",
        ]),
        ("h2", "How billable hours are worked out"),
        ("p", "Billable hours = Production / (task target per hour x your tenure). Example: task target 20 per hour, "
              "tenure 1.0, production 12 = 0.60 billable hours."),

        ("h", "4. Procedure - Delete your own entry"),
        ("steps", [
            "Find the entry in the table. The red bin appears in Action only while you are allowed to delete it.",
            ("Click the bin. Confirm Delete asks 'Are you sure...? This action cannot be undone.' Click Delete to "
             "remove it, or Cancel.", "agent_t03_delete_confirm", "Confirm Delete"),
            "After the delete window has passed, ask your manager to delete it from the Tracker Report.",
        ]),
        ("table", ["Entry", "You can delete it"], [
            ["Day shift", "On the day you added it."],
            ["Night shift added before midnight", "On the day you added it."],
            ["Night shift added between 00:00 and 09:00 (saved on the previous date)",
             "On the previous date and on the day you actually added it."],
        ]),

        ("h", "5. Rules to remember"),
        ("bullets", [
            "Add entries on the same day. Night-shift entries added between 00:00 and 09:00 are saved on the previous "
            "date, because they belong to the shift that started the evening before.",
            "Upload the actual output file - QA checks a sample of its rows (see SOP - QA - QC Process).",
            "Projects with Duplicate Check reject rows that were already submitted before.",
            "QA must check your file within 24 working hours (48 for night files added after midnight).",
            "If QA marks Correction or Rework, upload the fixed file from Analytics > Billable & QC Report > QC Report "
            "(see SOP - Agent - Reports, KRA and QC Results).",
        ]),

        ("h", "6. Common problems"),
        ("table", ["Message / problem", "What to do"], [
            ["'Only Excel files (.xlsx, .xls) are allowed.'", "Save the file as .xlsx or .xls and upload again."],
            ["'File size must not exceed 10MB'", "Remove extra sheets or split the file."],
            ["'Please complete AI Evaluation / Duplicate Check before submitting'", "Run the check buttons in the blue "
                                                                                    "box after the upload."],
            ["'... must pass before submitting'", "Fix the file (for example remove duplicate rows) and upload again."],
            ["'File processing failed'", "Check the file opens in Excel and has the expected columns, then retry."],
            ["Delete button missing", "The delete window has passed. Ask your manager."],
            ["Billable hours look wrong", "Check the Task chosen and the Production number."],
        ]),
    ],
}


AGENT_REPORTS = {
    "file": "SOP - Agent - Reports, KRA and QC Results",
    "title": "Reports, KRA, QC Results and My Roster (Agents)",
    "roles": "Agent",
    "blocks": [
        ("h", "1. Purpose"),
        ("p", "Agents use Analytics to follow their billable hours, monthly goal, QC results and KRA, to upload "
              "corrected or reworked files, and My Roster to see their schedule."),

        ("h", "2. Analytics > Overview"),
        ("img", "agent_03_overview", "Overview"),
        ("p", "Quick view of your hours for the selected dates."),

        ("h", "3. Billable & QC Report"),
        ("h2", "3.1 Daily Report"),
        ("img", "agent_04_billable_qc_report", "Daily Report"),
        ("table", ["Column", "Meaning"], [
            ["Date / Day Status", "The day and its roster status (Working, Week Off, Leave ...)."],
            ["Assign Hours", "Hours expected that day from the roster."],
            ["Worked Hours", "Billable hours from your tracker entries."],
            ["QC Score", "Average QC score of that day's files (blank until QA checks them)."],
            ["Tracker Count", "Number of tracker entries that day."],
            ["Daily Required Hours", "Hours you need per remaining day to reach the monthly goal."],
        ]),
        ("p", "Use From / To (within the chosen Month), Reset Filters and Export."),
        ("h2", "3.2 Monthly Report"),
        ("img", "agent_r01_monthly_report", "Monthly Report"),
        ("p", "Billable Hours Delivered, Monthly Goal, Pending Target (goal minus delivered) and Avg. QC Score for the "
              "month. Choose another month with Month; Export downloads it."),
        ("h2", "3.3 QC Report - results and re-uploads"),
        ("steps", [
            ("Open QC Report. Each file shows QC Date, File Submission, Project / Task, Score, Status (Regular, "
             "Correction #n, Rework #n), QC Status and Errors. Click View to see each error with its QC Code and "
             "points.", "qc_a01_agent_qc_report", "My QC Reports"),
            ("Click the arrow in History to open the QC History of a file: every correction/rework attempt with its "
             "QC date, status, score, errors and file.", "qc_a02_agent_qc_history", "QC History - Correction #1 open"),
            ("On the open attempt click Upload, choose the corrected (Correction) or reworked (Rework) Excel/CSV "
             "file and click Submit.", "qc_a03_agent_upload_modal", "Upload Correction File"),
            "The status changes to 'Under Review'. QA checks it again and the result appears here.",
        ]),
        ("table", ["Status", "What you do"], [
            ["Regular / Passed", "Nothing. The file passed."],
            ["Correction", "Fix only the marked rows in the marked sample and upload it."],
            ["Rework", "Fix all errors across the whole file and upload it."],
            ["Under Review", "Wait. QA is checking your upload."],
        ]),

        ("h", "4. KRA"),
        ("img", "agent_05_kra", "Monthly KRA"),
        ("bullets", [
            "Choose the month. Cards: Productivity 33%, Quality 33%, Roster 10%, Reporting 14% and the overall KRA %.",
            "Productivity: a day is Yes when billable hours reach 9 (4.5 on a half day).",
            "Quality: a day is Yes when the QC score is 98% or more.",
            "Reporting: days with fewer than 7 trackers (4 on a half day) count as low tracker days.",
            "Roster: present days against working days. The table lists every day; Excel downloads it.",
        ]),

        ("h", "5. My Roster"),
        ("img", "agent_06_my_roster", "My Roster"),
        ("p", "Your days for the month (working, shift, week off, leave, holiday). Ask your manager for any change; "
              "it goes to admin for approval."),

        ("h", "6. Common problems"),
        ("table", ["Problem", "What to do"], [
            ["QC Score is blank", "QA has not checked that day's files yet."],
            ["No Upload button", "The attempt is Under Review or already closed."],
            ["Numbers look wrong for a day", "Check your tracker entries and your roster for that day."],
        ]),
    ],
}

AGENT_SOPS = [AGENT_TRACKER, AGENT_REPORTS]

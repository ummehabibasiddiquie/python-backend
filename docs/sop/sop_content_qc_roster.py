"""Detailed SOP content: QC process (QA + agent) and Roster (manager + admin).

Block types used by build_sop_docs.py:
    ("h", "Heading")                      section heading
    ("h2", "Sub heading")                 sub heading
    ("p", "Paragraph")
    ("note", "Highlighted tip / warning")
    ("bullets", ["...", "..."])
    ("steps", ["text", ("text", "screenshot", "caption"), ...])   numbered steps, restart at 1
    ("img", "screenshot", "caption")
    ("table", ["Col A", "Col B"], [["a1", "b1"], ...])
"""

QC_PROCESS = {
    "file": "SOP - QA - QC Process (Agent Files, QC Form, Correction and Rework)",
    "title": "QC Process - Agent Files, QC Form, Correction and Rework",
    "roles": "QA (checks files); Agent (corrects / reworks); Managers and Admin (view results)",
    "blocks": [
        ("h", "1. Purpose"),
        ("p", "This SOP explains the full quality-check cycle in the HRMS: how QA picks an agent file, checks "
              "the sample on the QC form, marks errors, submits the result, and how Correction and Rework files "
              "come back from the agent and are reviewed again until the file is closed."),

        ("h", "2. Who does what"),
        ("table", ["Role", "What they do in this process"], [
            ["QA", "Checks agent files on the QC form, submits Regular / Correction / Rework, reviews corrected "
                   "and reworked files, and closes them."],
            ["Agent", "Sees the QC result and errors, downloads the marked file, and uploads the corrected or "
                      "reworked file."],
            ["Project Manager, Assistant Manager, Admin", "Follow results in QC Report Overview (see SOP - Manager - "
                                                          "QC Report Overview)."],
        ]),

        ("h", "3. Key terms"),
        ("table", ["Term", "Meaning"], [
            ["Sample", "The rows QA checks. Number of rows = task QC % x records in the file, rounded up "
                       "(10% if the task has no QC %)."],
            ["QC Code", "The unique code column in the agent file (for example 13-10-2026/Altrum/SS/34). Always "
                        "refer to the QC Code, not the Excel row number."],
            ["Category / Error", "Each project category has an error list (AFD). A category (for example "
                                 "Formatting) holds errors (for example Spacing/Extra Spacing, -10 points)."],
            ["Regular", "Score 100%. The file passes and is closed."],
            ["Correction", "Score 98% to 99.99%. The agent fixes the marked sample rows and uploads the file again."],
            ["Rework", "Score below 98%. The agent reworks the whole file and uploads it again."],
            ["Attempt", "Correction #1, Rework #2, and so on: how many times the file has gone back to the agent."],
        ]),

        ("h", "4. Screen guide - Agent Files & QC Report"),
        ("p", "Open Agent Files & QC Report from the top menu. It has three tabs: Agent's Tracker File (new files to "
              "check), Agent's Rework & Correction File (files the agent sent back) and QC Report (QC you have done)."),
        ("img", "qa_02_agent_files", "Agent Files & QC Report - Agent's Tracker File tab"),
        ("h2", "4.1 Work Date filter"),
        ("p", "From / To filter files by the agent's work date. Reset to Today goes back to today. Night-shift files "
              "added after midnight carry the previous date."),
        ("h2", "4.2 Urgent Files - do these first"),
        ("img", "qc_q01_urgent_panel", "Urgent Files list"),
        ("bullets", [
            "Shows files from September 2026 onward that are overdue or have 4 working hours or less left.",
            "Time left is red when overdue and amber when less than 4 hours remain.",
            "The red and grey badges show how many files are overdue and urgent. Search filters by agent, project "
            "or task. 'View all N urgent files' shows the full list.",
            "Click a row to open that task below, the download icon to get the agent's file, or QC Form to start QC.",
        ]),
        ("h2", "4.3 Projects / Tasks and the file list"),
        ("img", "qc_q02_task_files", "Projects / Tasks list and the files of the selected task"),
        ("bullets", [
            "Left: every project/task that has files for the dates, with the number of files. Use the search box "
            "to find an agent, project or task.",
            "Right: the files of the selected task - Date & Time, Agent, Project / Task, File (download) and QC Form.",
            "Use 'Show N entries' and the page buttons when there are many files.",
        ]),

        ("h", "5. Procedure - Check a file on the QC Form"),
        ("steps", [
            ("Click QC Form on the file. The form opens with the sample rows. Check the header: agent name, file "
             "name, Click to Download (full agent file), submission date and time, project, task and any "
             "'Project SOP' links.", "qa_05_qc_form", "QC Form header and the first sample row"),
            "In the table each row shows Sr. No., the File row number, the QC code, the task's important columns, "
            "Select Error, Selected Errors, one score column per category and the Record Score.",
            ("To mark an error on a row: open Select Category and pick the category, open Select Errors and tick "
             "one or more errors (each shows its points; Select All and Search are available).",
             "qc_q04_category_errors", "Choosing the category and the errors for a row"),
            ("Click Add (n) Error(s). The error appears in Selected Errors and the scores update at once. Click x on "
             "an error to remove it. Repeat for other categories on the same row if needed.",
             "qc_q05_error_added", "Error added - Formatting 90%, record 98%"),
            ("To check a row that is not in the sample: open 'Add a record from the file', choose the row (it shows "
             "the QC code, or the row number and first values) and click Add record. The row is added at the end "
             "with an 'Added' badge and is included in the score and the saved QC file.",
             "qc_q03_add_record_list", "Rows of the file that are not on the form"),
            ("Scroll down to Quality Assurance Information: QA name, Final QC Score, Status, Record Count in File, "
             "Data Generated for QC (includes added rows), Total Errors Marked and the Error Breakdown.",
             "qc_q06_summary_buttons", "Summary and the submit buttons"),
            "Only the button that matches the score can be clicked: Regular Submit (100%), Correction (98% to "
            "99.99%) or Rework Submit (below 98%). Cancel leaves the form without saving.",
            ("The Confirm QC Submission window shows the QA, agent email, project, task, status, score and error "
             "summary. Check them.", "qc_q07_confirm_modal", "Confirm QC Submission"),
            ("Type the Comments (required). Mention the QC Code and the error, for example 'QC Code 6417 - "
             "Formatting - Junk Character'. Click Confirm & Submit.", "qc_q07b_confirm_comments",
             "Comments are required before submitting"),
            "The file leaves your pending list. The agent is emailed the result and the marked QC file (error rows "
            "highlighted, errors in the last column) is saved for managers.",
        ]),
        ("h2", "Worked score example"),
        ("p", "The project has four categories. Marking 'Spacing/Extra Spacing (-10)' on row 1 makes Formatting 90%. "
              "Row 1 = average of 90, 100, 100, 100 = 97.5% (shown as 98%). The file has 3 sample rows: "
              "(97.5 + 100 + 100) / 3 = 99.17%, so only Correction can be submitted."),

        ("h", "6. Procedure - Correction and Rework cycle"),
        ("h2", "6.1 What the agent does"),
        ("steps", [
            ("The agent opens Analytics > Billable & QC Report > QC Report. Each file shows QC date, submission, "
             "project/task, score, Status (Regular / Correction #n / Rework #n), QC Status and Errors (View).",
             "qc_a01_agent_qc_report", "Agent - My QC Reports"),
            ("The agent clicks the arrow in History to see every attempt, then Upload on the open attempt.",
             "qc_a02_agent_qc_history", "Agent - QC History with Upload on Correction #1"),
            ("The agent selects the corrected / reworked Excel or CSV file and clicks Submit. The status becomes "
             "'Under Review' until QA checks it.", "qc_a03_agent_upload_modal", "Agent - upload correction file"),
        ]),
        ("h2", "6.2 What QA does with the returned file"),
        ("p", "Open Agent's Rework & Correction File. The work date filter uses the original file date. Pick the task "
              "on the left."),
        ("img", "qc_q08_rework_pending", "Returned files - Type, Attempt, Previous Score, Previous Errors, File, Action"),
        ("bullets", [
            "Type: Rework or Correction. Attempt: which cycle this is. Previous Score: the last QC score.",
            "Previous Errors > View lists the errors from the last check with their QC codes and points.",
            "File: download the file the agent uploaded.",
        ]),
        ("img", "qc_q10_previous_errors", "Previous errors for Correction #1"),
        ("steps", [
            "Rework file: click QC Form. A new sample is generated from the agent's latest uploaded file. Check it "
            "exactly like a new file and submit. Regular closes the file; Rework or Correction sends it back again "
            "(next attempt).",
            ("Correction file: download it and check the marked rows. In Action choose Completed (all fixed - file "
             "closed) or Correction (still wrong - goes back to the agent as the next attempt) and click Save Status.",
             "qc_q09_correction_pending", "Correction files - choose Completed or Correction, then Save Status"),
        ]),
        ("h2", "6.3 Cycle summary"),
        ("table", ["QA result", "What happens next", "Closes when"], [
            ["Regular (100%)", "File is completed.", "Immediately."],
            ["Correction (98-99.99%)", "Agent corrects the marked sample and uploads it. QA sets Completed or "
                                       "Correction.", "QA saves Completed."],
            ["Rework (below 98%)", "Agent reworks the whole file and uploads it. QA fills a new QC form on it.",
             "A rework check is submitted as Regular."],
        ]),

        ("h", "7. Procedure - Your QC Report"),
        ("img", "qc_q11_my_qc_report_history", "QC Report tab with a file's QC history opened"),
        ("bullets", [
            "Search by agent, project, task or QC; filter by Status, QC and dates. Clear resets the filters.",
            "Export downloads the table; History downloads the rework and correction cycles; Consolidated Export "
            "downloads the summary for the dates.",
            "Tracker File and QC File download the agent file and the marked QC file. The History arrow shows every "
            "attempt with its score and errors.",
        ]),

        ("h", "8. Rules to remember"),
        ("bullets", [
            "QC deadline: 24 working hours from submission (48 for night files added after midnight). Saturday, "
            "Sunday and holidays do not count.",
            "Scoring: every category starts at 100; each error takes off its points; a record's score is the average "
            "of its category scores; an error worth 100 points or more makes the record 0; the file score is the "
            "average of all rows on the form, including added rows.",
            "You cannot choose a different result than the score allows.",
            "Marks are not saved until Confirm & Submit. Refreshing or leaving the page loses them.",
            "Always write the QC Code in comments so the agent can find the row.",
            "If a QC was submitted by mistake, an admin can reset that tracker's QC (see the 'Reset QC for a Tracker' "
            "guide); do not fill it twice.",
        ]),

        ("h", "9. Common problems"),
        ("table", ["Problem", "What to do"], [
            ["'Every file record is already on the form'", "All rows are already sampled or added; nothing to add."],
            ["No categories in Select Category", "The project's category is not linked to an AFD. Ask admin."],
            ["QC Form keeps loading", "Check the agent file opens with Click to Download. If not, ask the agent to "
                                      "re-upload the tracker file."],
            ["\"Could not save QC\" on submit", "Do not refill repeatedly. Send the tracker number and a screenshot of "
                                                "the message (it shows the reason) to the HRMS team."],
            ["Agent cannot see Upload", "The file is Under Review (already uploaded) or the attempt is closed."],
        ]),
    ],
}


ROSTER_MANAGER = {
    "file": "SOP - Manager - Roster",
    "title": "Roster Management (Managers)",
    "roles": "Project Manager, Assistant Manager, Assistant Team Leader (and Admin / Super Admin)",
    "blocks": [
        ("h", "1. Purpose"),
        ("p", "The roster says, for every employee and every day of the month, whether they work (day or night "
              "shift, full or half day), are on week off, holiday or leave, or have left. Targets, billable "
              "hours and KRA are calculated from it, so every change goes to admin for approval."),

        ("h", "2. Who can do what"),
        ("table", ["Action", "Who"], [
            ["View and edit days, leave, Left", "Project Manager, Assistant Manager, Assistant Team Leader, Admin, Super Admin"],
            ["Generate missing rosters, Excel upload, submit for approval", "Same as above"],
            ["See all teams (Team filter)", "Project Manager, Admin, Super Admin. Assistant Managers and Team "
                                            "Leaders see their own team only."],
            ["Approve / reject, lock / unlock, send roster email, reset, edit holidays", "Admin and Super Admin only "
                                                                                         "(see SOP - Admin - Roster)"],
        ]),

        ("h", "3. Screen guide - Roster Calendar"),
        ("p", "Manage > Roster Management. Tabs: Roster Calendar (the grid), My Submissions (your changes), Holiday "
              "Master (holidays). Admins also see Approval Queue."),
        ("img", "mgr_14_roster_calendar", "Roster Calendar"),
        ("bullets", [
            "Month: the roster month. Team: filter by team (PM / Admin). Employee: type a name; leave empty for all. "
            "When exactly one employee matches, 'single actions ready' appears.",
            "Actions > Generate: Generate Missing Rosters (creates rosters only for employees who have none for the "
            "month), Single Employee (for the one matching employee), Generate Next Month Rosters (shown at the end "
            "of the month).",
            "Actions > Workflow: Excel Upload (download / upload a week in Excel).",
            "Yellow banner 'Locked weeks' lists weeks admin has locked, who locked them and when.",
            "Week tabs (Week 1 ... Week 5) switch the grid. Locked weeks are marked '· Locked'.",
        ]),
        ("img", "roster_m01_week4_tab", "An editable week"),
        ("bullets", [
            "Each cell shows the day type (Working, Half Working, Week Off, Leave, Holiday, Left) and badges such as "
            "Day / Night, Full Day / Half and hours.",
            "An amber dot on a cell means a change is saved but not yet approved.",
            "Cells cannot be clicked when the week or month is locked, or when that week already has a change waiting "
            "for approval.",
        ]),

        ("h", "4. Procedure - Generate rosters"),
        ("steps", [
            "Choose the Month. Click Generate Missing Rosters and Confirm. Existing rosters are not changed; the "
            "message shows how many were created and skipped.",
            "For one new joiner: type their name in Employee until only they remain, then click Single Employee.",
            "At month end, Generate Next Month Rosters creates next month's rosters for everyone who has none.",
        ]),

        ("h", "5. Procedure - Change a day"),
        ("steps", [
            ("Open the week tab and click the employee's day. The Edit Roster Day window opens.",
             "mgr_15_roster_day_edit", "Edit Roster Day - Working"),
            "Working / Week Off: choose Day Type, Shift (Day or Night) and, for Working, the Working Hours. Click Save "
            "Day Change Request.",
            ("Leave: choose Leave (Roster) for planned leave or Leave (Unrostered) for unplanned leave. Tick Half Day "
             "if they work half the day. Tick Affect Target to reduce the monthly working days and hours; leave it "
             "unticked to keep the full target. Click Save Leave Request.", "roster_m02_day_leave",
             "Leave options - Half Day and Affect Target"),
            ("Left: choose Left when the person stops coming from that date. Keep 'Apply Left from this date through "
             "the end of the month' ticked to mark every remaining day.", "roster_m03_day_left", "Left"),
            "The cell now shows the new value with an amber dot (draft). Nothing changes for targets until admin "
            "approves.",
            "Changed your mind before submitting? Open the same day again and save the new value. It replaces the "
            "earlier draft, so only one change per day goes to admin.",
        ]),

        ("h", "6. Procedure - Submit for approval"),
        ("steps", [
            "When your drafts are ready, the yellow bar shows 'N saved change(s) are not submitted yet'. Click Submit "
            "for approval and Confirm.",
            "Each week you edited goes to admin. While it is waiting, that week cannot be edited ('Week N has pending "
            "approval requests; withdraw or wait for review').",
            "After approval the change is applied, targets are recalculated and the week is locked.",
            "Approving does not send the roster email. Admin uses Send email on the week tab.",
        ]),

        ("h", "7. Procedure - Track or withdraw your changes"),
        ("img", "roster_m05_submissions_approved", "My Submissions"),
        ("steps", [
            "Open My Submissions. The cards show Total, Draft, Pending, Approved and Rejected for the month.",
            "Filter Draft / Pending / Approved / Rejected / All and search by employee, change type or details.",
            "Open Details to see the requested change and the reviewer's note. A rejected request shows the reason.",
            "To remove a draft before submitting, click Withdraw (or Withdraw draft in Details).",
        ]),

        ("h", "8. Procedure - Excel upload (many changes at once)"),
        ("img", "roster_m04_excel_upload", "Weekly Roster Excel"),
        ("steps", [
            "Click Actions > Excel Upload. Choose the week. Locked weeks are amber and cannot be uploaded.",
            "Click Download Week N (one sheet) or Download all weeks (one sheet per week).",
            "Fill the file offline and upload it in '2. Upload filled file'. The preview shows changes, unchanged rows "
            "and errors. Fix errors and upload again if needed.",
            "Click Apply & submit for approval. The changes are saved and that week is submitted for approval at once.",
        ]),

        ("h", "9. Other things on this page"),
        ("bullets", [
            "Holiday Master lists the holidays for a year (search by name or date). Only admins can change them.",
            "Monthly extra assigned hours are changed on User Monthly Goal, not on the roster. Negative values reduce "
            "the goal.",
        ]),
        ("img", "mgr_17_roster_holidays", "Holiday Master (view)"),

        ("h", "10. Rules to remember"),
        ("bullets", [
            "The employee needs a tracker joining date before their roster can be edited.",
            "Leave and half day cannot be added on a holiday. Set Working (day or night) if the person must work.",
            "One change per employee per day: a newer draft replaces the older one.",
            "Approved weeks are locked. Ask admin to unlock a week before changing it again.",
            "Half-day leave and half working days count as half a working day in KRA.",
        ]),

        ("h", "11. Common problems"),
        ("table", ["Problem", "What to do"], [
            ["Cannot click a day", "The week is locked, the month is locked, or the week has a change waiting for "
                                   "approval. Ask admin, or withdraw your submission."],
            ["'Tracker joining date is not set'", "Ask admin to set the joining date in User Management."],
            ["'No employees for this filter'", "Generate missing rosters or choose another team."],
            ["Single Employee is greyed out", "Type the name until only one employee remains."],
            ["Change shows but targets did not change", "It is still a draft or pending. Submit it and wait for approval."],
        ]),
    ],
}


ROSTER_ADMIN = {
    "file": "SOP - Admin - Roster",
    "title": "Roster Management (Admin and Super Admin)",
    "roles": "Admin, Super Admin",
    "blocks": [
        ("h", "1. Purpose"),
        ("p", "Admins approve roster changes, control which weeks can be edited, send the weekly roster email, keep "
              "the holiday list and, when needed, reset rosters. Admins can also edit days exactly like managers "
              "(see SOP - Manager - Roster); their changes go through the same approval step."),

        ("h", "2. Screen guide - admin controls"),
        ("img", "roster_a01_week4_admin_buttons", "Roster Calendar - admin view"),
        ("table", ["Control", "Where", "What it does"], [
            ["Send email · Week N", "Right of the week tabs", "Sends the roster email for that week only."],
            ["Lock Week N / Unlock Week N", "Right of the week tabs", "Stops or allows manager edits for that one week."],
            ["Lock Month / Unlock Month", "Actions > Admin", "Freezes or opens every week of the month. Lock Month is "
                                                            "available from the last day of the month."],
            ["Reset Employee", "Actions > Admin", "Clears one employee's requests for the month and regenerates their roster."],
            ["Reset All (MONTH)", "Actions > Admin", "Deactivates every roster of the month, clears all request "
                                                     "history and regenerates. Use only when the whole month is wrong."],
            ["Approval Queue", "Tab", "Approve or reject submitted changes."],
            ["Holiday Master", "Tab", "Add, edit, upload or deactivate holidays."],
        ]),

        ("h", "3. Procedure - Approve or reject changes"),
        ("img", "admin_06_roster_approval", "Approval Queue"),
        ("steps", [
            "Open Approval Queue. The cards show Total, Pending, Approved and Rejected for the month. Choose the Month, "
            "search, and use the Pending / Approved / Rejected / All filters.",
            ("Click Details on a request to see the employee, who submitted it and when, and the exact change "
             "(dates, leave type, half day, affects target, rostered).", "roster_a07_approval_details",
             "Request Details"),
            "Approve or Reject a single request, or tick 'Select all' / individual requests and use Approve (n) or "
            "Reject (n). Rejecting needs a comment.",
            "Selected requests are applied oldest first, so if a day has two changes the later one is what remains.",
            "After approval the change is applied, targets are recalculated and the weeks touched are locked.",
            "Super Admin: 'Email approvers (pending)' emails Admin and Super Admin about pending requests.",
        ]),

        ("h", "4. Procedure - Lock, unlock and email a week"),
        ("steps", [
            ("Open the week tab. To stop changes, click Lock Week N and Confirm.", "roster_a02_lock_week_dialog",
             "Lock Week confirmation"),
            ("To let managers change a locked week, open it and click Unlock Week N. Other locked weeks stay locked.",
             "roster_a04_unlock_week_dialog", "Unlock Week confirmation"),
            ("When the week is final, click Send email · Week N and Confirm. Only that week is emailed.",
             "roster_a03_send_email_dialog", "Send week roster email"),
            "Lock Month freezes the whole month (from its last day). Unlock Month or 'Unlock Calendar' on the banner "
            "opens it again.",
        ]),

        ("h", "5. Procedure - Reset rosters (use with care)"),
        ("img", "roster_a05_reset_all_dialog", "Reset All warning"),
        ("steps", [
            "Reset Employee: type the employee's name until only they remain, click Reset Employee and Confirm. Their "
            "requests for the month are cleared and the roster is rebuilt from their tenure and joining date.",
            "Reset All: only when the whole month must be rebuilt. It clears every Pending, Approved and Rejected "
            "request for the month. It can take a minute; wait for 'Working...' to finish.",
        ]),

        ("h", "6. Procedure - Holiday Master"),
        ("img", "roster_a08_holiday_master", "Holiday Master - admin"),
        ("steps", [
            ("Click Add Holiday, enter the Holiday Name and pick the Date, then Save.", "roster_a09_add_holiday",
             "Add Holiday"),
            "Upload Excel adds many holidays at once. The edit icon changes a holiday; Deactivate removes it from "
            "rosters.",
            "Holidays have the highest priority on a day. Leave and half day cannot be put on a holiday.",
        ]),

        ("h", "7. Admin editing days"),
        ("bullets", [
            "Click a day and use Edit Roster Day exactly as in the manager SOP. The change is a draft until it is "
            "submitted and approved - approve it in Approval Queue.",
            "Locked weeks block admins too. Unlock the week, make the change, then it locks again on approval.",
        ]),
        ("img", "roster_a06_day_edit", "Admin editing a day"),

        ("h", "8. Common problems"),
        ("table", ["Problem", "What to do"], [
            ["Lock Month is greyed out", "It opens on the last day of the month."],
            ["Manager says a week cannot be edited", "Check the locked-weeks banner and unlock that week."],
            ["Weekly email not sent", "The confirmation shows the reason. Check the week has approved rosters."],
            ["Two pending changes for the same day", "Approve both together (latest wins) or reject the older one."],
        ]),
    ],
}

DETAILED_SOPS = [QC_PROCESS, ROSTER_MANAGER, ROSTER_ADMIN]

"""Detailed SOP content: admin, super admin, QA reports, team leader, SOP library."""

ADMIN_USERS_AFD = {
    "file": "SOP - Admin - Users, AFD and Categories",
    "title": "User Management, AFD and Project Category",
    "roles": "Admin, Super Admin (and users given User Creation permission)",
    "blocks": [
        ("h", "1. Purpose"),
        ("p", "Admins create and maintain user accounts, and the QC error lists (AFD) and project categories that "
              "decide what QA can mark on the QC form and how much each error costs."),
        ("note", "Admins also use: SOP - Manager - Reports (Overview, Billable Report, QA Report, User Monthly Goal, "
                 "KRA, Tracker Report and Task EOD Report), SOP - Manager - Projects and Tasks, SOP - Manager - QC "
                 "Report Overview and QA Audit, SOP - Admin - Roster and SOP - Admin - SOP Library."),

        ("h", "2. User Management"),
        ("img", "admin_02_users", "User Management"),
        ("table", ["Part", "What it does"], [
            ["Filter Users", "Full Name, Email, Team and Role filters."],
            ["Add User", "Create a new account."],
            ["Table", "User (name, email), Designation, Reporting To, Role, Status switch (active / inactive) and "
                      "Actions (edit, delete)."],
        ]),
        ("h2", "2.1 Create a user"),
        ("steps", [
            ("Click Add User. Fill Full Name, Email Address, Role, Designation and Password (required). Phone, "
             "Address and Profile Picture are optional.", "adm_u01_add_user", "Create New User"),
            "Choosing the Role shows the extra fields that role needs (see the table below).",
            "Tracker Joining Date is the date the person starts using the roster and tracker (not the company joining "
            "date). It defaults to today; past or future dates are allowed.",
            "Click Create User.",
        ]),
        ("table", ["Role", "Extra fields"], [
            ["Super Admin, Admin", "None (no reporting line or team)."],
            ["Project Manager", "Team (optional)."],
            ["Assistant Manager", "Team (required), Project Manager (optional)."],
            ["Assistant Team Leader", "Team (required), Project Manager and Assistant Manager (optional)."],
            ["QA", "Team, Tenure and Tracker Joining Date (required); PM, AM, Team Leader (optional)."],
            ["Agent", "Team, Quality Analyst, Tenure and Tracker Joining Date (required); PM, AM, Team Leader "
                      "(optional)."],
        ]),
        ("h2", "2.2 Edit, deactivate or delete a user"),
        ("img", "adm_u03_edit_user", "Edit user"),
        ("bullets", [
            "Pencil: edit details. Tenure scales the agent's target (target = task target x tenure).",
            "Status switch: deactivate someone who has left. They cannot log in and drop out of lists; history stays.",
            "Bin: delete an account created by mistake.",
        ]),

        ("h", "3. AFD Management (QC error lists)"),
        ("img", "admin_04_afd", "Create New AFD"),
        ("steps", [
            "Enter the AFD Name (for example 'AFD for Research').",
            "Add Category: enter the Category Name and Category Score. Inside it, Add Sub for each error with its "
            "points (how much the error takes off).",
            "Add more categories as needed and click Save AFD.",
            ("Saved AFDs are listed below with their categories and errors. Use the pencil to edit and the bin to "
             "remove a category, an error or the AFD.", "adm_a01_afd_list", "Saved AFD with categories and errors"),
        ]),
        ("note", "An error worth 100 points or more is a fatal error: the record it is marked on scores 0."),

        ("h", "4. Project Category"),
        ("img", "admin_05_category", "Project Categories"),
        ("steps", [
            "Enter the Category Name, choose the AFD Name and click Add Category.",
            "Search categories; edit or delete with the icons.",
            "Set this category on each project (Edit Project > Project Category). QA then sees this AFD's errors on "
            "the QC form for that project.",
        ]),

        ("h", "5. Common problems"),
        ("table", ["Problem", "What to do"], [
            ["Agent missing in rosters / tracker", "Check the user is active, the role is Agent and the Tracker "
                                                   "Joining Date is set."],
            ["Target looks wrong", "Check the user's Tenure."],
            ["QA sees no errors on the QC form", "Link the project's category to an AFD."],
        ]),
    ],
}


SUPER_ADMIN = {
    "file": "SOP - Super Admin - Permissions and Report Emails",
    "title": "User Permission and Report Emails",
    "roles": "Super Admin",
    "blocks": [
        ("h", "1. Purpose"),
        ("p", "Super Admin controls who may create users and projects, and who receives the automatic report emails."),
        ("note", "Super Admin also has everything an Admin has. For those screens use the Admin SOPs and SOP - Manager "
                 "- Reports (Overview, Billable Report, QA Report, User Monthly Goal, KRA, Tracker Report and Task EOD "
                 "Report)."),
        ("h", "2. User Permission"),
        ("img", "sa_01_permissions", "User Permissions"),
        ("steps", [
            "Manage > User Permission. Search by name or email, or filter by role.",
            "Switch User Creation on to let that person add users; switch Project Creation on to let them add "
            "projects. Changes save at once.",
        ]),
        ("h", "3. Report emails"),
        ("img", "sa_02_report_emails", "Report emails"),
        ("table", ["Email", "When it is sent"], [
            ["Billable hours", "Yesterday's billable hours."],
            ["Intraday tracker", "Three times a day."],
            ["Previous-day production", "When the previous full day is complete."],
        ]),
        ("steps", [
            "Add a recipient: type the email, choose TO or CC, tick the reports they should get and click Add.",
            "In the list, switch each report on or off per person, or change TO / CC.",
            "Use the bin to remove someone. Search and the All / To / Cc filters help with long lists.",
        ]),
        ("note", "The Monday weekly goal email is not set up here. It goes automatically to Admins and Project "
                 "Managers (all agents) and to each Assistant Manager / Team Lead (their own agents). See SOP - "
                 "Manager - Reports, section 10."),
        ("h", "4. Common problems"),
        ("table", ["Problem", "What to do"], [
            ["Someone did not get an email", "Check they are listed with that report switched on."],
            ["A manager cannot add users", "Switch on User Creation for them."],
        ]),
    ],
}


SOP_LIBRARY = {
    "file": "SOP - Admin - SOP Library",
    "title": "SOP Library",
    "roles": "Admin, Super Admin, Project Manager (manage); everyone else (view)",
    "blocks": [
        ("h", "1. Purpose"),
        ("p", "The SOP library holds the organisation's procedures, grouped by topic. Each item is a link (for example "
              "a shared-drive file) or an uploaded document."),
        ("h", "2. Manage the library"),
        ("p", "Admin, Super Admin and Project Manager open it from Manage > SOPs (it is not in their top menu)."),
        ("img", "admin_09_sops_manage", "SOP library"),
        ("steps", [
            ("Click New topic, enter the topic (for example Attendance, Leave, Quality) and an optional description, "
             "then save.", "adm_s01_new_topic", "New topic"),
            "Open the topic and use Add to <topic>: give the item a title, then either paste a link (must start with "
            "https://) or upload a document, and save.",
            "Remove an item or a whole topic with the bin (removing a topic removes everything in it).",
        ]),
        ("h", "3. View the library"),
        ("img", "qa_12_sops", "SOP library - view"),
        ("p", "Agents, QA, Assistant Team Leaders and Assistant Managers open SOPs from the top menu (view only). "
              "Links open in a new tab; documents download."),
        ("h", "4. Tips"),
        ("bullets", [
            "Upload these Word SOPs here, one topic per role (Agent, QA, Manager, Admin).",
            "For shared-drive links, share the file as Viewer first.",
        ]),
    ],
}


QA_REPORTS = {
    "file": "SOP - QA - Reports and Hours",
    "title": "QA Reports, Hours and Roster",
    "roles": "QA, Assistant Team Leader",
    "blocks": [
        ("h", "1. Purpose"),
        ("p", "QA hours are counted from QC work (automatically, from each task's QA hour criteria) plus the "
              "non-QC work QA records in My Report. This SOP covers recording that work and the QA reports."),
        ("h", "2. My Report - record non-QC work"),
        ("img", "qa_06_my_report_hours", "My Report - Feedback & Reporting Tracker"),
        ("steps", [
            ("Click Add Tracker. The date is today.", "qa_h01_add_reporting_tracker", "Add Tracker (QA)"),
            "Choose the Type: Feedback, Training, Reporting or Other.",
            "Feedback / Training: choose the Agent (and project) it was for. Reporting / Other: describe the work in "
            "'What did you do'.",
            "Enter Hours and/or Minutes (for example 0 hr + 4 min), an optional Note, and click Add.",
            "You can delete your own entry within 24 hours.",
        ]),
        ("p", "Daily Report and Monthly Report total your hours: QC hours, rework hours, feedback, reporting and "
              "Total / 9 hours."),
        ("h", "3. Other screens"),
        ("table", ["Screen", "What it shows"], [
            ["Analytics > Overview", "Your agents' active count, billable vs assigned hours and latest files for the "
                                     "selected dates (cards explained in SOP - Manager - Reports, section 2)."],
            ["Tracker Report", "Agents' tracker entries. The Task EOD Report tab joins all agents' files for a task and "
                               "day into one Excel (see SOP - Manager - Reports, section 9)."],
            ["Agents Billable Report", "Agents' billable hours by day and month."],
            ["Audit Report", "Audits managers did on your QC (audit score vs your score)."],
            ["KRA", "Your monthly KRA."],
            ["My Roster", "Your schedule."],
            ["SOPs", "The SOP library (view only)."],
        ]),
        ("img", "qa_09_audit_report", "Audit Report"),
        ("img", "qa_10_kra", "KRA"),
        ("h", "4. Common problems"),
        ("table", ["Problem", "What to do"], [
            ["QC hours look low", "QC hours come from the task's QA hour criteria; ask the manager to check the task."],
            ["Entry added on the wrong day", "Delete it within 24 hours and add it again."],
        ]),
    ],
}


ASSISTANT_TEAM_LEADER = {
    "file": "SOP - Assistant Team Leader",
    "title": "Assistant Team Leader",
    "roles": "Assistant Team Leader",
    "blocks": [
        ("h", "1. Purpose"),
        ("p", "Assistant Team Leaders follow their own team's work, keep the team roster and do QC like a QA on the "
              "agents and projects where they are set as the QA. Apart from the roster and QC work, the team screens "
              "are view only."),
        ("h", "2. What you can use"),
        ("table", ["Screen", "What you can do"], [
            ["Agent Files & QC Report", "Fill QC forms, rework and correction for agents where you are the QA (same "
                                        "steps as SOP - QA - QC). Includes My QC Report."],
            ["My Report", "Add Tracker for your non-QC work (Feedback, Training, Reporting, Other) and see your daily "
                          "and monthly QA hours (same steps as SOP - QA - Reports and Hours, section 2)."],
            ["Audit Report", "Audits managers did on your QC."],
            ["Analytics", "View your team's overview, billable report and KRA. Overview cards are explained in "
                          "SOP - Manager - Reports, section 2."],
            ["Tracker Report", "View your team's tracker entries. The Task EOD Report tab joins all agents' files for "
                               "a task and day into one Excel (see SOP - Manager - Reports, section 9)."],
            ["Manage > Roster Management", "Edit your team's days and leave, and submit them for approval "
                                           "(see SOP - Manager - Roster)."],
            ["SOPs", "Read the SOP library."],
            ["Email (every Monday)", "Weekly goal email listing your agents who missed last week's goal (see SOP - "
                                     "Manager - Reports, section 10)."],
        ]),
        ("img", "atl_01_overview", "Overview"),
        ("img", "atl_02_tracker_report", "Tracker Report"),
        ("img", "atl_03_manage", "Roster Management (your team)"),
        ("h", "3. Rules"),
        ("bullets", [
            "You only see your own team (the Task EOD Report is the exception: it lists every project's tasks).",
            "For QC, you only see agents and projects where an admin or manager has picked you as the QA (Quality "
            "Analyst / Project QA). Ask them to add you if an agent is missing.",
            "You cannot change users, projects or agents' tracker entries; ask your manager.",
            "Roster changes go to admin for approval and approved weeks lock.",
        ]),
    ],
}

ADMIN_SOPS = [ADMIN_USERS_AFD, SUPER_ADMIN, SOP_LIBRARY, QA_REPORTS, ASSISTANT_TEAM_LEADER]

"""Handover documents 01-02: start here and system overview, setup and deployment."""

START_HERE = {
    "number": "01",
    "title": "Start Here and System Overview",
    "audience": "New developer taking over the TFS HRMS, and the person handing over",
    "blocks": [
        ("h", "1. What this handover covers"),
        ("p", "TFS HRMS (shown to users as \"TFS Ops Tracker\") is the in-house system the operations team uses every "
              "day. Agents log their production in it, QA check agents' files, managers plan rosters and follow "
              "billable hours, and admins run users, projects and approvals. It has three parts: a React website, a "
              "Python (Flask) API and a Node.js QC API, all using one MySQL database on a Hostinger VPS."),
        ("p", "Read the documents in this order:"),
        ("table", ["No.", "Document", "Read it to learn"], [
            ["01", "Start Here and System Overview (this document)", "Reading order, key facts, what the system "
                                                                     "does, roles, applications, live addresses, "
                                                                     "how the parts connect, daily jobs, golden "
                                                                     "rules."],
            ["02", "Setup and Deployment", "How to run all three parts on your laptop; branches, how to release, "
                                           "server commands, backups, logs."],
            ["03", "Technical Reference", "The rules users depend on (tracker, billable hours, QC, roster, QA hours, "
                                          "KRA), where things live in each repository, the main API endpoints and "
                                          "the database tables."],
            ["04", "Support and Known Issues", "Step-by-step fixes for the requests that come up most often, what "
                                               "changed lately, known bugs and risks, and what is still open."],
            ["05", "KT Checklist and Sign-off", "The access the new developer needs, and the sign-off sheet ticked "
                                                "by both people at the end."],
            ["06", "Credentials Register", "All logins, passwords and keys. A separate password-protected file; the "
                                           "lead gives the file password in person."],
            ["07", "API Reference", "Every Flask and Node QC endpoint: request, access, response and the screen "
                                    "that uses it."],
            ["08", "Database Schema", "Every table and column, how the tables link, generated from the database."],
        ]),
        ("p", "The user SOPs (one Word file per role and module) are in docs/sop/word. Read them too: they show "
              "every screen with screenshots and are the quickest way to learn what users see."),

        ("h", "2. Key facts"),
        ("table", ["Item", "Value"], [
            ["Live website address", "https://tfshrms.cloud"],
            ["Live Flask API address", "https://tfshrms.cloud/python"],
            ["Live Node QC API address", "https://tfshrms.cloud/api/v1"],
        ]),

        ("h", "3. What the system does"),
        ("table", ["Area", "What happens"], [
            ["Production tracker", "Agents add an entry for each piece of work: project, task, shift, production "
                                   "count and the output file. The system works out billable hours."],
            ["QC (quality check)", "QA open an agent's file, check a random sample of rows, mark errors and submit a "
                                   "result: Regular (100%), Correction or Rework. Agents fix and re-upload."],
            ["Roster", "Managers plan each person's month (working, week off, leave, holiday, shift). Admins "
                       "approve changes and lock weeks. The roster sets each person's assigned hours."],
            ["Reports", "Billable (daily and monthly), User and Project Monthly goals, QA hours, KRA, Tracker "
                        "Report, Task EOD Report, QC Report Overview, QA Agent Audit."],
            ["Administration", "Users, projects and tasks, AFD (QC error lists), project categories, permissions, "
                               "SOP library, report email recipients, holidays."],
            ["Emails", "Daily billable report, intraday and previous-day tracker reports, QC result emails to "
                       "agents, roster approval and weekly roster emails, password reset."],
        ]),

        ("h", "4. Roles"),
        ("table", ["role_id", "Role", "Sees"], [
            ["1", "Super Admin", "Everything, plus User Permission and Report emails."],
            ["2", "Admin", "Everything except Report emails. Approves roster changes, locks weeks, holidays."],
            ["3", "Project Manager", "All users' data; projects, roster, reports, QC overview, audit."],
            ["4", "Assistant Manager", "Only users assigned to them (asst_manager_id)."],
            ["7", "Assistant Team Leader", "Own team, view only except the roster (submits changes)."],
            ["5", "QA", "Agents assigned to them (qa_id): Agent Files & QC, My Report hours, audit results."],
            ["6", "Agent", "Only themselves: Tracker, own reports, KRA, QC results, My Roster, AI Evaluation."],
        ]),
        ("p", "Each user has a role plus reporting lines (project manager, assistant manager, team leader, QA). "
              "Visibility in every report follows these lines. The columns that hold them are in 03, Database "
              "reference."),

        ("h", "5. The applications"),
        ("table", ["Part", "Repository / branch", "Technology", "Port"], [
            ["Website", "hrms-frontend / live", "React 19, Vite 7, Tailwind 4, Ant Design, Recharts, axios",
             "5173 (dev)"],
            ["Flask API", "python-backend (local folder backend-api) / main", "Python 3, Flask 3, mysql-connector, "
             "pandas, openpyxl, APScheduler, Cloudinary", "5000"],
            ["Node QC API", "node-backend (local folder qc-backend) / main", "Node, TypeScript, Express 5, mysql2, "
             "ExcelJS, Cloudinary, nodemailer, Gemini (ai-sdk)", "8000"],
            ["Database", "-", "MySQL 8", "3306"],
            ["File storage", "-", "Cloudinary (see below)", "-"],
        ]),

        ("h2", "Cloudinary account"),
        ("table", ["Cloud name", "Used for", "Owner email"], [
            ["dhgyodnva", "All uploaded files: tracker, QC, project and SOP files, in folders under hrms/ "
                          "(tracker_files, qc_samples, ...). Free plan, about 9% of credits used (21 Oct 2026).",
             "tfsoperation@transformsolution.net (company mailbox)"],
        ]),
        ("p", "The system connects with the API keys in the .env files, so it works without anyone logging in. "
              "Log in with the owner email to see usage, limits and billing, and add a second company email as "
              "admin under Settings > Users."),

        ("h2", "Live addresses (Nginx on the VPS)"),
        ("table", ["Address", "Goes to"], [
            ["https://tfshrms.cloud/", "Website (static files in /var/www/tfshrms-frontend; unknown paths fall back "
                                       "to index.html)"],
            ["https://tfshrms.cloud/api/v1/...", "Node QC API on 127.0.0.1:8000"],
            ["https://tfshrms.cloud/python/...", "Flask API on 127.0.0.1:5000 (the /python prefix is removed)"],
        ]),
        ("p", "HTTP redirects to HTTPS; the SSL certificate is from Let's Encrypt (Certbot). Production is built on "
              "the server and served by Nginx (see 02). Vercel builds of the website are for testing only."),

        ("h", "6. How the parts talk"),
        ("code", """Browser (React website)
   |-- Flask API  (VITE_API_BASE_URL)          users, projects, tasks, tracker, roster,
   |                                           reports, KRA, QA hours, SOPs, emails
   |-- Node QC API (VITE_API_NODE_BASE_URL)    QC sample, QC save (regular / correction / rework),
                                               agent re-upload, annotated QC download, AI evaluation,
                                               duplicate check
Node QC API --> Flask API (PYTHON_URL)  /tracker/view to get tracker details and file URL
Flask + Node --> MySQL mytfs (same database, shared tables such as qc_records)
Flask + Node --> Cloudinary (files) and SMTP (emails)"""),
        ("bullets", [
            "The website decides which API to call per feature. QC form saves and samples go to Node; QC lists, "
            "audits and QC overview come from Flask.",
            "There is no login token. After login the browser keeps the user in sessionStorage and sends "
            "logged_in_user_id in each request; the APIs look up that user's role in the database.",
            "In development, Vite proxies /api/v1 to Node on 8000; Flask is called directly on 5000.",
        ]),

        ("h", "7. Daily automatic jobs"),
        ("table", ["Job", "When", "What it does"], [
            ["Assign daily hours (Flask scheduler, /qc/assign-daily-hours)", "08:00 daily",
             "Writes today's assigned hours per agent from the roster and tenure into temp_qc, and fills automatic "
             "100% QC for days with no file and 0 production (rules: 03, Business rules)."],
            ["Billable report email (billable_report_autosend.py)", "Daily (server cron)",
             "Yesterday's delivered billable hours to the 'Billable' recipients."],
            ["Intraday tracker email (send_tracker_report.py)", "3 times a day (server cron)",
             "Today's trackers so far to the 'Tracker' recipients."],
            ["Previous-day production (send_tracker_report_full_day.py)", "Daily (server cron)",
             "Yesterday's full production to the 'Tracker full' recipients."],
            ["Weekly goal report (weekly_goal_report.py)", "Monday 11:00 IST (server cron)",
             "Last week's (Mon-Sun) agents of teams A and B who missed their weekly goal. Admin and Project Manager "
             "get all agents; each Assistant Manager / Team Lead gets only their own agents. If nobody missed, an "
             "'all achieved' email is sent instead (rules: 03, Business rules)."],
        ]),
        ("p", "Recipients for the billable and the two tracker report emails are managed by Super Admin in Report "
              "emails (table report_email_recipient). The weekly goal report has no recipient list: it goes to "
              "active users by role and reporting line. Check the real schedule on the server with crontab -l."),

        ("h", "8. Golden rules"),
        ("bullets", [
            "Back up the live database before any SQL that changes data (02, Backups).",
            "Never run SQL against live from your laptop. Run it on the server, or in phpMyAdmin: SELECT first and "
            "check the rows, then change them inside START TRANSACTION ... COMMIT.",
            "Flask and Node QC go out from branch main; the website goes out from branch live.",
            "The Node QC API runs the compiled dist folder: after every pull, run npm run build before pm2 restart.",
            "Deploy the backend before the website when the website needs a new endpoint or field.",
            "Release at a quiet time and tell the lead first.",
            "Never delete a tracker row or an agent's uploaded file to fix QC; reset the QC records instead (04, "
            "section 1.1).",
            "Do not commit .env files, database dumps or real passwords.",
        ]),
    ],
}


LOCAL_SETUP_AND_DEPLOYMENT = {
    "number": "02",
    "title": "Setup and Deployment",
    "audience": "Developers",
    "blocks": [
        ("p", "Sections 1 to 7 are local setup on your laptop. Sections 8 to 13 are branches, releases and the "
              "server."),

        ("h", "1. Install"),
        ("table", ["Tool", "Version used", "Notes"], [
            ["Git", "any recent", "Push from your own terminal; GitHub will ask you to sign in."],
            ["Python", "3.11 or newer (3.14 works)", "For the Flask API."],
            ["Node.js and npm", "Node 18+ (24 works), npm 10+", "For the website and the QC API."],
            ["MySQL Server 8", "8.x", "Local database tfs_hrms. MySQL Workbench or HeidiSQL helps."],
        ]),

        ("h", "2. Get the code"),
        ("code", """mkdir Hrms_live && cd Hrms_live
git clone https://github.com/ummehabibasiddiquie/python-backend.git backend-api
git clone https://github.com/ummehabibasiddiquie/node-backend.git   qc-backend
git clone https://github.com/ummehabibasiddiquie/hrms-frontend.git  hrms-frontend-live
cd hrms-frontend-live && git checkout live"""),
        ("p", "The folder names above match the paths used in all documents and scripts."),

        ("h", "3. Local database"),
        ("steps", [
            "Create an empty database: CREATE DATABASE tfs_hrms CHARACTER SET utf8mb4;",
            "Ask the lead for a recent copy of the live database (taken on the server with mysqldump, see section "
            "13) and import it: mysql -u root tfs_hrms < mytfs_backup.sql",
            "Treat the copy as confidential: it holds real names, emails and encrypted passwords. Keep it out of git.",
            "Passwords in tfs_user are encrypted with ENCRYPTION_KEY. Use the same key as live in your backend .env, "
            "or the imported users cannot log in. Use test accounts for each role (ask the lead).",
        ]),
        ("note", "Local data is only a copy. Tracker IDs and QC records on your laptop are not the live ones; never "
                 "fix a live problem by changing your local database."),

        ("h", "4. Environment files"),
        ("p", "Each repository needs a .env file (not in git). Ask the lead for the values (06 lists which ones are "
              "secret); the names are:"),
        ("table", ["Repository", "Variables"], [
            ["backend-api/.env", "DB_HOST, DB_PORT, DB_DATABASE, DB_USERNAME, DB_PASSWORD; ENCRYPTION_KEY; "
                                 "RESET_SECRET_KEY, RESET_TOKEN_TTL_SECONDS, RESET_FRONTEND_URL; SMTP_HOST, SMTP_PORT, "
                                 "SMTP_USER, SMTP_PASS, SMTP_FROM_NAME; CLOUDINARY_CLOUD_NAME, "
                                 "PYTHON_CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET_KEY; API_BASE_URL; BASE_UPLOAD_URL; "
                                 "optional CRON_SECRET"],
            ["qc-backend/.env", "PORT=8000; DB_HOST, DB_PORT, DB_DATABASE, DB_USERNAME, DB_PASSWORD; "
                                "PYTHON_URL (Flask base URL); SMTP_*; CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, "
                                "CLOUDINARY_API_SECRET; ENCRYPTION_SECRET; UPLOADS_DIR; NODE_ENV"],
            ["hrms-frontend-live/.env", "VITE_API_BASE_URL (Flask, e.g. http://127.0.0.1:5000), "
                                        "VITE_API_NODE_BASE_URL (Node, e.g. http://127.0.0.1:8000/api/v1), "
                                        "VITE_API_TIMEOUT, VITE_CONSOLE_LOGS"],
        ]),
        ("note", "With the live Cloudinary keys, files you upload locally go to the live storage. Use test files "
                 "only."),

        ("h", "5. Run the three parts"),
        ("p", "Use three terminals."),
        ("code", """# 1. Flask API on :5000
cd backend-api
python -m venv .venv
.venv\\Scripts\\activate            # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
python app.py

# 2. Node QC API on :8000
cd qc-backend
npm install
npm run dev                       # production style: npm run build && npm start

# 3. Website on :5173
cd hrms-frontend-live
npm install
npm run dev"""),
        ("bullets", [
            "Flask runs with debug on but auto-reload off (use_reloader=False). Restart python app.py after every "
            "backend change.",
            "npm run dev (nodemon) reloads the Node API on change.",
            "Open http://localhost:5173 and log in. Agents land on /agent; everyone else on /dashboard.",
        ]),

        ("h", "6. Useful local tools"),
        ("table", ["Tool", "Where", "Use"], [
            ["Backend unit tests", "backend-api/tests", "python -m unittest (QC auto score, roster rules, report "
                                                        "recipients)."],
            ["SOP screenshots and Word SOPs", "docs/sop", "capture_screenshots.py (Playwright, local only) then "
                                                          "build_sop_docs.py."],
            ["Handover documents", "docs/handover", "build_handover_docs.py rebuilds these files."],
            ["QC tracker reset script", "backend-api/scripts/reset_qc_tracker.py", "See 04, section 1.1."],
        ]),
        ("note", "docs/sop/capture_screenshots.py contains test logins. Keep it local; do not commit or share it "
                 "as it is."),

        ("h", "7. Common setup problems"),
        ("table", ["Problem", "Fix"], [
            ["Login says wrong password for every user", "ENCRYPTION_KEY differs from the one the data was encrypted "
                                                         "with."],
            ["Website shows a connection banner", "Flask or Node is not running, or the VITE_* URLs are wrong."],
            ["QC form cannot load the file", "PYTHON_URL in qc-backend/.env must point to the running Flask API."],
            ["Change in Flask has no effect", "Restart python app.py (no auto-reload)."],
            ["git push hangs", "Run it in your own terminal so the GitHub sign-in window can appear."],
        ]),

        ("h", "8. Branches"),
        ("table", ["Repository", "Release branch", "Other branches"], [
            ["python-backend (backend-api)", "main", "roster-module and older feature branches (not deployed)"],
            ["node-backend (qc-backend)", "main", "roster-module (not deployed)"],
            ["hrms-frontend", "live", "main, production-live, development, roster-module (not deployed)"],
        ]),
        ("p", "Work on a feature branch or directly on the release branch for small fixes, as agreed with the lead. "
              "Only what is on main (backends) and live (website) reaches users."),

        ("h", "9. The server"),
        ("table", ["Item", "Value"], [
            ["Host", "Hostinger VPS srv1255447, IP 72.62.197.92 (Ubuntu), domain tfshrms.cloud"],
            ["Login", "ssh root@72.62.197.92 (password or SSH key from the lead; never written in documents, see 06)"],
            ["Website source / served files", "/root/tfshrms/hrms-frontend  ->  /var/www/tfshrms-frontend (Nginx)"],
            ["Flask API folder", "/root/tfshrms/hrms-backend (venv, pm2 app python-backend)"],
            ["Node QC API folder", "/root/tfshrms/qc-backend (pm2 app node-backend, runs dist/index.js)"],
            ["Nginx site config", "/etc/nginx/sites-available/tfshrms.cloud"],
            ["Database", "MySQL on 127.0.0.1, database mytfs; application user tfs (password in the backend .env)"],
        ]),
        ("p", "~/tfshrms in the commands below is /root/tfshrms when logged in as root."),

        ("h", "10. Releasing a change"),
        ("h2", "10.1 On your laptop"),
        ("code", """git status                     # only the files you mean to ship
git add <files>
git commit -m "Say what changed and why"
git push origin main           # backends
git push origin live           # website"""),
        ("h2", "10.2 Flask API"),
        ("code", """ssh <user>@72.62.197.92
cd ~/tfshrms/hrms-backend
git pull origin main
pip install -r requirements.txt     # only if requirements.txt changed
pm2 restart python-backend
pm2 logs python-backend --lines 50"""),
        ("h2", "10.3 Node QC API"),
        ("code", """cd ~/tfshrms/qc-backend
git pull origin main
npm install            # only if package.json changed; do not use --omit=dev
npm run build          # pm2 runs dist/, so this step is required
pm2 restart node-backend
pm2 logs node-backend --lines 50"""),
        ("h2", "10.4 Website (production)"),
        ("code", """cd /root/tfshrms/hrms-frontend
git pull origin live                 # live is the release branch (not main)
npm install                          # only if package.json changed
npm run build
sudo cp -r dist/* /var/www/tfshrms-frontend/"""),
        ("bullets", [
            "The frontend .env on the server must have VITE_API_BASE_URL = https://tfshrms.cloud/python and "
            "VITE_API_NODE_BASE_URL = https://tfshrms.cloud/api/v1; they are fixed into the build.",
            "No restart is needed; ask users to hard-refresh (Ctrl+F5).",
            "Vercel builds automatically on every push to its connected branch. Use it only for testing; it is not "
            "the live site.",
        ]),
        ("h2", "10.5 Database changes"),
        ("bullets", [
            "SQL migrations are in backend-api/migrations, named by date. Run new ones on mytfs in date order, after "
            "a backup, before restarting the API that needs them.",
            "Some columns and tables are added by the code itself on first use (for example project_sop_links, "
            "goal_locked, sop_topic, sop_item, report_email_recipient, roster_week_lock, kra_day_note). No SQL "
            "is needed for those.",
        ]),
        ("h2", "10.6 After every release"),
        ("steps", [
            "pm2 list: every app shows online and the restart count is not climbing.",
            "pm2 logs <app>: no errors in the first minute.",
            "Log in to the live site as an admin and open the screen you changed.",
            "Tell the users who asked for the change.",
        ]),

        ("h", "11. Everyday server commands"),
        ("code", """pm2 list                              # status of all apps
pm2 logs node-backend --lines 200     # QC API log (QC save errors appear here)
pm2 logs python-backend --lines 200   # Flask log
pm2 restart <app>
pm2 save                              # keep the current app list after a reboot
crontab -l                            # scheduled report emails
df -h                                 # disk space
mysql -u tfs -p mytfs                 # MySQL shell (password from the backend .env)"""),
        ("h2", "11.1 If a pm2 app is missing (for example after a rebuild of the server)"),
        ("code", """pm2 start /root/tfshrms/hrms-backend/venv/bin/python --name python-backend \\
    --cwd /root/tfshrms/hrms-backend -- app.py
cd /root/tfshrms/qc-backend && pm2 start dist/index.js --name node-backend
pm2 save && pm2 startup               # start everything again after a reboot"""),
        ("h2", "11.2 Nginx and SSL"),
        ("code", """sudo nano /etc/nginx/sites-available/tfshrms.cloud   # edit routes
sudo nginx -t                                        # always test before reload
sudo systemctl reload nginx
sudo tail -f /var/log/nginx/error.log                # 502 / 504 errors appear here"""),
        ("bullets", [
            "Routes: see 01, Live addresses. Proxy timeouts are 300 seconds.",
            "client_max_body_size is 10M: uploads bigger than 10 MB are refused by Nginx before reaching the API.",
            "SSL certificates are renewed by Certbot (files under /etc/letsencrypt/live/tfshrms.cloud/).",
        ]),
        ("h2", "11.3 Copying files to and from the server (run on your laptop)"),
        ("code", """scp root@72.62.197.92:/root/backup.sql C:\\Users\\<you>\\Downloads\\
scp C:\\Users\\<you>\\Downloads\\file.sql root@72.62.197.92:/root/tfshrms"""),
        ("h2", "11.4 Weekly goal report"),
        ("p", "A cron script like the other report emails. Run these in /root/tfshrms/hrms-backend."),
        ("code", """venv/bin/python weekly_goal_report.py --dry-run          # who would get what; sends nothing
venv/bin/python weekly_goal_report.py --test-to a@x,b@x   # one [TEST] email to these addresses only
venv/bin/python weekly_goal_report.py --week-start 2026-10-19            # send a past week again
venv/bin/python weekly_goal_report.py --week-start 2026-10-19 --to a@x   # resend to one recipient
tail weekly_goal_report.log                              # what was sent, and errors"""),
        ("bullets", [
            "Schedule (Monday 11:00 IST): one line in crontab -e. With the server on IST: 0 11 * * 1 cd "
            "/root/tfshrms/hrms-backend && venv/bin/python weekly_goal_report.py >> weekly_goal_cron.log 2>&1 (on "
            "UTC use 30 5 * * 1). "
            "Check the zone with timedatectl.",
            "Stop it: put # at the start of that line. Start again: remove the #. Change the time: edit the numbers.",
            "--week-start accepts any date in the week; the report always covers that Monday to Sunday.",
        ]),

        ("h", "12. Where to look when something fails"),
        ("table", ["Symptom", "Look at"], [
            ["\"Could not save QC\" on a QC save", "The reason is in the message; full detail in pm2 logs "
                                                   "node-backend."],
            ["Any other 500 or empty screen", "pm2 logs python-backend; browser developer tools > Network tab."],
            ["502 Bad Gateway / site down", "pm2 list (an app stopped?), then sudo tail /var/log/nginx/error.log."],
            ["Upload fails for large files", "The Nginx upload limit (section 11.2)."],
            ["Report email not received", "crontab -l, the script log files (daily_tracker_report.log, "
                                           "logs/send_tracker_report.log) and Report emails recipients."],
            ["Weekly goal email not received", "weekly_goal_report.log; the person is active, has an email and is "
                                               "Admin, Project Manager, or the agents' Assistant Manager / Team "
                                               "Lead (section 11.4)."],
            ["QC email to agent not received", "pm2 logs node-backend lines starting [Email] or [QC Email]; the "
                                               "agent's user_email."],
        ]),

        ("h", "13. Backups"),
        ("code", """# On the server, before any data change
mysqldump -u tfs -p --single-transaction --routines mytfs > ~/mytfs_backup_$(date +%d%m%Y_%H%M).sql
ls -lh ~/mytfs_backup_*.sql"""),
        ("bullets", [
            "Existing dumps found on the server: /root/mytfs_backup_06102026.sql and /root/mytfs_backup_08102026.sql.",
            "Hostinger also takes VPS backups (hPanel > VPS > Backups).",
            "A backup taken before a mistake is the only way to undo a wrong DELETE or UPDATE.",
        ]),
    ],
}

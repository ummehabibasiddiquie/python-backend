"""Handover documents 05-06: KT checklist and sign-off, credentials register."""

COLUMNS = ["Checklist item", "Done (Y/N)", "Receiver initials", "Remarks"]


def section(title: str, items: list[str]) -> list:
    return [("h2", title), ("table", COLUMNS, [[item, "", "", ""] for item in items])]


KT_CHECKLIST = {
    "number": "05",
    "title": "KT Checklist and Sign-off",
    "audience": "Person handing over and the new developer (both sign)",
    "blocks": [
        ("p", "Purpose: confirm that the knowledge transfer is complete. Go through each item together; the "
              "receiver writes Y and their initials only when they can do it on their own."),
        ("h", "1. Employee details"),
        ("table", ["Field", "Value"], [
            ["Knowledge giver", "Ummehabiba Siddiquie"],
            ["Knowledge receiver", ""],
            ["Department / team", "Development"],
            ["KT start date", ""],
            ["KT end date", ""],
        ]),

        ("h", "2. Access the new developer needs"),
        ("p", "The person handing over arranges each item and ticks its box (☑) once the new developer has it. "
              "Never send passwords by email or chat; share them in person or through the company password manager. "
              "The passwords and keys for these are in 06, the password-protected Credentials Register."),
        ("table", ["Access", "What for", "Given (tick)"], [
            ["GitHub: ummehabibasiddiquie/python-backend (was backend-api)", "Flask API code", "☐"],
            ["GitHub: ummehabibasiddiquie/node-backend (was qc-backend)", "Node QC API code", "☐"],
            ["GitHub: ummehabibasiddiquie/hrms-frontend", "React website code", "☐"],
            ["SSH to the VPS srv1255447 (72.62.197.92)", "Deploying, logs, pm2, Nginx, database backups", "☐"],
            ["Hostinger hPanel", "VPS console, backups, DNS for tfshrms.cloud", "☐"],
            ["MySQL user for the live database mytfs", "Support SQL (04, Support runbook)", "☐"],
            ["Vercel (testing deployments of the website)", "Preview builds from GitHub; not production", "☐"],
            ["Cloudinary account dhgyodnva (login tfsoperation@transformsolution.net)", "All uploaded files "
             "(tracker, QC, project, SOP files)", "☐"],
            ["SMTP mailbox used by the system", "Report, QC and roster emails", "☐"],
            ["HRMS test accounts, one per role (local copy only)", "Testing every role on your laptop", "☐"],
            ["The three .env files (backend, QC backend, frontend)", "Local setup; values come from the lead", "☐"],
        ]),

        ("h", "3. Checklist"),
        *section("3.1 System overview and APIs (documents 01, 03, 07)", [
            "Explains what the HRMS does and the 7 roles",
            "Knows the website, Flask API, Node QC API, MySQL and Cloudinary and how they connect",
            "Knows the live addresses (tfshrms.cloud, /python, /api/v1) and that Vercel is only for testing",
            "Can find a feature's code in each repository",
            "Can look up any endpoint in the API Reference (07): its request fields, who may call it and which "
            "screen uses it",
            "Knows which endpoints have no access check (07, section 5)",
        ]),
        *section("3.2 Local setup (document 02, sections 1 to 7)", [
            "Runs all three apps on their laptop with a local database copy",
            "Logs in as every role on the local copy",
        ]),
        *section("3.3 Server, Nginx and PM2 (document 02, sections 9 and 11)", [
            "Can SSH into the VPS with their own access",
            "Knows the folder layout under /root/tfshrms and /var/www/tfshrms-frontend",
            "Can check pm2 status and logs, restart an app, and pm2 save",
            "Can edit, test (nginx -t) and reload the Nginx config; knows the routes and the 10 MB upload limit",
            "Can copy files to and from the server (scp)",
        ]),
        *section("3.4 Releases (document 02, sections 8 and 10)", [
            "Knows the release branches: main for both backends, live for the website",
            "Has released the Flask API (pull, restart, check logs)",
            "Has released the Node QC API (pull, npm run build, restart)",
            "Has released the website (pull live, build, copy to /var/www/tfshrms-frontend)",
            "Runs new SQL migrations in order after a backup",
        ]),
        *section("3.5 Database (documents 03 section 3, 08, and 02 section 13)", [
            "Can take a backup with mysqldump and restore it",
            "Knows the main tables and the is_delete / is_active rule",
            "Can find any table and column, and how tables link, in the Database Schema (08)",
            "Regenerates 08 after a migration (python docs/handover/build_db_schema.py, then rebuild the documents)",
            "Runs support SQL safely: SELECT first, then a transaction, never from a laptop against live",
        ]),
        *section("3.6 Business rules (document 03 section 1 and the SOPs)", [
            "Tracker and billable hours, tenure, night shift, delete rules",
            "QC: sample size, scoring, Regular / Correction / Rework, cycles and emails",
            "Roster: drafts, submit, approval, week locks, reset, Excel upload",
            "QA hours, KRA, monthly goals, Task EOD Report",
        ]),
        *section("3.7 Support (document 04, section 1)", [
            "Has reset a QC for a tracker (on a test copy)",
            "Can find the cause of a failed QC save (\"Could not save QC\" message and pm2 logs)",
            "Can check scheduled report emails (crontab, logs, recipients)",
            "Can dry-run, test (--test-to), resend and stop or start the weekly goal report (document 02, 11.4)",
        ]),
        *section("3.8 Accounts and access (section 2 and document 06)", [
            "Can push to all three GitHub repositories",
            "Has received the password-protected Credentials Register (06) and its file password in person",
        ]),
        *section("3.9 Open items (document 04, sections 3 to 5)", [
            "Has read the known issues and pending work and agreed priorities with the lead",
        ]),

        ("h", "4. Final assessment"),
        ("table", ["Question", "Answer"], [
            ["Receiver can manage routine operations on their own", "Yes / No"],
            ["Additional KT sessions needed", "Yes / No"],
            ["Pending topics", ""],
        ]),

        ("h", "5. Approval"),
        ("table", ["", "Name", "Signature", "Date"], [
            ["Knowledge giver", "Ummehabiba Siddiquie", "", ""],
            ["Knowledge receiver", "", "", ""],
            ["Manager", "", "", ""],
        ]),
    ],
}


# Built separately by build_credentials_register.py into a password-protected file.
# Cells like "{backend-api:SMTP_PASS}" are filled from that repository's local .env at build time.
CREDENTIALS_REGISTER = {
    "number": "06",
    "title": "Credentials Register",
    "audience": "Person handing over and the new developer only - CONFIDENTIAL",
    "blocks": [
        ("h", "1. How to use this register"),
        ("bullets", [
            "This file holds real passwords and keys. It is protected with a password; give that password to the "
            "new developer in person, never by email or chat.",
            "Values marked \"from local .env\" were copied from the laptop's .env files when the file was built. "
            "Check they match the .env files on the server.",
            "Type the remaining values (server, hPanel, GitHub, Vercel and so on) into the empty cells and save. "
            "Word keeps the file protected when you save it.",
            "Change the server root password before recording it here. The old one was exposed in plain text in a "
            "previous KT document.",
            "Do not copy this file to shared drives, email or git. Change credentials when someone leaves "
            "(section 4).",
        ]),

        ("h", "2. Logins"),
        ("table", ["Credential", "Used for", "Login / username", "Password / key", "Last changed"], [
            ["VPS root login / SSH key", "Server: deploy, logs, pm2, Nginx, backups (ssh root@72.62.197.92, "
                                         "Hostinger VPS srv1255447)", "root", "", ""],
            ["Hostinger hPanel", "VPS console, VPS backups, DNS for tfshrms.cloud", "", "", ""],
            ["MySQL live user", "Both APIs and support SQL (mysql -u tfs -p mytfs on the server)", "tfs", "", ""],
            ["MySQL root (server)", "Database administration on the VPS", "root", "", ""],
            ["Cloudinary dashboard", "Usage, limits and billing (cloud dhgyodnva)",
             "tfsoperation@transformsolution.net", "", ""],
            ["SMTP mailbox", "Report, QC, roster and password reset emails",
             "{backend-api:SMTP_USER}", "{backend-api:SMTP_PASS}", ""],
            ["GitHub", "python-backend, node-backend, hrms-frontend", "ummehabibasiddiquie", "", ""],
            ["GitHub Personal Access Token", "git pull / push on the server, if used", "ummehabibasiddiquie", "", ""],
            ["Vercel", "Testing deployments of the website (not production)", "", "", ""],
            ["HRMS Super Admin", "https://tfshrms.cloud - users, permissions, report emails", "", "", ""],
            ["Gemini API key", "AI evaluation (GOOGLE_GENERATIVE_AI_API_KEY, if used)", "-", "", ""],
        ]),

        ("h", "3. Application secrets (.env files)"),
        ("p", "Server files: /root/tfshrms/hrms-backend/.env (Flask) and /root/tfshrms/qc-backend/.env (Node QC). "
              "The values below are from local .env; the database values on the server are different (live "
              "database mytfs, user tfs)."),
        ("table", ["File", "Setting", "Value", "Used for"], [
            ["Flask", "ENCRYPTION_KEY", "{backend-api:ENCRYPTION_KEY}", "Encrypts every user password. Never change."],
            ["Flask", "RESET_SECRET_KEY", "{backend-api:RESET_SECRET_KEY}", "Signs password reset links"],
            ["Flask", "SMTP_HOST / SMTP_PORT", "{backend-api:SMTP_HOST} / {backend-api:SMTP_PORT}", "Email server"],
            ["Flask", "CLOUDINARY_CLOUD_NAME", "{backend-api:CLOUDINARY_CLOUD_NAME}", "File storage account"],
            ["Flask", "PYTHON_CLOUDINARY_API_KEY", "{backend-api:PYTHON_CLOUDINARY_API_KEY}", "File storage"],
            ["Flask", "CLOUDINARY_API_SECRET_KEY", "{backend-api:CLOUDINARY_API_SECRET_KEY}", "File storage"],
            ["Node QC", "CLOUDINARY_API_KEY", "{qc-backend:CLOUDINARY_API_KEY}", "File storage"],
            ["Node QC", "CLOUDINARY_API_SECRET", "{qc-backend:CLOUDINARY_API_SECRET}", "File storage"],
            ["Node QC", "ENCRYPTION_SECRET", "Not set - the code uses its built-in default",
             "Encrypts agents' saved Gemini keys. Setting it now makes the saved keys unreadable."],
            ["Node QC", "SMTP_USER", "{qc-backend:SMTP_USER}", "QC result emails"],
            ["Both", "DB_PASSWORD (server)", "", "Live MySQL user tfs - type it in"],
        ]),
        ("note", "ENCRYPTION_KEY must never change: every user's password is encrypted with it, so a new key stops "
                 "every login. Use the same key in a local copy that holds live data."),

        ("h", "4. When someone leaves"),
        ("steps", [
            "Change the VPS root password and remove their SSH key from the server.",
            "Change the MySQL passwords and the SMTP password if they knew them.",
            "Rotate the Cloudinary API secret, update both .env files (Flask and Node QC) and restart the pm2 "
            "apps (pm2 restart python-backend, pm2 restart node-backend).",
            "Remove their access to GitHub, Vercel and Hostinger.",
            "Update the values and the Last changed column in this file.",
        ]),
    ],
}

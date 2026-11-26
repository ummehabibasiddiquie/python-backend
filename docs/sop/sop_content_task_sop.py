"""SOP + test guide for the Task SOP maker-checker module (roster-module)."""

TASK_SOP_MODULE = {
    "file": "SOP - Manager - Task SOP Maker Checker",
    "title": "Task SOP (Maker-Checker) - Upload, Approve and Agent View",
    "roles": (
        "Project Manager, Assistant Manager, Admin, Super Admin, QA "
        "(upload / approve); Agent (view in Tracker only)"
    ),
    "blocks": [
        ("h", "1. Purpose"),
        (
            "p",
            "Each task can have its own Standard Operating Procedure as a Word (.docx) file. "
            "A checker uploads a draft; a different checker must approve it before agents follow it. "
            "Until approval, agents still see the last approved (live) SOP in white, and any new draft "
            "in yellow as pending only.",
        ),
        (
            "note",
            "This is different from the organisation SOP Library (Admin) and from Project SOP links "
            "(shared-drive links on the project). Task SOP lives on the task and appears in the "
            "Production Tracker under How to do this task.",
        ),

        ("h", "2. Who does what"),
        (
            "table",
            ["Role", "What they can do"],
            [
                [
                    "Super Admin, Admin, Project Manager, Assistant Manager, QA",
                    "Upload / replace draft, Discard draft, Approve another person's draft, "
                    "Delete live SOP, see No SOP / SOP added / SOP-waiting badges and sidebar SOP count.",
                ],
                [
                    "Uploader (maker)",
                    "Cannot approve their own draft. Another checker must click Approve SOP.",
                ],
                [
                    "Agent / Operations / others",
                    "View only in Tracker (white = live approved, yellow = pending draft). "
                    "No Manage upload or approve buttons.",
                ],
            ],
        ),

        ("h", "3. Process flow (happy path)"),
        (
            "p",
            "Follow this flow for the first SOP on a task. Use the same path for later updates "
            "(live SOP stays white for agents until the new draft is approved).",
        ),
        (
            "table",
            ["Step", "Who", "Action", "What you should see"],
            [
                [
                    "1",
                    "Checker A",
                    "Manage → Projects & Targets → open project → Edit task (or SOP-only for read-only roles)",
                    "Task SOP section; badge may say No SOP",
                ],
                [
                    "2",
                    "Checker A",
                    "Upload .docx (max 25 MB) → Save as draft",
                    "Badge: SOP-waiting for approval; sidebar may show N SOP; email to other checkers",
                ],
                [
                    "3",
                    "Checker B",
                    "Open same task → Approve SOP (not the uploader)",
                    "Badge: SOP added; pending count drops; approval email",
                ],
                [
                    "4",
                    "Agent",
                    "Tracker → select that project and task → How to do this task",
                    "White live SOP HTML (no yellow if no new draft)",
                ],
            ],
        ),
        (
            "note",
            "Flow summary: Upload draft (A) → Waiting for approval → Approve (B) → Live for agents. "
            "There is no separate Reject button. To reject a draft, use Discard draft.",
        ),

        ("h", "4. Where to click in HRMS"),
        ("h2", "4.1 Manage (checkers)"),
        (
            "steps",
            [
                (
                    "Log in as a checker. Open Manage → Projects & Targets.",
                    "proj_02_project_tasks",
                    "Projects and task list",
                ),
                "Active projects are listed first (A–Z), then Inactive. "
                "If any task has a draft, the project shows an amber N SOP chip.",
                "Open a project. On each task name you should see one of: "
                "No SOP (grey), SOP added (green), SOP-waiting for approval (amber). "
                "Both green and amber can show when live exists and a new draft is pending.",
                (
                    "Click Edit (pencil). For full managers the Edit Task modal includes Task SOP. "
                    "For read-only checkers (for example some QA views) the modal may be SOP-only.",
                    "proj_06_edit_task",
                    "Edit Task / Task SOP",
                ),
                "Download the Word template if needed (Task_SOP_Template.docx), fill steps, "
                "save as .docx, upload, optional change note, then Save as draft.",
                "As a different checker, open the same task and click Approve SOP. "
                "Discard draft clears the pending draft without publishing.",
            ],
        ),
        ("h2", "4.2 Tracker (agents)"),
        (
            "steps",
            [
                "Log in as an Agent. Open Production Tracker / Add Tracker.",
                "Choose the Project and Task that has an approved SOP.",
                "In How to do this task: white section = approved live SOP. "
                "Yellow section = draft waiting for approval (do not treat yellow as live).",
                "If a notice modal appears for a new or updated SOP, read it and dismiss. "
                "Follow the white (approved) steps for production work.",
            ],
        ),

        ("h", "5. States cheat sheet"),
        (
            "table",
            ["State", "Manage badges", "Agent Tracker"],
            [
                ["No SOP yet", "No SOP", "No SOP for this task yet"],
                ["Draft only (first upload)", "SOP-waiting for approval", "Yellow draft only (not live)"],
                ["Approved", "SOP added", "White live SOP"],
                [
                    "Approved + new draft",
                    "SOP added + SOP-waiting for approval",
                    "White live + yellow pending",
                ],
            ],
        ),

        ("h", "6. File rules"),
        (
            "bullets",
            [
                "Format: Word .docx only.",
                "Maximum size: 25 MB. Compress or remove large screenshots if upload fails.",
                "Upload goes straight to Cloudinary (folder hrms/task_sop) so large files are not "
                "blocked by the web host body limit.",
                "Stored file name pattern: TaskName_ProjectCode_SOP_DD-Mon-YYYY.docx (no username).",
                "Template path in the app: /templates/Task_SOP_Template.docx.",
            ],
        ),

        ("h", "7. Emails (what to expect)"),
        (
            "table",
            ["When", "Who gets mail", "Subject idea"],
            [
                [
                    "Save as draft",
                    "Admin, Super Admin, Project Manager, Assistant Manager "
                    "(not the uploader; QA is not on this mail list)",
                    "Task SOP added/updated — please approve: Project / Task",
                ],
                [
                    "Approve SOP",
                    "Those roles plus maker and approver",
                    "Task SOP approved: Project / Task",
                ],
            ],
        ),

        ("h", "8. Test plan (run in this order)"),
        ("h2", "8.1 Prep"),
        (
            "bullets",
            [
                "Use two checker accounts (A and B) that are not the same user, plus one Agent account.",
                "Pick a test project with at least one task (or create a throwaway task).",
                "Prepare a small .docx under 25 MB and one file that is not .docx for negative tests.",
            ],
        ),
        ("h2", "8.2 Cases"),
        (
            "table",
            ["#", "Case", "Steps", "Pass if"],
            [
                [
                    "T1",
                    "First SOP happy path",
                    "A uploads + Save as draft → B Approves → Agent opens Tracker",
                    "Waiting badge then SOP added; agent sees white SOP; no yellow",
                ],
                [
                    "T2",
                    "Self-approve blocked",
                    "A uploads draft → A clicks Approve",
                    "Approve not allowed / must be another checker",
                ],
                [
                    "T3",
                    "Update while live exists",
                    "With SOP added, A uploads new draft → Agent views → B Approves",
                    "Agent sees white old + yellow new until approve; then new white only",
                ],
                [
                    "T4",
                    "Discard draft (live remains)",
                    "Live + draft → Discard draft",
                    "Waiting badge gone; SOP added remains; agent white only",
                ],
                [
                    "T5",
                    "Discard draft-only",
                    "Draft only → Discard",
                    "Back to No SOP",
                ],
                [
                    "T6",
                    "Delete live",
                    "Approve then Delete live SOP (if available)",
                    "No SOP for agents",
                ],
                [
                    "T7",
                    "File validation",
                    "Try non-.docx and >25 MB",
                    "Clear error; draft not saved",
                ],
                [
                    "T8",
                    "Sidebar count",
                    "Create drafts on 2 tasks in one project",
                    "Sidebar shows 2 SOP; after both approved, chip gone",
                ],
                [
                    "T9",
                    "Agent cannot manage",
                    "Log in as Agent; open Manage if visible",
                    "No upload / Approve on Task SOP",
                ],
                [
                    "T10",
                    "Project list order",
                    "Filter All on Projects & Targets",
                    "Active projects first, then A–Z; Inactive after",
                ],
            ],
        ),

        ("h", "9. Common problems"),
        (
            "table",
            ["Problem", "What to check"],
            [
                [
                    "Sidebar shows N SOP but all tasks say No SOP",
                    "API must be restarted after deploy so /task_sop/project_status is live. "
                    "Refresh the page. Do not run two Flask processes on the same port.",
                ],
                [
                    "Unable to load data / Network error after a backend change",
                    "Only one backend on port 5000; restart python app.py; hard-refresh the browser.",
                ],
                [
                    "Approve button missing or disabled for the uploader",
                    "Expected. Log in as a different checker.",
                ],
                [
                    "Upload fails around a few MB on hosted frontends",
                    "App uses direct Cloudinary sign+upload. Confirm Cloudinary env vars and 25 MB limit.",
                ],
                [
                    "Agent follows yellow text",
                    "Yellow is pending only. Production must follow white approved SOP.",
                ],
            ],
        ),

        ("h", "10. Sign-off checklist"),
        (
            "bullets",
            [
                "T1–T10 executed and results noted (pass / fail / blocked).",
                "At least one real email received for draft and for approve (or confirmed skipped only in local dry-run).",
                "Agent confirmed white SOP matches the approved Word content.",
                "No leftover test drafts on live production tasks (Discard or Approve).",
            ],
        ),
    ],
}

TASK_SOP_SOPS = [TASK_SOP_MODULE]

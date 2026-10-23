"""
Build one Word SOP per HRMS module from docs/sop/screenshots.

Usage (from backend-api):
    python docs/sop/capture_screenshots.py   # refresh screenshots first (optional)
    python docs/sop/build_sop_docs.py
Output: docs/sop/word/SOP - <Role> - <Module>.docx
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

HERE = Path(__file__).resolve().parent
SHOTS = HERE / "screenshots"
OUT = HERE / "word"
VERSION = "1.0"
ISSUED = date(2026, 10, 21).strftime("%d %b %Y")
BRAND = RGBColor(0x1D, 0x4E, 0xD8)
SCREENSHOT_NOTE = (
    "Screenshots are taken from the HRMS test copy. Names, dates and numbers are examples only."
)

# Each step: (instruction, screenshot file name or None, caption)
SOPS = [
    # ------------------------------------------------------------------ Agent
    {
        "file": "SOP - Agent - Production Tracker",
        "title": "Production Tracker",
        "roles": "Agent",
        "purpose": (
            "Agents record every piece of work in the Production Tracker. Each entry carries the "
            "project, task, shift, production and the output Excel file. Billable hours, QC and KRA "
            "are all calculated from these entries, so they must be added on time and correctly."
        ),
        "steps": [
            ("Log in. Agents land on the Tracker page. The table lists your entries for the selected "
             "dates. Use From / To, Project and Task to filter, and Export to download the list.",
             "agent_01_tracker", "Production Tracker - your entries"),
            ("Click Add Tracker. Choose the Project, Task and Shift. Base Target fills in from the task. "
             "Enter Production, add an optional note (up to 200 characters) and upload the output file.",
             "agent_02_add_tracker", "Add New Tracker form"),
            ("Click Submit Entry. The entry appears in the table straight away with its billable hours.",
             None, ""),
            ("If the project has SOP links, a 'Project SOP' link appears under Project Name. Click it to "
             "open the SOP in a new browser tab. You can only view it.", None, ""),
        ],
        "rules": [
            "Upload the file in Excel format (.xlsx or .xls), maximum 10 MB.",
            "Billable hours = Production / your tenure target for the task.",
            "Night shift: entries added between 00:00 and 09:00 are recorded on the previous date, "
            "because they belong to the shift that started the evening before.",
            "You can delete your own entry only on the day you added it. Night-shift entries added "
            "between 00:00 and 09:00 can also be deleted on the next calendar day. After that, ask your "
            "manager.",
            "Projects with Duplicate Check on reject rows that were already submitted.",
            "QA checks your file within 24 working hours (48 for night files added after midnight). "
            "Weekends and holidays do not count.",
        ],
        "problems": [
            ("The delete button is missing", "The entry is older than the delete window. Ask your manager."),
            ("Upload failed", "Check the file is .xlsx/.xls and under 10 MB, then try again."),
            ("Billable hours look wrong", "Check Production and the Task selected; the target comes from the task."),
        ],
    },
    {
        "file": "SOP - Agent - Reports and KRA",
        "title": "Overview, Billable & QC Report and KRA",
        "roles": "Agent",
        "purpose": (
            "Agents use Analytics to follow their own billable hours, QC scores and monthly KRA, and "
            "My Roster to see their working days, week offs and leave."
        ),
        "steps": [
            ("Open Analytics > Overview for a quick summary of the selected dates.",
             "agent_03_overview", "Overview"),
            ("Open Billable & QC Report. Daily Report shows each day's assigned hours, worked hours, QC "
             "score, tracker count and the hours still required per day. Use Monthly Report for the month "
             "and QC Report for your QC results. Export downloads the table.",
             "agent_04_billable_qc_report", "Billable & QC Report - Daily"),
            ("Open KRA and choose the month. The cards show Productivity, Quality, Roster and Reporting "
             "and the overall KRA %. The table shows every day.",
             "agent_05_kra", "Monthly KRA"),
            ("Open My Roster to see your schedule for the month.", "agent_06_my_roster", "My Roster"),
        ],
        "rules": [
            "KRA weights: Productivity 33%, Quality 33%, Roster 10%, Reporting 14% (as shown on the KRA cards).",
            "Productivity: a day counts as Yes when billable hours meet the target (9 h full day, 4.5 h half day).",
            "Quality: a day counts as Yes when the QC score is 98% or more.",
            "Reporting: days with fewer than 7 trackers (full day) or 4 (half day) count as low tracker days.",
            "Half-day leave and half working days count as half a working day.",
        ],
        "problems": [
            ("A QC score is blank", "QA has not checked that day's files yet."),
            ("Roster day looks wrong", "Ask your manager to correct the roster; it goes to admin for approval."),
        ],
    },
    # ------------------------------------------------------------------ QA
    {
        "file": "SOP - QA - QC Form",
        "title": "Agent Files and QC Form",
        "roles": "QA",
        "purpose": (
            "QA checks a sample of every agent file, marks errors per record and decides whether the "
            "file is Regular (passed), Correction or Rework. The marked file is saved for the agent and "
            "managers."
        ),
        "steps": [
            ("Open Agent Files & QC Report > Agent's Tracker File. 'Urgent Files - do these first' lists "
             "files that are overdue or have 4 working hours or less left. Below it, files are grouped by "
             "project and task.", "qa_02_agent_files", "Agent's Tracker File and urgent list"),
            ("Click QC Form on a file. The form opens with the sample: the task's QC % of the file's rows, "
             "rounded up. Use 'Click to Download' to open the agent's full file.",
             "qa_05_qc_form", "QC Form with the sample"),
            ("For each record, pick a Category and then the errors. Each error takes its points off that "
             "category. The Record Score and the overall QC score update as you mark.", None, ""),
            ("To check a row that was not sampled, choose it in 'Add a record from the file' (it shows the "
             "QC code) and click Add record. It is included in the score.", None, ""),
            ("Click Submit, choose the result, write comments that refer to the QC Code (not the Excel row "
             "number), and click Confirm & Submit.", None, ""),
            ("Files the agent sends back after Correction or Rework appear in Agent's Rework & Correction "
             "File. Open them the same way.", "qa_03_rework_correction_files",
             "Agent's Rework & Correction File"),
            ("QC Report shows the QC you have done.", "qa_04_my_qc_report", "My QC Report"),
        ],
        "rules": [
            "Sample size = task QC % x number of records in the file, rounded up (10% when the task has none).",
            "Each category starts at 100. A record's score is the average of its category scores. An error "
            "worth 100 points or more makes that record 0.",
            "The file's QC score is the average of all record scores on the form, including added records.",
            "100% = Regular (completed). 98% to 99.99% = Correction. Below 98% = Rework.",
            "Correction: the agent corrects the marked sample and uploads it again. Rework: the agent reworks "
            "the whole file.",
            "Deadline: 24 working hours from submission (48 for night files added after midnight). Weekends "
            "and holidays pause the clock. In the screenshots the overdue times are examples only.",
        ],
        "problems": [
            ("'Every file record is already on the form'", "All rows of the file are already sampled or added."),
            ("Internal server error on submit", "Do not refill the form repeatedly. Note the tracker and report it "
             "to the HRMS team with a screenshot."),
            ("Wrong record marked", "Remove the error from Selected Errors before you submit."),
        ],
    },
    {
        "file": "SOP - QA - Reports and Hours",
        "title": "QA Reports, Hours and Roster",
        "roles": "QA",
        "purpose": "QA tracks their own reporting hours and sees agent, audit and KRA reports.",
        "steps": [
            ("Analytics > Overview gives the summary for the selected dates.", "qa_01_overview", "Overview"),
            ("My Report > Tracker: add your non-QC work (training, reporting, other) with Add Tracker. "
             "Daily Report and Monthly Report total your hours.", "qa_06_my_report_hours",
             "My Report - Feedback & Reporting Tracker"),
            ("Tracker Report lists agents' tracker entries.", "qa_07_tracker_report", "Tracker Report"),
            ("Agents Billable Report shows agents' billable hours by day and month.",
             "qa_08_agents_billable", "Agents Billable Report"),
            ("Audit Report shows the audits done on your QC.", "qa_09_audit_report", "Audit Report"),
            ("KRA shows your monthly KRA.", "qa_10_kra", "KRA"),
            ("My Roster shows your schedule.", "qa_11_my_roster", "My Roster"),
            ("SOPs opens the SOP library (view only).", "qa_12_sops", "SOP library"),
        ],
        "rules": [
            "Add your reporting tracker entries on the same day.",
            "You can delete your own reporting entry within 24 hours.",
        ],
        "problems": [
            ("Hours missing in Daily Report", "Check the entry date and that it was saved in My Report > Tracker."),
        ],
    },
    # ------------------------------------------------------------------ Manager
    {
        "file": "SOP - Manager - Projects and Tasks",
        "title": "Projects & Targets",
        "roles": "Project Manager, Assistant Manager, Admin, Super Admin",
        "purpose": (
            "Managers set up projects and tasks: who works on them, the targets, the QC sample % and QA "
            "hour targets, and the SOP links agents and QA open from their screens."
        ),
        "steps": [
            ("Open Manage > Projects & Targets. Search, filter Active / Inactive and pick a project on the "
             "left. The right side shows its tasks with Target / Hr and QC target.",
             "mgr_02_projects", "Project Management"),
            ("Click Add Project, or Edit on a project. Fill Project Name, Code, Category, Project Manager, "
             "Assistant Project Manager(s), Quality Analyst(s) and Agent(s). Turn on AI Evaluation or "
             "Duplicate Check if needed.", "mgr_03_edit_project", "Edit Project"),
            ("Under SOP Links (shared drive), enter a title, paste the drive link and click Add link. Share "
             "the file on the drive as Viewer first. Click Update Project to save.", None, ""),
            ("Click Add Task, or the edit icon on a task. Set the task name, Target / Hr, team, QC % and the "
             "important columns QA sees on the QC form.", None, ""),
            ("In the task's QA hour criteria, set only one type: minutes per QC record, minutes per file, or "
             "object-count ranges. Entering one type clears the other two.", None, ""),
            ("Use the Status switch to make a project or task Active / Inactive. Delete removes unused "
             "projects; projects with history are deactivated instead.", None, ""),
        ],
        "rules": [
            "Project Name, Code, Assistant Project Manager, QA and Agents are required.",
            "SOP links must start with https://. The HRMS only opens the link; who can edit the file is set on "
            "the drive.",
            "QC % decides the sample size on the QC form.",
            "Only one QA hour criteria type can be active per task.",
        ],
        "problems": [
            ("Agent cannot see the project", "Check the agent is selected under Agent(s) and the project is Active."),
            ("SOP link opens 'Request access'", "Share the file on the drive with the team as Viewer."),
        ],
    },
    {
        "file": "SOP - Manager - Roster",
        "title": "Roster Management",
        "roles": "Project Manager, Assistant Manager, Assistant Team Leader",
        "purpose": (
            "Managers keep each employee's monthly roster: working days, shifts, week offs, holidays and "
            "leave. Every change goes to admin for approval before it counts for targets and KRA."
        ),
        "steps": [
            ("Open Manage > Roster Management > Roster Calendar. Pick the Month, Team and Employee, then a "
             "week tab. Locked weeks are listed in yellow.", "mgr_14_roster_calendar", "Roster Calendar"),
            ("Click a day to edit it. Choose the Day Type (Working, Week Off, Leave, Left), Shift (Day / "
             "Night) and Working Hours, then Save Day Change Request. The day shows as pending.",
             "mgr_15_roster_day_edit", "Edit Roster Day"),
            ("Changed your mind? Edit the same day again. The newer change replaces the earlier one, so only "
             "one change per day goes for approval.", None, ""),
            ("When you have finished the month or week, click Submit for approval. Each edited week goes to "
             "admin.", None, ""),
            ("Track your changes in My Submissions (Draft, Pending, Approved, Rejected).",
             "mgr_16_roster_submissions", "My Submissions"),
            ("Holiday Master lists the organisation holidays.", "mgr_17_roster_holidays", "Holiday Master"),
            ("Use Generate Missing Rosters for new employees, and Excel Upload to change many days at once.",
             None, ""),
        ],
        "rules": [
            "The employee must have a tracker joining date before their roster can be edited.",
            "Leave or half day cannot be added on a holiday; set Working if the person must work.",
            "A week is locked after admin approves it. Ask admin to unlock it for further changes.",
            "Approving a roster does not send an email. Use Send email on the week tab.",
        ],
        "problems": [
            ("Cannot click a day", "The week is locked. Ask admin to unlock it."),
            ("'Tracker joining date is not set'", "Ask admin to set the joining date in User Management."),
        ],
    },
    {
        "file": "SOP - Manager - Reports",
        "title": "Analytics and Reports",
        "roles": "Project Manager, Assistant Manager, Admin, Super Admin",
        "purpose": "Managers follow billable hours, monthly goals, QA hours and KRA for their teams.",
        "steps": [
            ("Analytics > Overview: active agents, billable vs assigned hours and the latest QC files.",
             "mgr_01_overview", "Overview"),
            ("Billable Report > Daily Report: each agent's day. Export downloads all agents.",
             "mgr_04_billable_daily", "Billable Report - Daily"),
            ("Billable Report > Monthly Report: billable hours delivered, monthly goal, pending target and "
             "average QC per agent. Export Month downloads the table.", "mgr_05_billable_monthly",
             "Billable Report - Monthly"),
            ("User Monthly Report and Project Monthly Report show monthly goals by user and by project.",
             "mgr_06_user_monthly_report", "User Monthly Report"),
            ("Project Monthly Report.", "mgr_07_project_monthly_report", "Project Monthly Report"),
            ("QA Report shows QA hours.", "mgr_08_qa_report", "QA Report"),
            ("KRA shows each person's monthly KRA.", "mgr_09_kra", "KRA"),
            ("Tracker Report lists every tracker entry with filters.", "mgr_10_tracker_report", "Tracker Report"),
        ],
        "rules": [
            "Billable report exports include a Tenure column for admins and managers only.",
            "Monthly goal = monthly target + extra assigned hours.",
        ],
        "problems": [
            ("A number looks wrong", "Check the date range and the roster for that person and day."),
        ],
    },
    {
        "file": "SOP - Manager - QC Report Overview and QA Audit",
        "title": "QC Report Overview and QA Agent Audit",
        "roles": "Project Manager, Assistant Manager, Admin, Super Admin",
        "purpose": (
            "QC Report Overview shows every QC result with its errors and files. QA Agent Audit lets "
            "managers review QA work."
        ),
        "steps": [
            ("Open QC Report Overview. Filter by Agent, QC, Project, Task and Work Date. Each row shows "
             "records, QC sample, errors, score and error type. Click View for the errors, the download icon "
             "for the marked QC file, and the arrow for rework and correction history.",
             "mgr_11_qc_report_overview", "QC Report Overview"),
            ("Exports: Export Excel (the table), Export History (rework and correction cycles), Consolidated "
             "Export, and Error Report (only files with errors, with how many times each error appears in "
             "each file).", None, ""),
            ("Open QA Agent Audit > QA Agent Audit Form to see each QA's records and average score, and audit "
             "their work.", "mgr_12_qa_agent_audit_form", "QA Agent Audit Form"),
            ("QA Agent Audit Report lists the audits done.", "mgr_13_qa_agent_audit_report",
             "QA Agent Audit Report"),
        ],
        "rules": [
            "Work Date filters by the agent's file date, not the QC date.",
            "The downloaded QC file has error rows highlighted and the errors in the last column.",
        ],
        "problems": [
            ("Score shows 0% with no errors", "Report it to the HRMS team with the tracker number."),
        ],
    },
    {
        "file": "SOP - Assistant Team Leader",
        "title": "Assistant Team Leader",
        "roles": "Assistant Team Leader",
        "purpose": (
            "Assistant Team Leaders view their team's numbers and keep the team roster. Other screens are "
            "view only."
        ),
        "steps": [
            ("Analytics > Overview for the team summary.", "atl_01_overview", "Overview"),
            ("Tracker Report for the team's entries.", "atl_02_tracker_report", "Tracker Report"),
            ("Manage > Roster Management to edit the team roster and submit it for approval (see SOP - "
             "Manager - Roster). Manage > SOPs opens the SOP library.", "atl_03_manage", "Manage"),
        ],
        "rules": ["Assistant Team Leaders cannot change users, projects or trackers."],
        "problems": [("A button is greyed out", "That action is view only for your role.")],
    },
    # ------------------------------------------------------------------ Admin
    {
        "file": "SOP - Admin - Users, AFD and Categories",
        "title": "User Management, AFD and Project Category",
        "roles": "Admin, Super Admin",
        "purpose": (
            "Admins create and maintain users and the QC error lists (AFD) that drive QC scoring."
        ),
        "steps": [
            ("Manage > User Management: filter by name, email, team or role. Add User creates a user; the "
             "edit icon changes details; the switch activates or deactivates.", "admin_02_users",
             "User Management"),
            ("When adding an Agent or QA, fill the Tracker Joining Date and the Tenure. Tenure scales the "
             "agent's target.", None, ""),
            ("Manage > AFD Management: create an AFD with its Categories and Subcategories (errors) and the "
             "points each error takes off.", "admin_04_afd", "AFD Management"),
            ("Manage > Project Category: link a category to its AFD. Projects in that category use that error "
             "list on the QC form.", "admin_05_category", "Project Category"),
        ],
        "rules": [
            "Tracker Joining Date is required for Agent and QA.",
            "An error worth 100 points or more is fatal: the record scores 0.",
        ],
        "problems": [
            ("QA sees no errors to pick", "Check the project's category is linked to an AFD."),
        ],
    },
    {
        "file": "SOP - Admin - Roster Approval",
        "title": "Roster Approval",
        "roles": "Admin, Super Admin",
        "purpose": "Admins approve or reject roster changes submitted by managers.",
        "steps": [
            ("Open Manage > Roster Management > Approval Queue. Filter Pending / Approved / Rejected / All and "
             "search by employee. Open Details to see the change.", "admin_06_roster_approval",
             "Approval Queue"),
            ("Approve a single request, or select several and approve them together. Rejecting needs a "
             "comment.", None, ""),
            ("Roster Calendar shows the result. Approved weeks are locked; unlock a week to let managers "
             "change it again.", "admin_07_roster_calendar", "Roster Calendar"),
        ],
        "rules": [
            "Selected requests are applied oldest first, so the latest change for a day is what remains.",
            "Approving locks the week for managers.",
        ],
        "problems": [
            ("Two changes for the same day", "Approve both; the later one is applied last. Or reject the older one."),
        ],
    },
    {
        "file": "SOP - Admin - SOP Library",
        "title": "SOP Library",
        "roles": "Admin, Super Admin, Project Manager, Assistant Manager (manage); everyone (view)",
        "purpose": "The SOP library holds the organisation's SOPs as links or uploaded documents.",
        "steps": [
            ("Open Manage > SOPs (or SOPs in the top menu). Create a topic, then add a link or a document "
             "under it.", "admin_09_sops_manage", "SOP library - manage"),
            ("Everyone else opens the same library from SOPs and can only view.", "qa_12_sops",
             "SOP library - view"),
        ],
        "rules": [
            "Links must start with https://.",
            "Upload these Word SOPs here, one topic per role.",
        ],
        "problems": [("Cannot add an item", "Only Admin, Super Admin, Project Manager and Assistant Manager can add.")],
    },
    {
        "file": "SOP - Super Admin - Permissions and Report Emails",
        "title": "User Permission and Report Emails",
        "roles": "Super Admin",
        "purpose": "Super Admin controls who can create users and projects, and who receives the report emails.",
        "steps": [
            ("Manage > User Permission: switch User Creation and Project Creation on or off per person.",
             "sa_01_permissions", "User Permissions"),
            ("Report emails: add a recipient, choose TO or CC and the reports they get - Billable hours "
             "(yesterday), Intraday tracker (3 times a day) and Previous-day production. Use the bin icon to "
             "remove someone.", "sa_02_report_emails", "Report emails"),
        ],
        "rules": ["Changes apply from the next scheduled email."],
        "problems": [("Someone did not get an email", "Check they are listed with that report switched on.")],
    },
]


def set_cell_shading(cell, hex_color: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tc_pr.append(shd)


def add_heading(doc: Document, text: str, level: int) -> None:
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = BRAND


def legacy_blocks(sop: dict) -> list:
    """Older SOP entries (purpose / steps / rules / problems) as blocks."""
    return [
        ("h", "1. Purpose"),
        ("p", sop["purpose"]),
        ("h", "2. Who can use it"),
        ("p", sop["roles"]),
        ("h", "3. Steps"),
        ("steps", [(t, s, c) if s else t for t, s, c in sop["steps"]]),
        ("h", "4. Rules to remember"),
        ("bullets", sop["rules"]),
        ("h", "5. Common problems"),
        ("table", ["Problem", "What to do"], [list(p) for p in sop["problems"]]),
    ]


class Renderer:
    def __init__(self, doc: Document):
        self.doc = doc
        self.figure = 0
        self.missing: list[str] = []

    def image(self, shot: str, caption: str) -> None:
        path = SHOTS / f"{shot}.png"
        if not path.exists():
            self.missing.append(shot)
            self.doc.add_paragraph(f"[Screenshot missing: {shot}.png]")
            return
        self.figure += 1
        self.doc.add_picture(str(path), width=Inches(6.7))
        self.doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap = self.doc.add_paragraph(f"Figure {self.figure}: {caption}")
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.runs[0].italic = True
        cap.runs[0].font.size = Pt(9)

    def table(self, headers: list[str], rows: list[list[str]]) -> None:
        table = self.doc.add_table(rows=1, cols=len(headers))
        table.style = "Table Grid"
        for cell, text in zip(table.rows[0].cells, headers):
            cell.text = text
            set_cell_shading(cell, "1D4ED8")
            run = cell.paragraphs[0].runs[0]
            run.bold = True
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        for values in rows:
            for cell, text in zip(table.add_row().cells, values):
                cell.text = text
        self.doc.add_paragraph()

    def steps(self, items: list) -> None:
        for number, item in enumerate(items, start=1):
            text, shot, caption = (item, None, "") if isinstance(item, str) else item
            p = self.doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.3)
            p.paragraph_format.first_line_indent = Inches(-0.3)
            p.paragraph_format.space_after = Pt(4)
            lead = p.add_run(f"{number}.  ")
            lead.bold = True
            p.add_run(text)
            if shot:
                self.image(shot, caption)

    def note(self, text: str) -> None:
        table = self.doc.add_table(rows=1, cols=1)
        table.style = "Table Grid"
        cell = table.rows[0].cells[0]
        cell.text = text
        set_cell_shading(cell, "FEF3C7")
        self.doc.add_paragraph()

    def render(self, blocks: list) -> None:
        for block in blocks:
            kind = block[0]
            if kind == "h":
                add_heading(self.doc, block[1], 1)
            elif kind == "h2":
                add_heading(self.doc, block[1], 2)
            elif kind == "p":
                self.doc.add_paragraph(block[1])
            elif kind == "note":
                self.note(block[1])
            elif kind == "bullets":
                for text in block[1]:
                    self.doc.add_paragraph(text, style="List Bullet")
            elif kind == "steps":
                self.steps(block[1])
            elif kind == "img":
                self.image(block[1], block[2])
            elif kind == "table":
                self.table(block[1], block[2])
            else:
                raise ValueError(f"Unknown block type: {kind}")


def build(sop: dict) -> tuple[Path, list[str]]:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    for section in doc.sections:
        section.left_margin = section.right_margin = Inches(0.8)
        section.top_margin = section.bottom_margin = Inches(0.8)
        footer = section.footer.paragraphs[0]
        footer.text = f"TFS HRMS - SOP - {sop['title']} - v{VERSION}"
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER

    title = doc.add_heading(f"SOP: {sop['title']}", level=0)
    for run in title.runs:
        run.font.color.rgb = BRAND

    meta = doc.add_table(rows=4, cols=2)
    meta.style = "Table Grid"
    meta.alignment = WD_TABLE_ALIGNMENT.CENTER
    for row, (label, value) in zip(meta.rows, [
        ("Module", sop["title"]),
        ("Who uses it", sop["roles"]),
        ("Version", VERSION),
        ("Issued", ISSUED),
    ]):
        row.cells[0].text = label
        row.cells[1].text = value
        set_cell_shading(row.cells[0], "DBEAFE")
        row.cells[0].paragraphs[0].runs[0].bold = True

    note = doc.add_paragraph(SCREENSHOT_NOTE)
    note.runs[0].italic = True
    note.runs[0].font.size = Pt(9)

    renderer = Renderer(doc)
    renderer.render(sop.get("blocks") or legacy_blocks(sop))

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{sop['file']}.docx"
    doc.save(str(path))
    return path, renderer.missing


def all_sops() -> list[dict]:
    from sop_content_admin import ADMIN_SOPS
    from sop_content_agent import AGENT_SOPS
    from sop_content_manager import MANAGER_SOPS
    from sop_content_qc_roster import DETAILED_SOPS as QC_ROSTER_SOPS

    DETAILED_SOPS = AGENT_SOPS + QC_ROSTER_SOPS + MANAGER_SOPS + ADMIN_SOPS
    replaced_by_detailed = {
        "SOP - QA - QC Form",
        "SOP - Manager - Roster",
        "SOP - Admin - Roster Approval",
        "SOP - Agent - Reports and KRA",
    }
    detailed_files = {s["file"] for s in DETAILED_SOPS}
    legacy = [s for s in SOPS if s["file"] not in replaced_by_detailed | detailed_files]
    return DETAILED_SOPS + legacy, replaced_by_detailed


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(HERE))
    sops, retired = all_sops()
    for name in retired:
        (OUT / f"{name}.docx").unlink(missing_ok=True)
    all_missing: list[str] = []
    for sop in sops:
        path, missing = build(sop)
        all_missing += missing
        print("wrote", path.name)
    print("missing screenshots:", sorted(set(all_missing)) or "none")

"""Generate manager RBAC PDF and separate Admin/Super Admin PDF."""
import shutil

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable,
)
from reportlab.lib.colors import HexColor

OUT_MGR = r"c:\Users\UmmehabibaSiddiquie\Desktop\Hrms_live\output\pdf\HRMS_Role_Based_Access_Control.pdf"
OUT_MGR_DOCS = r"c:\Users\UmmehabibaSiddiquie\Desktop\Hrms_live\docs\HRMS_Role_Based_Access_Control.pdf"
OUT_ADM = r"c:\Users\UmmehabibaSiddiquie\Desktop\Hrms_live\output\pdf\HRMS_Admin_Super_Admin_Access.pdf"
OUT_ADM_DOCS = r"c:\Users\UmmehabibaSiddiquie\Desktop\Hrms_live\docs\HRMS_Admin_Super_Admin_Access.pdf"

NAVY = HexColor("#1B3A5F")
BLUE = HexColor("#2E5A88")
LIGHT = HexColor("#E8EEF5")
ROW_ALT = HexColor("#F5F8FB")
BORDER = HexColor("#C5D0DE")
MUTED = HexColor("#5A6A7A")

PAGE_W, PAGE_H = A4
MARGIN = 0.65 * inch


def make_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=8,
            leading=26,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverSub",
            fontName="Helvetica",
            fontSize=11,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=4,
            leading=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H1Doc",
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=NAVY,
            spaceBefore=14,
            spaceAfter=8,
            leading=16,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H2Doc",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=BLUE,
            spaceBefore=10,
            spaceAfter=5,
            leading=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyDoc",
            fontName="Helvetica",
            fontSize=9,
            textColor=HexColor("#222222"),
            alignment=TA_JUSTIFY,
            spaceAfter=5,
            leading=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BulletDoc",
            fontName="Helvetica",
            fontSize=9,
            textColor=HexColor("#222222"),
            leftIndent=12,
            spaceAfter=2,
            leading=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Cell",
            fontName="Helvetica",
            fontSize=7.5,
            textColor=HexColor("#222222"),
            leading=9.5,
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CellLeft",
            fontName="Helvetica",
            fontSize=7.5,
            textColor=HexColor("#222222"),
            leading=9.5,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CellHead",
            fontName="Helvetica-Bold",
            fontSize=7.5,
            textColor=colors.white,
            leading=9.5,
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CellHeadLeft",
            fontName="Helvetica-Bold",
            fontSize=7.5,
            textColor=colors.white,
            leading=9.5,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="NoteDoc",
            fontName="Helvetica-Oblique",
            fontSize=8,
            textColor=MUTED,
            spaceBefore=4,
            spaceAfter=6,
            leading=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FooterNote",
            fontName="Helvetica",
            fontSize=8,
            textColor=MUTED,
            alignment=TA_CENTER,
            leading=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Callout",
            fontName="Helvetica",
            fontSize=8.5,
            textColor=NAVY,
            backColor=LIGHT,
            borderPadding=6,
            spaceBefore=6,
            spaceAfter=8,
            leading=11,
            alignment=TA_LEFT,
        )
    )
    return styles


def header_footer_factory(title_left, footer_left):
    def header_footer(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, PAGE_H - 28, PAGE_W, 28, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(MARGIN, PAGE_H - 18, title_left)
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 18, "Confidential - Internal Use")
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, 40, PAGE_W - MARGIN, 40)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(MARGIN, 28, footer_left)
        canvas.drawRightString(PAGE_W - MARGIN, 28, f"Page {doc.page}")
        canvas.restoreState()

    return header_footer


def make_table(styles, headers, rows, col_widths):
    head = [
        Paragraph(h, styles["CellHeadLeft"] if i == 0 else styles["CellHead"])
        for i, h in enumerate(headers)
    ]
    data = [head]
    for row in rows:
        data.append(
            [
                Paragraph(str(c), styles["CellLeft"] if i == 0 else styles["Cell"])
                for i, c in enumerate(row)
            ]
        )
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for i in range(1, len(data)):
        bg = ROW_ALT if i % 2 == 0 else colors.white
        style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))
    t.setStyle(TableStyle(style_cmds))
    return t


def write_pdf(path, docs_copy, story, header_footer, title):
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=0.7 * inch,
        bottomMargin=0.65 * inch,
        title=title,
        author="HRMS Product Team",
    )
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print("Wrote", path)
    try:
        shutil.copyfile(path, docs_copy)
        print("Copied", docs_copy)
    except PermissionError:
        print("Could not update", docs_copy, "- file may be open; close it and re-run")


def build_manager_pdf():
    styles = make_styles()

    def p(text, style="BodyDoc"):
        return Paragraph(text, styles[style])

    story = []
    story.append(Spacer(1, 1.2 * inch))
    story.append(HRFlowable(width="100%", thickness=2, color=NAVY, spaceAfter=16))
    story.append(p("HRMS", "CoverTitle"))
    story.append(p("Role-Based Access Control", "CoverTitle"))
    story.append(Spacer(1, 6))
    story.append(p("Operational Roles - Access Reference for Managers", "CoverSub"))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceBefore=12, spaceAfter=14))
    story.append(
        p(
            "Covers: Project Manager, Assistant Manager, Team Leader, QA, and Agent.<br/>"
            "Admin and Super Admin are documented in a separate privileged-access PDF.",
            "CoverSub",
        )
    )
    story.append(Spacer(1, 20))
    meta = [
        ["Document type", "Access control reference (operational roles)"],
        ["Audience", "Managers, supervisors, QA leads"],
        ["Companion doc", "Admin and Super Admin Access Control"],
        ["Date", "18 September 2026"],
        ["Classification", "Internal / Confidential"],
    ]
    mt = Table(
        [
            [Paragraph(f"<b>{a}</b>", styles["BodyDoc"]), Paragraph(b, styles["BodyDoc"])]
            for a, b in meta
        ],
        colWidths=[1.6 * inch, 3.6 * inch],
    )
    mt.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(mt)
    story.append(Spacer(1, 0.9 * inch))
    story.append(
        p(
            "Access is based on user role. Job designation is display-only and does not control permissions.",
            "FooterNote",
        )
    )
    story.append(PageBreak())

    story.append(p("1. Purpose", "H1Doc"))
    story.append(
        p(
            "This document explains what each operational HRMS role can see and do so managers can "
            "assign the correct role and understand team vs organization visibility.",
            "BodyDoc",
        )
    )
    story.append(
        p(
            "<b>Note:</b> Super Admin and Admin capabilities are listed in the separate "
            "<i>Admin and Super Admin Access Control</i> document - not in this PDF.",
            "NoteDoc",
        )
    )

    story.append(p("2. Access Levels", "H1Doc"))
    story.append(
        make_table(
            styles,
            ["Level", "Meaning"],
            [
                ["No access", "Feature is not available for this role"],
                ["View", "Can see data only (read-only)"],
                ["Edit", "Can create and update records"],
                ["Manage", "Full control (create, update, delete as applicable)"],
                [
                    "Approve",
                    "Admin / Super Admin only - see privileged access document",
                ],
            ],
            [1.3 * inch, 5.2 * inch],
        )
    )

    story.append(p("3. Roles and Data Visibility", "H1Doc"))
    story.append(
        make_table(
            styles,
            ["Role", "What data they can see"],
            [
                ["Project Manager", "Entire organization"],
                ["Assistant Manager", "Own team / assigned agents"],
                ["Assistant Team Leader", "Own team only (for QC: agents where they are set as the QA)"],
                ["QA", "Agents assigned to them (+ own data)"],
                ["Agent", "Own data only"],
            ],
            [1.8 * inch, 4.7 * inch],
        )
    )

    story.append(PageBreak())
    story.append(p("4. Feature Access Matrix", "H1Doc"))
    story.append(
        p("Dash (-) means no access. Roster approve/reject is Admin/Super Admin only.", "BodyDoc")
    )
    usable = PAGE_W - 2 * MARGIN
    cw = [usable * 0.34] + [usable * 0.66 / 5] * 5
    story.append(
        make_table(
            styles,
            ["Feature", "PM", "AM", "TL", "QA", "Agent"],
            [
                ["Analytics / Overview", "View", "View", "View", "View", "View"],
                ["Billable report", "View", "View", "View", "View", "Own"],
                ["QA hours report", "View", "View", "-", "-", "-"],
                ["User Monthly Goals", "Edit", "Edit*", "View", "-", "-"],
                ["Project Monthly Report", "View", "View", "View", "-", "-"],
                ["KRA", "View+", "Scoped", "Team", "Scoped", "Own"],
                ["Tracker Report", "View", "View", "View", "View", "-"],
                ["Agent Files & QC", "View", "View", "Edit (QA)", "View", "-"],
                ["QC Report Overview", "View", "View", "-", "-", "-"],
                ["QA Agent Audit", "View", "View", "-", "-", "-"],
                ["Audit Report (own)", "-", "-", "Own", "Own", "-"],
                ["My Report (QA hours)", "-", "-", "Own", "Own", "-"],
                ["Manage Users", "Manage", "-", "-", "-", "-"],
                ["Manage Projects", "Manage", "Manage", "-", "-", "-"],
                ["Roster Management", "Edit", "Edit*", "Edit*", "-", "-"],
                ["Roster Approve / Reject", "-", "-", "-", "-", "-"],
                ["My Roster", "-", "-", "-", "View", "View"],
                ["Projects (view only)", "-", "-", "View", "View", "Own"],
                ["Daily Tracker (Agent)", "-", "-", "-", "-", "Edit"],
                ["AI Evaluation", "-", "-", "-", "-", "Yes"],
                ["Salary details", "View", "-", "-", "-", "-"],
            ],
            cw,
        )
    )
    story.append(
        p(
            "Abbreviations: PM = Project Manager · AM = Assistant Manager · TL = Team Leader · "
            "View+ = View and Export · * = team-scoped",
            "NoteDoc",
        )
    )

    story.append(PageBreak())
    story.append(p("5. Role-by-Role Details", "H1Doc"))

    roles = [
        (
            "5.1 Project Manager",
            "Organization-wide visibility for most reports.",
            [
                "Can: view all analytics, tracker, QC, and KRA; edit User Monthly Goals; manage users and projects; edit and submit roster; view salary",
                "Cannot: approve or reject roster; lock roster weeks / holiday master; manage report emails",
            ],
            None,
        ),
        (
            "5.2 Assistant Manager",
            "Team / assignment scoped access.",
            [
                "Can: view analytics for assigned agents; edit User Monthly Goals for own team only; manage assigned projects; edit and submit team roster",
                "Cannot: manage users; approve roster; see organization-wide data outside assignment/team",
            ],
            "Team is locked in the UI for monthly goals and roster filters.",
        ),
        (
            "5.3 Assistant Team Leader (Team Leader)",
            "Mostly view-only, with two exceptions: edits and submits the team roster, and does QC like a QA.",
            [
                "Can: view team analytics, billable, monthly reports, KRA, and tracker report; edit and submit team roster; do QC like a QA (Agent Files and QC, QC form, rework, correction) on agents where set as the QA; add own QA hours in My Report; view Analytics > Audit Report (own audits)",
                "Cannot: edit User Monthly Goals hours; manage users or projects; approve roster; access QC Report Overview or the manager QA Agent Audit",
            ],
            "Outside roster and their own QC work, the system treats Team Leader as read-only.",
        ),
        (
            "5.4 QA",
            "Scoped to agents assigned to them.",
            [
                "Can: view analytics, billable and KRA for assigned agents, and the Audit Report for their own QC; maintain own QA hours; view own roster; view Tracker Report and Agent Files and QC; use QC form",
                "Cannot: manage users, projects, or roster administration",
            ],
            None,
        ),
        (
            "5.5 Agent",
            "Self-service role. Default landing page is the Agent Tracker.",
            [
                "Can: enter and edit own daily tracker; view own analytics, billable and QC, and KRA; view own roster; use AI Evaluation",
                "Cannot: see other agents' data; access Manage, roster management, or organization-level reports",
            ],
            None,
        ),
    ]
    for title, intro, bullets, note in roles:
        block = [p(title, "H2Doc"), p(intro, "BodyDoc")]
        for b in bullets or []:
            block.append(p(f"• {b}", "BulletDoc"))
        if note:
            block.append(p(f"Note: {note}", "NoteDoc"))
        story.append(KeepTogether(block))

    story.append(p("6. Important Business Rules", "H1Doc"))
    for i, r in enumerate(
        [
            "Roster approval is not available to roles in this document - only Admin / Super Admin.",
            "Project Manager can see org-wide data but cannot approve roster.",
            "Assistant Manager is locked to their team for monthly goals and roster filters.",
            "Team Leader is view-only except roster edit/submit and their own QC work (only where set as the QA).",
            "Agents and QA use My Roster (view only), not Roster Management.",
            "Creating a user with the wrong role immediately changes what they can see and do - choose carefully.",
        ],
        1,
    ):
        story.append(p(f"{i}. {r}", "BulletDoc"))

    story.append(p("7. Quick Decision Guide", "H1Doc"))
    story.append(
        make_table(
            styles,
            ["If you want someone to...", "Assign this role"],
            [
                [
                    "See all teams/reports, manage users/projects, but not approve roster",
                    "Project Manager",
                ],
                [
                    "Manage one team's goals, projects, and roster (no user management)",
                    "Assistant Manager",
                ],
                ["View team reports, update roster, and do QC where set as QA", "Assistant Team Leader"],
                ["Review QC / assigned agents and enter QA hours", "QA"],
                ["Enter daily work and view own reports only", "Agent"],
                [
                    "Full system control / roster approval",
                    "See Admin and Super Admin document",
                ],
            ],
            [3.8 * inch, 2.7 * inch],
        )
    )

    write_pdf(
        OUT_MGR,
        OUT_MGR_DOCS,
        story,
        header_footer_factory("HRMS  |  Role-Based Access Control", "Operational Roles"),
        "HRMS Role-Based Access Control",
    )


def build_admin_pdf():
    styles = make_styles()

    def p(text, style="BodyDoc"):
        return Paragraph(text, styles[style])

    story = []
    story.append(Spacer(1, 1.2 * inch))
    story.append(HRFlowable(width="100%", thickness=2, color=NAVY, spaceAfter=16))
    story.append(p("HRMS", "CoverTitle"))
    story.append(p("Admin & Super Admin", "CoverTitle"))
    story.append(p("Access Control", "CoverTitle"))
    story.append(Spacer(1, 6))
    story.append(p("Privileged Access Reference", "CoverSub"))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceBefore=12, spaceAfter=14))
    story.append(
        p(
            "This document covers Super Admin and Admin only.<br/>"
            "Operational roles are documented in a separate manager PDF.",
            "CoverSub",
        )
    )
    story.append(Spacer(1, 20))
    meta = [
        ["Document type", "Privileged access reference"],
        ["Audience", "System owners, HR leadership, IT / product"],
        ["Companion doc", "HRMS Role-Based Access Control (operational)"],
        ["Date", "18 September 2026"],
        ["Classification", "Internal / Confidential"],
    ]
    mt = Table(
        [
            [Paragraph(f"<b>{a}</b>", styles["BodyDoc"]), Paragraph(b, styles["BodyDoc"])]
            for a, b in meta
        ],
        colWidths=[1.6 * inch, 3.6 * inch],
    )
    mt.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(mt)
    story.append(PageBreak())

    story.append(p("1. Purpose", "H1Doc"))
    story.append(
        p(
            "This document describes the highest privilege roles in HRMS: what Super Admin and Admin "
            "can see and do, how they differ, and which actions only these roles can perform.",
            "BodyDoc",
        )
    )

    story.append(p("2. Roles Covered", "H1Doc"))
    story.append(
        make_table(
            styles,
            ["Role", "Data visibility", "Privilege summary"],
            [
                [
                    "Super Admin",
                    "Entire organization",
                    "Highest access - full control including report emails",
                ],
                [
                    "Admin",
                    "Entire organization",
                    "Same day-to-day power as Super Admin, except report emails",
                ],
            ],
            [1.4 * inch, 1.6 * inch, 3.5 * inch],
        )
    )

    story.append(p("3. Feature Access Comparison", "H1Doc"))
    usable = PAGE_W - 2 * MARGIN
    story.append(
        make_table(
            styles,
            ["Feature", "Super Admin", "Admin"],
            [
                ["Analytics / Overview", "View", "View"],
                ["Billable / QA hours / Tracker / QC / KRA", "View (+ Export for KRA)", "View (+ Export for KRA)"],
                ["User Monthly Goals", "Edit", "Edit"],
                ["Manage Users", "Manage", "Manage"],
                ["Manage Projects / AFD / Category / Permissions", "Manage", "Manage"],
                ["Roster generate / edit / submit", "Manage", "Manage"],
                ["Roster approve / reject", "Approve", "Approve"],
                ["Roster week lock", "Manage", "Manage"],
                ["Holiday master", "Manage", "Manage"],
                ["Report emails", "Manage", "No access"],
                ["Salary details", "View", "View"],
                ["QC form / Entry screens", "Allowed", "Allowed"],
            ],
            [usable * 0.48, usable * 0.26, usable * 0.26],
        )
    )

    story.append(PageBreak())
    story.append(p("4. Super Admin - Detailed Capabilities", "H1Doc"))
    story.append(p("Highest access level in the system. Organization-wide scope (no team lock).", "BodyDoc"))
    for b in [
        "View all analytics, billable, QA hours, tracker, QC, and KRA for the entire organization",
        "Edit User Monthly Goals for any team / agent",
        "Create, edit, and delete users",
        "Fully manage projects, AFD, categories, and permissions",
        "Full roster control: generate, edit, submit, approve/reject, lock weeks, holiday master",
        "Manage report email settings",
        "View salary details",
    ]:
        story.append(p(f"• {b}", "BulletDoc"))

    story.append(p("5. Admin - Detailed Capabilities", "H1Doc"))
    story.append(
        p(
            "Same as Super Admin for day-to-day operations, with one difference: "
            "Admin cannot manage Report emails.",
            "BodyDoc",
        )
    )
    story.append(
        make_table(
            styles,
            ["Area", "Admin vs Super Admin"],
            [
                ["Report emails", "Admin cannot manage report emails"],
                ["Roster approve / reject / week lock / holidays", "Same as Super Admin"],
                ["Users / projects / org-wide reports / salary", "Same as Super Admin"],
            ],
            [2.4 * inch, 4.1 * inch],
        )
    )

    story.append(p("6. Privileged Actions (Admin / Super Admin Only)", "H1Doc"))
    story.append(
        p(
            "These actions are not available to Project Manager, Assistant Manager, Team Leader, QA, or Agent:",
            "BodyDoc",
        )
    )
    for i, r in enumerate(
        [
            "Approve or reject roster submissions",
            "Lock roster weeks",
            "Manage holiday master",
            "Manage report emails (Super Admin only)",
        ],
        1,
    ):
        story.append(p(f"{i}. {r}", "BulletDoc"))
    story.append(
        p(
            "Note: Project Manager may see org-wide data and edit roster requests, but cannot approve roster.",
            "NoteDoc",
        )
    )

    story.append(p("7. Important Rules", "H1Doc"))
    for i, r in enumerate(
        [
            "Assign Super Admin / Admin only to trusted system owners.",
            "Prefer Admin when report-email configuration is not required; use Super Admin when it is.",
            "Creating a user as Admin or Super Admin immediately grants organization-wide control.",
            "Roster approval must never be expected from PM / AM / Team Leader.",
        ],
        1,
    ):
        story.append(p(f"{i}. {r}", "BulletDoc"))

    story.append(p("8. Quick Decision Guide", "H1Doc"))
    story.append(
        make_table(
            styles,
            ["If you want someone to...", "Assign"],
            [
                ["Full system control including report emails", "Super Admin"],
                ["Full system control without report emails", "Admin"],
                [
                    "Org-wide reports + manage users/projects, but no roster approve",
                    "Project Manager (operational RBAC doc)",
                ],
                [
                    "Team-only goals / roster edit, no user management",
                    "Assistant Manager (operational RBAC doc)",
                ],
            ],
            [3.8 * inch, 2.7 * inch],
        )
    )

    write_pdf(
        OUT_ADM,
        OUT_ADM_DOCS,
        story,
        header_footer_factory("HRMS  |  Admin & Super Admin Access", "Privileged Access"),
        "HRMS Admin and Super Admin Access Control",
    )


if __name__ == "__main__":
    build_manager_pdf()
    build_admin_pdf()

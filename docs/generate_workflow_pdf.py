"""Generate full system role-based workflow PDF for managers."""
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
    Preformatted,
)
from reportlab.lib.colors import HexColor

OUT = r"c:\Users\UmmehabibaSiddiquie\Desktop\Hrms_live\output\pdf\HRMS_Role_Based_Workflow.pdf"
OUT_DOCS = r"c:\Users\UmmehabibaSiddiquie\Desktop\Hrms_live\docs\HRMS_Role_Based_Workflow.pdf"

NAVY = HexColor("#1B3A5F")
BLUE = HexColor("#2E5A88")
LIGHT = HexColor("#E8EEF5")
ROW_ALT = HexColor("#F5F8FB")
BORDER = HexColor("#C5D0DE")
MUTED = HexColor("#5A6A7A")
PAGE_W, PAGE_H = A4
MARGIN = 0.6 * inch


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, PAGE_H - 28, PAGE_W, 28, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(MARGIN, PAGE_H - 18, "HRMS  |  Role-Based Workflow")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 18, "Confidential - Internal Use")
    canvas.setStrokeColor(BORDER)
    canvas.line(MARGIN, 40, PAGE_W - MARGIN, 40)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(MARGIN, 28, "What each role can do and from where")
    canvas.drawRightString(PAGE_W - MARGIN, 28, f"Page {doc.page}")
    canvas.restoreState()


def styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name="CoverTitle", fontName="Helvetica-Bold", fontSize=20, textColor=NAVY, alignment=TA_CENTER, spaceAfter=6, leading=24))
    s.add(ParagraphStyle(name="CoverSub", fontName="Helvetica", fontSize=10, textColor=MUTED, alignment=TA_CENTER, spaceAfter=4, leading=13))
    s.add(ParagraphStyle(name="H1Doc", fontName="Helvetica-Bold", fontSize=12, textColor=NAVY, spaceBefore=12, spaceAfter=6, leading=15))
    s.add(ParagraphStyle(name="H2Doc", fontName="Helvetica-Bold", fontSize=10.5, textColor=BLUE, spaceBefore=9, spaceAfter=4, leading=13))
    s.add(ParagraphStyle(name="BodyDoc", fontName="Helvetica", fontSize=8.5, textColor=HexColor("#222222"), alignment=TA_JUSTIFY, spaceAfter=4, leading=11))
    s.add(ParagraphStyle(name="BulletDoc", fontName="Helvetica", fontSize=8.5, textColor=HexColor("#222222"), leftIndent=10, spaceAfter=2, leading=11))
    s.add(ParagraphStyle(name="Flow", fontName="Courier", fontSize=7.5, textColor=HexColor("#1a1a1a"), leading=10, backColor=LIGHT, leftIndent=4, rightIndent=4, spaceBefore=4, spaceAfter=6))
    s.add(ParagraphStyle(name="NoteDoc", fontName="Helvetica-Oblique", fontSize=8, textColor=MUTED, spaceBefore=3, spaceAfter=5, leading=10))
    s.add(ParagraphStyle(name="Cell", fontName="Helvetica", fontSize=7, textColor=HexColor("#222222"), leading=9, alignment=TA_CENTER))
    s.add(ParagraphStyle(name="CellLeft", fontName="Helvetica", fontSize=7, textColor=HexColor("#222222"), leading=9, alignment=TA_LEFT))
    s.add(ParagraphStyle(name="CellHead", fontName="Helvetica-Bold", fontSize=7, textColor=colors.white, leading=9, alignment=TA_CENTER))
    s.add(ParagraphStyle(name="CellHeadLeft", fontName="Helvetica-Bold", fontSize=7, textColor=colors.white, leading=9, alignment=TA_LEFT))
    s.add(ParagraphStyle(name="FooterNote", fontName="Helvetica", fontSize=8, textColor=MUTED, alignment=TA_CENTER, leading=10))
    return s


def tbl(st, headers, rows, widths):
    data = [[Paragraph(h, st["CellHeadLeft"] if i == 0 else st["CellHead"]) for i, h in enumerate(headers)]]
    for row in rows:
        data.append([Paragraph(str(c), st["CellLeft"] if i == 0 else st["Cell"]) for i, c in enumerate(row)])
    t = Table(data, colWidths=widths, repeatRows=1)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.35, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for i in range(1, len(data)):
        cmds.append(("BACKGROUND", (0, i), (-1, i), ROW_ALT if i % 2 == 0 else colors.white))
    t.setStyle(TableStyle(cmds))
    return t


def build():
    st = styles()

    def p(text, style="BodyDoc"):
        return Paragraph(text, st[style])

    def flow(text):
        # Escape for Paragraph; use Preformatted-like via Paragraph with <br/>
        lines = text.strip().split("\n")
        html = "<br/>".join(line.replace(" ", "&nbsp;") for line in lines)
        return Paragraph(html, st["Flow"])

    usable = PAGE_W - 2 * MARGIN
    story = []

    # Cover
    story.append(Spacer(1, 1.1 * inch))
    story.append(HRFlowable(width="100%", thickness=2, color=NAVY, spaceAfter=14))
    story.append(p("HRMS", "CoverTitle"))
    story.append(p("Full System Role-Based Workflow", "CoverTitle"))
    story.append(Spacer(1, 4))
    story.append(p("What each role can do — and from where", "CoverSub"))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceBefore=10, spaceAfter=12))
    story.append(
        p(
            "End-to-end workflows for Project Manager, Assistant Manager,<br/>"
            "Team Leader, QA, and Agent. Admin / Super Admin privileged steps<br/>"
            "are summarized here and detailed in a separate document.",
            "CoverSub",
        )
    )
    story.append(Spacer(1, 18))
    meta = [
        ["Document type", "System workflow reference"],
        ["Audience", "Managers, supervisors, QA leads"],
        ["Date", "18 September 2026"],
        ["Classification", "Internal / Confidential"],
    ]
    mt = Table(
        [[Paragraph(f"<b>{a}</b>", st["BodyDoc"]), Paragraph(b, st["BodyDoc"])] for a, b in meta],
        colWidths=[1.5 * inch, 3.5 * inch],
    )
    mt.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(mt)
    story.append(PageBreak())

    story.append(p("1. How to Read This Document", "H1Doc"))
    story.append(
        tbl(
            st,
            ["Term", "Meaning"],
            [
                ["From where", "Menu path in the app (Header → screen → action)"],
                ["What they can do", "View, Edit, Submit, Export, Manage"],
                ["Scope", "Self · Team · Assigned agents · Entire organization"],
            ],
            [1.5 * inch, 5.0 * inch],
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        tbl(
            st,
            ["Role", "Lands on after login", "Data they usually see"],
            [
                ["Project Manager", "Dashboard", "Entire organization"],
                ["Assistant Manager", "Dashboard", "Own team / assigned agents"],
                ["Assistant Team Leader", "Dashboard", "Own team only"],
                ["QA", "Dashboard", "Assigned agents (+ own)"],
                ["Agent", "Tracker screen", "Own data only"],
            ],
            [1.6 * inch, 1.7 * inch, 3.2 * inch],
        )
    )
    story.append(
        p(
            "Admin and Super Admin approve roster and manage locks/holidays — see the privileged access PDF for full detail.",
            "NoteDoc",
        )
    )

    story.append(p("2. End-to-End Business Workflows", "H1Doc"))

    story.append(p("2.1 Daily Work Tracking", "H2Doc"))
    story.append(
        flow(
            """Agent → Header → Tracker → Submit
        ↓
Managers / QA see it in:
  Tracker Report · Billable Report · Agent Files & QC (PM, QA, TL as QA)"""
        )
    )
    story.append(
        tbl(
            st,
            ["Role", "From where", "What they can do"],
            [
                ["Agent", "Header → Tracker", "Create / edit / submit own daily entries"],
                ["Project Manager", "Header → Tracker Report", "View / filter / export — all org"],
                ["Assistant Manager", "Header → Tracker Report", "View / filter / export — assigned / team"],
                ["Team Leader", "Header → Tracker Report", "View — team only"],
                ["QA", "Header → Tracker Report", "View — assigned agents"],
            ],
            [1.3 * inch, 2.0 * inch, 3.2 * inch],
        )
    )

    story.append(p("2.2 User Monthly Goals and Roster", "H2Doc"))
    story.append(
        flow(
            """Manage → Roster → Generate (PM / AM / Admin)
        ↓ creates monthly target + working days
Analytics → User Monthly Goal / Report
        ↓ PM / AM edit Extra Hours → Submit / Export
        ↓ Team Leader: view only"""
        )
    )
    story.append(
        tbl(
            st,
            ["Role", "From where", "What they can do", "Scope"],
            [
                ["Project Manager", "Analytics → User Monthly Report", "Edit Extra Hours, Submit, Export", "All org"],
                ["Assistant Manager", "Analytics → User Monthly Goal", "Edit Extra Hours, Submit, Export", "Own team only"],
                ["Team Leader", "Analytics → User Monthly Goal", "View only", "Team"],
                ["Agent / QA", "—", "No this screen", "—"],
            ],
            [1.2 * inch, 2.0 * inch, 2.2 * inch, 1.1 * inch],
        )
    )

    story.append(PageBreak())
    story.append(p("2.3 Roster Change → Approval", "H2Doc"))
    story.append(
        flow(
            """PM / AM / Team Leader
  Manage → Roster Management → Edit → Submit for approval
        ↓
Admin / Super Admin ONLY
  Approval Queue → Approve or Reject
        ↓
Agent / QA → My Roster (view only)"""
        )
    )
    story.append(
        tbl(
            st,
            ["Role", "From where", "What they can do"],
            [
                ["Project Manager", "Manage → Roster Management", "Edit, Generate, Submit — all org"],
                ["Assistant Manager", "Manage → Roster Management", "Edit, Generate, Submit — team locked"],
                ["Team Leader", "Manage → Roster Management", "Edit, Submit — team (only write area for TL)"],
                ["Agent / QA", "Header → My Roster", "View own roster only"],
                ["Admin / Super Admin", "Approval Queue", "Approve / Reject (privileged doc)"],
            ],
            [1.4 * inch, 2.2 * inch, 2.9 * inch],
        )
    )

    story.append(p("2.4 QC / Agent Files", "H2Doc"))
    story.append(
        flow(
            """PM / QA / TL (as QA) → Agent Files & QC Report → QC Form
        ↓
Also in: QC Report Overview (PM, AM) · QA Agent Audit (PM, AM)
        · Analytics → Audit Report (QA, TL: own audits)"""
        )
    )
    story.append(
        tbl(
            st,
            ["Role", "From where", "What they can do"],
            [
                ["Project Manager", "Agent Files · QC Overview · QA Audit", "View / export; open QC Form"],
                ["Assistant Manager", "QC Overview · QA Audit", "View / export (scoped)"],
                ["QA", "Agent Files · My Report", "QC on assigned agents; own QA hours"],
                ["Team Leader", "Agent Files · My Report · Analytics → Audit Report", "QC like a QA where set as the QA; own QA hours; own audits"],
                ["Agent", "—", "No Agent Files / QC Overview in normal nav"],
            ],
            [1.4 * inch, 2.4 * inch, 2.7 * inch],
        )
    )

    story.append(p("2.5 KRA", "H2Doc"))
    story.append(
        p(
            "Analytics → KRA → select month and agent → view scores → notes (managers/QA) → Export Excel.",
            "BodyDoc",
        )
    )
    story.append(
        tbl(
            st,
            ["Role", "KRA scope"],
            [
                ["Project Manager", "All agents"],
                ["Assistant Manager", "Assigned agents"],
                ["Team Leader", "Team"],
                ["QA", "Assigned agents"],
                ["Agent", "Self only"],
            ],
            [2.0 * inch, 4.5 * inch],
        )
    )

    story.append(PageBreak())
    story.append(p("3. Role Workflows — Screen by Screen", "H1Doc"))

    story.append(p("3.1 Project Manager", "H2Doc"))
    story.append(p("<b>Login → Dashboard</b> · Header: Analytics · Tracker Report · Agent Files &amp; QC · QC Overview · QA Audit · Manage", "BodyDoc"))
    story.append(
        tbl(
            st,
            ["From where", "What they can do", "Scope"],
            [
                ["Analytics tabs (Overview, Billable, QA, Goals, Project Monthly, KRA)", "View; Goals = Edit Extra Hours + Export; KRA = notes + Export", "All org"],
                ["Tracker Report / Agent Files / QC Overview / QA Audit", "View / export; QC Form", "All org"],
                ["Manage → Users / Projects / AFD / Category / Permissions", "Manage", "Org"],
                ["Manage → Roster Management", "Edit, Generate, Submit for approval", "All org"],
            ],
            [2.6 * inch, 2.6 * inch, 1.3 * inch],
        )
    )
    story.append(p("Cannot: Approve roster, lock weeks, holiday master, report emails.", "NoteDoc"))

    story.append(p("3.2 Assistant Manager", "H2Doc"))
    story.append(p("<b>Login → Dashboard</b> · Header: Analytics · Tracker Report · QC Overview · QA Audit · Manage", "BodyDoc"))
    story.append(
        tbl(
            st,
            ["From where", "What they can do", "Scope"],
            [
                ["Analytics → User Monthly Goal", "Edit Extra Hours, Submit, Export", "Own team only"],
                ["Other Analytics / Tracker / QC / KRA", "View / export", "Assigned / team"],
                ["Manage → Projects / AFD / Category / Permissions", "Manage", "Own / assigned"],
                ["Manage → Roster Management", "Edit, Generate, Submit", "Team locked"],
                ["Manage → User Management", "Not available", "—"],
            ],
            [2.6 * inch, 2.6 * inch, 1.3 * inch],
        )
    )

    story.append(p("3.3 Assistant Team Leader", "H2Doc"))
    story.append(p("<b>Login → Dashboard</b> · Header: Analytics · My Report · Tracker Report · Agent Files &amp; QC · Manage · Mostly view-only except roster and own QC work.", "BodyDoc"))
    story.append(
        tbl(
            st,
            ["From where", "What they can do", "Scope"],
            [
                ["Analytics (all tabs including Goals / KRA)", "View only", "Team"],
                ["Tracker Report", "View", "Team"],
                ["Agent Files & QC Report", "QC Form, rework, correction", "Agents where set as the QA"],
                ["My Report", "Enter own QA hours", "Self"],
                ["Analytics → Audit Report", "View audits on own QC", "Self"],
                ["Manage → Roster Management", "Edit + Submit for approval", "Team"],
                ["Manage → Users / Projects / other tabs", "Hidden", "—"],
            ],
            [2.6 * inch, 2.6 * inch, 1.3 * inch],
        )
    )

    story.append(p("3.4 QA", "H2Doc"))
    story.append(p("<b>Login → Dashboard</b> · Header: Analytics · My Report · My Roster · Tracker Report · Agent Files &amp; QC", "BodyDoc"))
    story.append(
        tbl(
            st,
            ["From where", "What they can do", "Scope"],
            [
                ["Analytics → Overview / Billable / KRA", "View (KRA notes/export)", "Assigned"],
                ["Analytics → Audit Report", "View audits on own QC", "Self"],
                ["My Report", "Enter / edit own QA hours", "Self"],
                ["My Roster", "View", "Self"],
                ["Tracker Report / Agent Files & QC", "View; QC Form", "Assigned"],
            ],
            [2.6 * inch, 2.6 * inch, 1.3 * inch],
        )
    )

    story.append(p("3.5 Agent", "H2Doc"))
    story.append(p("<b>Login → Tracker</b> · Header: Analytics · My Roster · Tracker · AI Evaluation", "BodyDoc"))
    story.append(
        tbl(
            st,
            ["From where", "What they can do", "Scope"],
            [
                ["Tracker", "Create / edit / submit daily work", "Self"],
                ["Analytics → Overview / Billable & QC / KRA", "View", "Self"],
                ["My Roster", "View only", "Self"],
                ["AI Evaluation", "Run evaluation", "Self"],
            ],
            [2.6 * inch, 2.6 * inch, 1.3 * inch],
        )
    )

    story.append(PageBreak())
    story.append(p("4. Navigation Map (Header Items)", "H1Doc"))
    story.append(
        tbl(
            st,
            ["Header item", "PM", "AM", "TL", "QA", "Agent"],
            [
                ["Analytics", "Yes", "Yes", "Yes", "Yes", "Yes"],
                ["Tracker Report", "Yes", "Yes", "Yes", "Yes", "-"],
                ["Agent Files & QC Report", "Yes", "-", "Yes", "Yes", "-"],
                ["QC Report Overview", "Yes", "Yes", "-", "-", "-"],
                ["QA Agent Audit", "Yes", "Yes", "-", "-", "-"],
                ["Manage", "Yes", "Yes", "Roster", "-", "-"],
                ["My Report", "-", "-", "Yes", "Yes", "-"],
                ["My Roster", "-", "-", "-", "Yes", "Yes"],
                ["Tracker", "-", "-", "-", "-", "Yes"],
                ["AI Evaluation", "-", "-", "-", "-", "Yes"],
            ],
            [usable * 0.34] + [usable * 0.132] * 5,
        )
    )

    story.append(p("5. Who Starts vs Who Finishes", "H1Doc"))
    story.append(
        tbl(
            st,
            ["Process", "Started by", "Finished / approved by"],
            [
                ["Daily tracker entry", "Agent", "Visible in manager reports"],
                ["Monthly goals Extra Hours", "PM / AM (TL view only)", "Saved on Goals screen"],
                ["Roster generate", "PM / AM / Admin", "Creates goal baseline"],
                ["Roster day change", "PM / AM / Team Leader", "Admin / Super Admin approve"],
                ["QC scoring", "QA / TL (as QA) / PM via QC Form", "QC Overview / Audit"],
                ["KRA export", "Any role with KRA tab", "Same screen download"],
            ],
            [2.0 * inch, 2.3 * inch, 2.2 * inch],
        )
    )

    story.append(p("6. Quick “Where Do I Go?” Guide", "H1Doc"))
    story.append(
        tbl(
            st,
            ["I need to…", "Go here", "Role"],
            [
                ["Enter today’s work", "Header → Tracker", "Agent"],
                ["See team hours", "Analytics → Billable Report", "PM / AM / TL / QA"],
                ["Set Extra Assign Hours", "Analytics → User Monthly Goal/Report", "PM / AM"],
                ["Change roster days", "Manage → Roster Management", "PM / AM / TL"],
                ["Approve roster", "Manage → Approval Queue", "Admin / Super Admin"],
                ["Score QC on a file", "Agent Files → QC Form", "PM / QA / TL"],
                ["Enter my QA hours", "Header → My Report", "QA / TL"],
                ["Download KRA Excel", "Analytics → KRA → Export", "Scoped by role"],
                ["See my shift plan", "Header → My Roster", "Agent / QA"],
            ],
            [2.2 * inch, 2.8 * inch, 1.5 * inch],
        )
    )

    story.append(Spacer(1, 10))
    story.append(p("7. Related Documents", "H1Doc"))
    story.append(
        tbl(
            st,
            ["Document", "Use for"],
            [
                ["HRMS Role-Based Access Control", "Feature access matrix (View / Edit / Manage)"],
                ["Admin & Super Admin Access Control", "Privileged actions and Admin vs Super Admin"],
                ["This document", "Full workflow — what + from where"],
            ],
            [2.8 * inch, 3.7 * inch],
        )
    )

    doc = SimpleDocTemplate(
        OUT,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=0.7 * inch,
        bottomMargin=0.6 * inch,
        title="HRMS Full System Role-Based Workflow",
        author="HRMS Product Team",
    )
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print("Wrote", OUT)
    try:
        shutil.copyfile(OUT, OUT_DOCS)
        print("Copied", OUT_DOCS)
    except PermissionError:
        alt = OUT_DOCS.replace(".pdf", "_updated.pdf")
        shutil.copyfile(OUT, alt)
        print("Copied", alt, "(docs file locked)")


if __name__ == "__main__":
    build()

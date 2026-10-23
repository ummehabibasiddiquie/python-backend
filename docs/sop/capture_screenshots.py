"""
Capture HRMS screenshots for the module SOPs.

Runs against the local HRMS (frontend :5173, Flask :5000, Node :8000) and only opens
pages and forms. It never clicks Save / Submit / Delete.

The browser clock is fixed to SOP_DATE so date filters open on a period that has data.

Test logins (one per role, local copy only) are read from test_logins.local.json next to this
file, which is not in git: {"password": "...", "users": {"super_admin": "email", "admin": ..., ...}}.

Usage (from backend-api):
    python docs/sop/capture_screenshots.py                  # all shots
    python docs/sop/capture_screenshots.py agent qa         # only these roles
    python docs/sop/capture_screenshots.py qa_05_qc_form    # only this shot
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

BASE = "http://localhost:5173"
SOP_DATE = "2026-10-13T12:00:00+05:30"
VIEWPORT = {"width": 1440, "height": 900}
OUT = Path(__file__).parent / "screenshots"
LOGINS_FILE = Path(__file__).parent / "test_logins.local.json"


def load_logins() -> tuple[str, dict[str, str]]:
    if not LOGINS_FILE.exists():
        sys.exit(f"Missing {LOGINS_FILE.name}: create it with the local test logins (see the docstring).")
    data = json.loads(LOGINS_FILE.read_text(encoding="utf-8"))
    return data["password"], data["users"]


PASSWORD, USERS = load_logins()

# react-hot-toast renders a fixed wrapper (inset 16px, z-index 9999). Dropdown menus also
# use z-index 9999, so match the inset too or the menus disappear from screenshots.
HIDE_TOASTS = (
    'div[role="status"]{display:none !important}'
    'div[style*="z-index: 9999"][style*="inset: 16px"]{display:none !important}'
)


def d(tab: str, **extra) -> str:
    query = "&".join([f"tab={tab}"] + [f"{k}={v}" for k, v in extra.items()])
    return f"/dashboard?{query}"


# ---------- actions (open forms only; never save) ----------

def open_add_tracker(page: Page):
    page.get_by_role("button", name="Add Tracker").first.click()
    page.wait_for_timeout(1500)


def open_first_project_edit(page: Page):
    page.locator("text=/^Edit$/").first.click()
    page.wait_for_timeout(2500)


def open_first_qc_form(page: Page):
    page.get_by_role("button", name="QC Form").first.click()
    page.wait_for_url("**/qc-form**", timeout=45000)
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(2500)


def open_first_roster_cell(page: Page):
    # Weeks 1-3 of the local data are locked; Week 4 is still editable.
    page.get_by_role("button", name="Week 4", exact=True).click()
    page.wait_for_timeout(1500)
    page.locator("text=/^Working$/").first.click()
    page.get_by_text("Edit Roster Day").wait_for(timeout=10000)
    page.wait_for_timeout(1000)


def show_approved_requests(page: Page):
    page.get_by_role("button", name="Approved", exact=True).click()
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(1500)


# Roster detail shots. These only open dialogs or change a form value on screen;
# the next page.goto() closes them, so Confirm / Save are never clicked.

def open_week(page: Page, number: int):
    # Locked week tabs read "Week 3 · Locked", so match the start of the label.
    page.get_by_role("button", name=re.compile(rf"^Week {number}( ·|$)")).first.click()
    page.wait_for_timeout(1500)


def week4_tab(page: Page):
    open_week(page, 4)


def lock_week4_dialog(page: Page):
    open_week(page, 4)
    page.get_by_role("button", name="Lock Week 4").click()
    page.get_by_text("Lock Week 4", exact=True).last.wait_for(timeout=10000)
    page.wait_for_timeout(500)


def email_week3_dialog(page: Page):
    open_week(page, 3)
    page.get_by_role("button", name="Send email · Week 3").click()
    page.get_by_text("Send Week 3 roster email").wait_for(timeout=10000)
    page.wait_for_timeout(500)


def unlock_week3_dialog(page: Page):
    open_week(page, 3)
    page.get_by_role("button", name="Unlock Week 3").click()
    page.get_by_text("Unlock Week 3", exact=True).last.wait_for(timeout=10000)
    page.wait_for_timeout(500)


def reset_all_dialog(page: Page):
    page.get_by_role("button", name="Reset All").click()
    page.get_by_text("Reset & Regeneraate (All)").wait_for(timeout=10000)
    page.wait_for_timeout(500)


def day_editor_as(day_type_label: str):
    def action(page: Page):
        open_first_roster_cell(page)
        page.get_by_label("Day Type").select_option(label=day_type_label)
        page.wait_for_timeout(800)
    return action


def open_excel_upload(page: Page):
    page.get_by_role("button", name="Excel Upload").click()
    page.get_by_text("Weekly Roster Excel").wait_for(timeout=15000)
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(1000)


def open_add_holiday(page: Page):
    page.get_by_role("button", name="Add Holiday").click()
    page.get_by_placeholder("e.g. Republic Day").wait_for(timeout=10000)
    page.wait_for_timeout(500)


# ---------- QC workflow (QA and agent). Forms are filled on screen only, never submitted. ----------

def card_with(page: Page, text: str):
    """The nearest rounded card that contains this text."""
    return page.locator("div.rounded-2xl, div.rounded-xl", has=page.get_by_text(text, exact=True)).last


def qc_urgent_panel(page: Page):
    panel = card_with(page, "Urgent Files — do these first")
    panel.scroll_into_view_if_needed()
    return panel


def qc_select_first_task(page: Page):
    sidebar_heading = page.get_by_text("Projects / Tasks", exact=True).first
    sidebar_heading.scroll_into_view_if_needed()
    page.locator("div.w-\\[22rem\\] button").first.click()
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(1500)
    return page.locator("div.rounded-2xl", has=page.get_by_text("Projects / Tasks", exact=True)).first


def qc_add_record_open(page: Page):
    open_first_qc_form(page)
    box = card_with(page, "Add a record from the file")
    box.scroll_into_view_if_needed()
    box.get_by_role("button").first.click()
    page.wait_for_timeout(1200)
    return None


def _open_menu(page: Page):
    """The dropdown menu that is open right now (it holds a Search... box)."""
    return page.locator("div", has=page.get_by_placeholder("Search...")).last


def _mark_first_error(page: Page):
    page.get_by_text("Select Category").first.scroll_into_view_if_needed()
    page.mouse.wheel(0, 250)
    page.get_by_text("Select Category").first.click()
    page.wait_for_timeout(800)
    page.locator("button:visible").filter(has_text="Formatting").first.click()
    page.wait_for_timeout(800)
    page.mouse.wheel(0, 350)
    page.wait_for_timeout(500)
    page.locator("button", has_text="Select Errors").first.click()
    page.wait_for_timeout(1000)


def qc_category_and_errors_open(page: Page):
    open_first_qc_form(page)
    _mark_first_error(page)
    return None


def qc_error_added(page: Page):
    open_first_qc_form(page)
    _mark_first_error(page)
    page.locator("text=/pts\\)$/").locator("visible=true").first.click()
    page.wait_for_timeout(500)
    page.keyboard.press("Escape")
    page.mouse.click(5, 300)
    page.wait_for_timeout(300)
    page.get_by_role("button", name="Add (1) Error").first.click()
    page.wait_for_timeout(1200)
    page.locator("table").first.scroll_into_view_if_needed()
    return page.locator("table").first


def qc_summary_and_buttons(page: Page):
    qc_error_added(page)
    info = card_with(page, "Quality Assurance Information")
    info.scroll_into_view_if_needed()
    page.mouse.wheel(0, 400)
    page.wait_for_timeout(800)
    return None


def qc_confirm_modal(page: Page):
    qc_error_added(page)
    for name in ("Correction", "Rework Submit", "Regular Submit"):
        btn = page.get_by_role("button", name=name, exact=True)
        if btn.count() and btn.first.is_enabled():
            btn.first.click()
            break
    page.get_by_text("Confirm QC Submission").wait_for(timeout=10000)
    page.wait_for_timeout(800)
    return None


def qc_confirm_comments(page: Page):
    qc_confirm_modal(page)
    page.get_by_placeholder("Example: QC Code 6417 — Formatting - Junk Character").scroll_into_view_if_needed()
    page.wait_for_timeout(600)
    return None


def qc_previous_errors(page: Page):
    qc_select_first_task(page)
    page.get_by_role("button", name="View").first.click()
    page.wait_for_timeout(1500)
    return None


def qc_my_report_expanded(page: Page):
    page.locator("table tbody tr button").first.click()
    page.wait_for_timeout(1500)
    return None


def agent_qc_report(page: Page):
    page.get_by_text("QC Report", exact=True).last.click()
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(2000)
    return None


def agent_qc_expand_open_cycle(page: Page):
    """Expand the first file whose QC Status is still Correction or Rework (waiting for the agent)."""
    agent_qc_report(page)
    rows = page.locator("table > tbody > tr")
    for i in range(rows.count()):
        cells = rows.nth(i).locator("> td")
        if cells.count() < 8:
            continue
        qc_status = cells.nth(5).inner_text()
        if "Correction" in qc_status or "Rework" in qc_status:
            cells.nth(7).locator("button").click()
            page.wait_for_timeout(1500)
            break
    page.get_by_role("button", name="Upload").first.scroll_into_view_if_needed()
    page.mouse.wheel(0, 150)
    page.wait_for_timeout(500)
    return None


def agent_qc_upload_modal(page: Page):
    agent_qc_expand_open_cycle(page)
    page.get_by_role("button", name="Upload").first.click()
    page.wait_for_timeout(1000)
    return None


# ---------- Agent tracker detail (form filled on screen only, never submitted) ----------

def _pick_in_select(page: Page, trigger_text: str, option_index: int = 1):
    page.get_by_text(trigger_text, exact=True).first.click()
    page.wait_for_timeout(800)
    options = page.locator("button:visible", has=page.locator("span"))
    menu_opts = page.locator("div:has(> input[placeholder='Search...']) ~ div button:visible")
    target = menu_opts if menu_opts.count() else options
    target.nth(option_index).click()
    page.wait_for_timeout(1000)


def agent_add_tracker_filled(page: Page):
    open_add_tracker(page)
    modal = page.locator("form").first
    selects = modal.locator("button:has-text('Select ...')")
    selects.first.click()
    page.wait_for_timeout(800)
    page.locator("button:visible").filter(has_text="Creator Research").first.click()
    page.wait_for_timeout(1200)
    modal.locator("button:has-text('Select ...')").first.click()
    page.wait_for_timeout(800)
    page.locator("button:visible").filter(has_text="CRI100").first.click()
    page.wait_for_timeout(1000)
    page.get_by_placeholder("Enter production").fill("12")
    page.wait_for_timeout(800)
    return None


def agent_delete_confirm(page: Page):
    page.get_by_role("button", name="Delete Tracker").first.click()
    page.get_by_text("Are you sure you want to delete this tracker entry?").wait_for(timeout=10000)
    page.wait_for_timeout(500)
    return None


def agent_summary_totals(page: Page):
    card = card_with(page, "Summary Totals")
    card.scroll_into_view_if_needed()
    return card


def agent_monthly_report(page: Page):
    page.get_by_text("Monthly Report", exact=True).first.click()
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(1500)
    return None


# ---------- Projects & tasks detail (forms opened only, never saved) ----------

def select_project(page: Page, name: str = "Altrum"):
    page.get_by_text(name, exact=True).first.click()
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(1500)


def proj_add_project(page: Page):
    page.get_by_role("button", name="Add Project").click()
    page.wait_for_timeout(1500)
    return None


def proj_altrum(page: Page):
    select_project(page)
    return None


def proj_files_dropdown(page: Page):
    select_project(page)
    page.get_by_role("button", name="Files").first.click()
    page.wait_for_timeout(1500)
    return None


def _scroll_modal_to_bottom(page: Page):
    page.mouse.move(720, 500)
    for _ in range(8):
        page.mouse.wheel(0, 600)
        page.wait_for_timeout(200)
    page.wait_for_timeout(600)


def proj_add_task(page: Page):
    select_project(page)
    page.get_by_role("button", name="Add Task").first.click()
    page.wait_for_timeout(1500)
    return None


def proj_add_task_bottom(page: Page):
    proj_add_task(page)
    _scroll_modal_to_bottom(page)
    return None


def proj_edit_task(page: Page):
    select_project(page)
    page.get_by_title("Edit Task").first.click()
    page.get_by_text("Edit Task").first.wait_for(timeout=10000)
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(2500)
    return None


def proj_edit_task_bottom(page: Page):
    proj_edit_task(page)
    _scroll_modal_to_bottom(page)
    return None


# ---------- Manager reports detail (opened only, never saved) ----------

def tr_edit_tracker(page: Page):
    page.get_by_title("Edit tracker").first.click()
    page.get_by_text("Edit Tracker", exact=True).wait_for(timeout=10000)
    page.wait_for_timeout(1500)
    return None


def tr_add_for_agent(page: Page):
    page.get_by_title("Add new tracker entry").click()
    page.wait_for_timeout(1500)
    return None


def eod_task_list(page: Page):
    page.get_by_text("Task List", exact=True).wait_for(timeout=30000)
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(1000)
    return None


def eod_tracker_list(page: Page):
    eod_task_list(page)
    page.locator("table tbody tr td:nth-child(4) button").first.click()
    page.get_by_text("Tracker List", exact=True).wait_for(timeout=30000)
    page.get_by_text(re.compile(r"^Total: \d+")).wait_for(timeout=90000)
    page.wait_for_timeout(800)
    return None


def eod_tracker_list_excluded(page: Page):
    eod_tracker_list(page)
    page.get_by_role("button", name=re.compile(r"^Excluded \(")).click()
    page.wait_for_timeout(800)
    return None


def page_bottom(page: Page):
    page.mouse.move(720, 500)
    for _ in range(10):
        page.mouse.wheel(0, 600)
        page.wait_for_timeout(200)
    page.wait_for_timeout(800)
    return None


def umr_edit_row(page: Page):
    page.get_by_title("Edit monthly target and extra hours").first.click()
    page.wait_for_timeout(1000)
    return None


def billable_agent_panel(page: Page):
    page.locator("table tbody tr").first.click()
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(2000)
    return None


def qco_view_errors(page: Page):
    page.get_by_text("View", exact=True).first.click()
    page.wait_for_timeout(2000)
    return None


def qco_expand_history(page: Page):
    rows = page.locator("table > tbody > tr")
    for i in range(rows.count()):
        expander = rows.nth(i).locator("button:has(svg.lucide-chevron-down)")
        if expander.count():
            expander.first.click()
            break
    page.wait_for_timeout(1500)
    page.get_by_text("Rework & Correction History").first.scroll_into_view_if_needed()
    return None


def audit_expand_first(page: Page):
    page.locator("button:has(svg.lucide-chevron-down)").first.click()
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(2000)
    return None


def audit_open_form(page: Page):
    audit_expand_first(page)
    page.locator("table tbody tr td:last-child button").first.click()
    page.get_by_placeholder("Enter QC Score (0-100)").wait_for(timeout=10000)
    page.wait_for_timeout(1000)
    return None


def billable_day_edit(page: Page):
    billable_agent_panel(page)
    page.locator("table tbody tr td:last-child button").first.click()
    page.get_by_placeholder("Enter hours (e.g., 8.5)").wait_for(timeout=10000)
    page.wait_for_timeout(800)
    return None


# ---------- Admin forms (opened only, never saved) ----------

def users_add(page: Page):
    page.get_by_role("button", name="Add User").click()
    page.wait_for_timeout(1500)
    return None


def users_add_bottom(page: Page):
    users_add(page)
    _scroll_modal_to_bottom(page)
    return None


def users_edit_first(page: Page):
    page.locator("table tbody tr td:last-child button").first.click()
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(2000)
    return None


def page_scroll_down(page: Page):
    page.mouse.move(720, 500)
    for _ in range(4):
        page.mouse.wheel(0, 500)
        page.wait_for_timeout(200)
    page.wait_for_timeout(800)
    return None


def sop_new_topic(page: Page):
    page.get_by_role("button", name="New topic").click()
    page.get_by_placeholder("Attendance, Leave, Quality…").wait_for(timeout=10000)
    page.wait_for_timeout(500)
    return None


def qa_add_reporting_tracker(page: Page):
    page.get_by_role("button", name="Add Tracker").first.click()
    page.wait_for_timeout(1500)
    return None


def open_first_approval_details(page: Page):
    show_approved_requests(page)
    page.get_by_role("button", name="Details").first.click()
    page.get_by_text("Request Details").wait_for(timeout=10000)
    page.wait_for_timeout(800)


# (role, file name, url, optional action)
SHOTS = [
    # ---- Agent ----
    ("agent", "agent_01_tracker", "/agent", None),
    ("agent", "agent_02_add_tracker", "/agent", open_add_tracker),
    ("agent", "agent_03_overview", d("overview"), None),
    ("agent", "agent_04_billable_qc_report", d("billable_report"), None),
    ("agent", "agent_05_kra", d("kra_report"), None),
    ("agent", "agent_06_my_roster", d("my_roster"), None),
    # ---- QA ----
    ("qa", "qa_01_overview", d("overview"), None),
    ("qa", "qa_02_agent_files", d("agent_file_report", subtab="agent_files"), None),
    ("qa", "qa_03_rework_correction_files", d("agent_file_report", subtab="rework_review"), None),
    ("qa", "qa_04_my_qc_report", d("agent_file_report", subtab="qc_report"), None),
    ("qa", "qa_05_qc_form", d("agent_file_report", subtab="agent_files"), open_first_qc_form),
    ("qa", "qa_06_my_report_hours", d("my_hours"), None),
    ("qa", "qa_07_tracker_report", d("tracker_report"), None),
    ("qa", "qa_08_agents_billable", d("billable_report"), None),
    ("qa", "qa_09_audit_report", d("audit_report"), None),
    ("qa", "qa_10_kra", d("kra_report"), None),
    ("qa", "qa_11_my_roster", d("my_roster"), None),
    ("qa", "qa_12_sops", d("sops"), None),
    # ---- Project Manager / Assistant Manager ----
    ("project_manager", "mgr_01_overview", d("overview"), None),
    ("project_manager", "mgr_02_projects", d("manage", adminTab="projects"), None),
    ("project_manager", "mgr_03_edit_project", d("manage", adminTab="projects"), open_first_project_edit),
    ("project_manager", "mgr_04_billable_daily", d("billable_report", subtab="daily"), None),
    ("project_manager", "mgr_05_billable_monthly", d("billable_report", subtab="monthly"), None),
    ("project_manager", "mgr_06_user_monthly_report", d("user_monthly_report"), None),
    ("project_manager", "mgr_07_project_monthly_report", d("project_monthly_report"), None),
    ("project_manager", "mgr_08_qa_report", d("qa_hours"), None),
    ("project_manager", "mgr_09_kra", d("kra_report"), None),
    ("project_manager", "mgr_10_tracker_report", d("tracker_report"), None),
    ("project_manager", "mgr_11_qc_report_overview", d("qc_report_overview"), None),
    ("project_manager", "mgr_12_qa_agent_audit_form", d("qa_agent_audit", subtab="audit_form"), None),
    ("project_manager", "mgr_13_qa_agent_audit_report", d("qa_agent_audit", subtab="audit_report"), None),
    ("project_manager", "mgr_14_roster_calendar", d("manage", adminTab="roster", subtab="team_week"), None),
    ("project_manager", "mgr_15_roster_day_edit", d("manage", adminTab="roster", subtab="team_week"), open_first_roster_cell),
    ("project_manager", "mgr_16_roster_submissions", d("manage", adminTab="roster", subtab="submissions"), None),
    ("project_manager", "mgr_17_roster_holidays", d("manage", adminTab="roster", subtab="holidays"), None),
    ("project_manager", "mgr_18_sops", d("sops"), None),
    ("assistant_manager", "am_01_overview", d("overview"), None),
    ("assistant_manager", "am_02_manage", d("manage"), None),
    ("assistant_team_leader", "atl_01_overview", d("overview"), None),
    ("assistant_team_leader", "atl_02_tracker_report", d("tracker_report"), None),
    ("assistant_team_leader", "atl_03_manage", d("manage"), None),
    # ---- Admin / Super Admin ----
    ("admin", "admin_01_overview", d("overview"), None),
    ("admin", "admin_02_users", d("manage", adminTab="users"), None),
    ("admin", "admin_03_projects", d("manage", adminTab="projects"), None),
    ("admin", "admin_04_afd", d("manage", adminTab="afd"), None),
    ("admin", "admin_05_category", d("manage", adminTab="category"), None),
    ("admin", "admin_06_roster_approval", d("manage", adminTab="roster", subtab="approval"), show_approved_requests),
    ("admin", "admin_07_roster_calendar", d("manage", adminTab="roster", subtab="team_week"), None),
    ("admin", "admin_08_qc_report_overview", d("qc_report_overview"), None),
    ("admin", "admin_09_sops_manage", d("manage", adminTab="sops"), None),
    ("super_admin", "sa_01_permissions", d("manage", adminTab="permissions"), None),
    ("super_admin", "sa_02_report_emails", d("report_emails"), None),
    # ---- Roster detail (manager and admin) ----
    ("project_manager", "roster_m01_week4_tab", d("manage", adminTab="roster", subtab="team_week"), week4_tab),
    ("project_manager", "roster_m02_day_leave", d("manage", adminTab="roster", subtab="team_week"), day_editor_as("Leave (Roster)")),
    ("project_manager", "roster_m03_day_left", d("manage", adminTab="roster", subtab="team_week"), day_editor_as("Left")),
    ("project_manager", "roster_m04_excel_upload", d("manage", adminTab="roster", subtab="team_week"), open_excel_upload),
    ("project_manager", "roster_m05_submissions_approved", d("manage", adminTab="roster", subtab="submissions"), show_approved_requests),
    ("admin", "roster_a01_week4_admin_buttons", d("manage", adminTab="roster", subtab="team_week"), week4_tab),
    ("admin", "roster_a02_lock_week_dialog", d("manage", adminTab="roster", subtab="team_week"), lock_week4_dialog),
    ("admin", "roster_a03_send_email_dialog", d("manage", adminTab="roster", subtab="team_week"), email_week3_dialog),
    ("admin", "roster_a04_unlock_week_dialog", d("manage", adminTab="roster", subtab="team_week"), unlock_week3_dialog),
    ("admin", "roster_a05_reset_all_dialog", d("manage", adminTab="roster", subtab="team_week"), reset_all_dialog),
    ("admin", "roster_a06_day_edit", d("manage", adminTab="roster", subtab="team_week"), open_first_roster_cell),
    ("admin", "roster_a07_approval_details", d("manage", adminTab="roster", subtab="approval"), open_first_approval_details),
    ("admin", "roster_a08_holiday_master", d("manage", adminTab="roster", subtab="holidays"), None),
    ("admin", "roster_a09_add_holiday", d("manage", adminTab="roster", subtab="holidays"), open_add_holiday),
    # ---- QC workflow detail ----
    ("qa", "qc_q01_urgent_panel", d("agent_file_report", subtab="agent_files"), qc_urgent_panel),
    ("qa", "qc_q02_task_files", d("agent_file_report", subtab="agent_files"), qc_select_first_task),
    ("qa", "qc_q03_add_record_list", d("agent_file_report", subtab="agent_files"), qc_add_record_open),
    ("qa", "qc_q04_category_errors", d("agent_file_report", subtab="agent_files"), qc_category_and_errors_open),
    ("qa", "qc_q05_error_added", d("agent_file_report", subtab="agent_files"), qc_error_added),
    ("qa", "qc_q06_summary_buttons", d("agent_file_report", subtab="agent_files"), qc_summary_and_buttons),
    ("qa", "qc_q07_confirm_modal", d("agent_file_report", subtab="agent_files"), qc_confirm_modal),
    ("qa", "qc_q07b_confirm_comments", d("agent_file_report", subtab="agent_files"), qc_confirm_comments),
    ("qa", "qc_q08_rework_pending", d("agent_file_report", subtab="rework_review"), qc_select_first_task,
     {"clock": "2026-09-28T12:00:00+05:30", "width": 1760}),
    ("qa", "qc_q09_correction_pending", d("agent_file_report", subtab="rework_review"), qc_select_first_task,
     {"clock": "2026-09-14T12:00:00+05:30", "width": 1760}),
    ("qa", "qc_q10_previous_errors", d("agent_file_report", subtab="rework_review"), qc_previous_errors,
     {"clock": "2026-09-28T12:00:00+05:30"}),
    ("qa", "qc_q11_my_qc_report_history", d("agent_file_report", subtab="qc_report"), qc_my_report_expanded),
    ("admin", "adm_u01_add_user", d("manage", adminTab="users"), users_add),
    ("admin", "adm_u02_add_user_bottom", d("manage", adminTab="users"), users_add_bottom),
    ("admin", "adm_u03_edit_user", d("manage", adminTab="users"), users_edit_first),
    ("admin", "adm_a01_afd_list", d("manage", adminTab="afd"), page_scroll_down),
    ("admin", "adm_s01_new_topic", d("manage", adminTab="sops"), sop_new_topic),
    ("qa", "qa_h01_add_reporting_tracker", d("my_hours"), qa_add_reporting_tracker),
    ("project_manager", "rep_01_tracker_edit", d("tracker_report"), tr_edit_tracker),
    ("project_manager", "rep_02_tracker_add_for_agent", d("tracker_report"), tr_add_for_agent),
    ("project_manager", "rep_03_user_monthly_edit", d("user_monthly_report"), umr_edit_row),
    ("project_manager", "rep_04_billable_agent_daily", d("billable_report", subtab="daily"), billable_agent_panel),
    ("project_manager", "rep_05_billable_agent_monthly", d("billable_report", subtab="monthly"), billable_agent_panel),
    ("project_manager", "rep_06_qco_view_errors", d("qc_report_overview"), qco_view_errors),
    ("project_manager", "rep_07_qco_history", d("qc_report_overview"), qco_expand_history),
    ("project_manager", "rep_08_audit_expanded", d("qa_agent_audit", subtab="audit_form"), audit_expand_first,
     {"width": 1760}),
    ("project_manager", "rep_09_audit_form", d("qa_agent_audit", subtab="audit_form"), audit_open_form),
    ("project_manager", "rep_10_billable_day_edit", d("billable_report", subtab="daily"), billable_day_edit),
    ("project_manager", "rep_11_overview_qc_files", d("overview"), page_bottom),
    ("project_manager", "rep_12_eod_task_list", d("tracker_report", subtab="task_eod_report"), eod_task_list),
    ("project_manager", "rep_13_eod_tracker_list", d("tracker_report", subtab="task_eod_report"), eod_tracker_list),
    ("project_manager", "rep_14_eod_excluded", d("tracker_report", subtab="task_eod_report"), eod_tracker_list_excluded),
    ("project_manager", "proj_01_add_project", d("manage", adminTab="projects"), proj_add_project),
    ("project_manager", "proj_02_project_tasks", d("manage", adminTab="projects"), proj_altrum),
    ("project_manager", "proj_03_files_dropdown", d("manage", adminTab="projects"), proj_files_dropdown),
    ("project_manager", "proj_04_add_task", d("manage", adminTab="projects"), proj_add_task),
    ("project_manager", "proj_05_add_task_bottom", d("manage", adminTab="projects"), proj_add_task_bottom),
    ("project_manager", "proj_06_edit_task", d("manage", adminTab="projects"), proj_edit_task),
    ("project_manager", "proj_07_edit_task_bottom", d("manage", adminTab="projects"), proj_edit_task_bottom),
    ("agent", "agent_t02_add_filled", "/agent", agent_add_tracker_filled),
    ("agent", "agent_t03_delete_confirm", "/agent", agent_delete_confirm),
    ("agent", "agent_t04_summary_totals", "/agent", agent_summary_totals),
    ("agent", "agent_r01_monthly_report", d("billable_report"), agent_monthly_report),
    ("agent", "qc_a01_agent_qc_report", d("billable_report"), agent_qc_report),
    ("agent", "qc_a02_agent_qc_history", d("billable_report"), agent_qc_expand_open_cycle),
    ("agent", "qc_a03_agent_upload_modal", d("billable_report"), agent_qc_upload_modal),
]


def login(page: Page, email: str) -> None:
    page.goto(f"{BASE}/login")
    page.fill('input[placeholder="Enter email"]', email)
    page.fill('input[placeholder="••••••••"]', PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_url(lambda url: "/login" not in url, timeout=30000)
    page.wait_for_load_state("networkidle", timeout=30000)


def dismiss_popups(page: Page) -> None:
    for name in ("Understood, I will improve", "Got it", "Close"):
        btn = page.get_by_role("button", name=name)
        try:
            if btn.count() and btn.first.is_visible():
                btn.first.click()
                page.wait_for_timeout(500)
        except Exception:
            pass


def capture(wanted: list[str]) -> None:
    """wanted: role names and/or screenshot names; empty means everything."""
    OUT.mkdir(parents=True, exist_ok=True)
    selected = [s for s in SHOTS if not wanted or s[0] in wanted or s[1] in wanted]
    roles = list(dict.fromkeys(s[0] for s in selected))
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for role in roles:
            shots = [s for s in selected if s[0] == role]
            if not shots:
                continue
            context = browser.new_context(viewport=VIEWPORT)
            context.clock.set_fixed_time(SOP_DATE)
            page = context.new_page()
            try:
                login(page, USERS[role])
            except Exception as exc:
                print(f"[{role}] login failed: {exc}")
                context.close()
                continue
            for shot in shots:
                _, name, url, action = shot[:4]
                options = shot[4] if len(shot) > 4 else {}
                try:
                    context.clock.set_fixed_time(options.get("clock", SOP_DATE))
                    page.set_viewport_size({
                        "width": options.get("width", VIEWPORT["width"]),
                        "height": VIEWPORT["height"],
                    })
                    page.goto(f"{BASE}{url}")
                    page.wait_for_load_state("networkidle", timeout=45000)
                    page.add_style_tag(content=HIDE_TOASTS)
                    page.wait_for_timeout(2000)
                    dismiss_popups(page)
                    target = None
                    if action:
                        target = action(page)
                        page.add_style_tag(content=HIDE_TOASTS)
                        page.wait_for_timeout(300)
                    if target is not None:
                        target.screenshot(path=str(OUT / f"{name}.png"))
                    else:
                        page.screenshot(path=str(OUT / f"{name}.png"))
                    (OUT / f"{name}__FAILED.png").unlink(missing_ok=True)
                    print(f"[{role}] ok   {name}", flush=True)
                except Exception as exc:
                    page.screenshot(path=str(OUT / f"{name}__FAILED.png"))
                    print(f"[{role}] FAIL {name}: {str(exc).splitlines()[0]}", flush=True)
            context.close()
        browser.close()


if __name__ == "__main__":
    capture(sys.argv[1:])

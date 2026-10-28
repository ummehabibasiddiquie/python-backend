"""
Generate handover_content_db.py (handover document 08 - Database Schema) from a live MySQL schema.

Usage (from backend-api):
    python docs/handover/build_db_schema.py        # reads the database in backend-api/.env
    python docs/handover/build_handover_docs.py    # then rebuild the Word documents
Only the structure is read (tables, columns, keys, indexes); no row data and no secrets.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from pprint import pformat

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))  # backend-api, for config.get_db_connection

from config import get_db_connection  # noqa: E402

AREAS = [
    ("People and access", ["tfs_user", "user_role", "user_designation", "team", "user_permission"]),
    ("Projects, tasks and QC error lists", ["project", "task", "project_category", "afd", "qc_afd"]),
    ("Production and hours", ["task_work_tracker", "tracker_records", "temp_qc", "user_monthly_tracker",
                              "project_monthly_tracker", "api_call_logs"]),
    ("QC", ["qc_records", "qc_correction_history", "qc_rework_history", "qc_audit", "qc_performance"]),
    ("QA hours", ["qa_work_tracker"]),
    ("Roster", ["roster_month", "roster_day", "roster_leave", "roster_change_request", "roster_version_snapshot",
                "roster_audit_log", "roster_week_lock", "org_holiday"]),
    ("KRA", ["kra_day_note", "kra_day_override", "kra_month_input"]),
    ("SOP library and report emails", ["sop_topic", "sop_item", "report_email_recipient"]),
]

TABLE_NOTES = {
    "tfs_user": "Every user. is_delete = 1 means the row is live (0 = deleted). Reporting lines are ID lists.",
    "user_role": "Roles 1-7: Super Admin, Admin, Project Manager, Assistant Manager, QA, Agent, Assistant Team Leader.",
    "user_designation": "Job titles shown in Add / Edit User.",
    "team": "Teams (A, B, Quality, Marketing). Billable reports use teams A and B.",
    "user_permission": "User Creation and Project Creation flags per user.",
    "project": "Projects. Team, QA and manager lists are JSON ID arrays.",
    "task": "Tasks of a project: target, QC %, important columns, QA target settings.",
    "project_category": "Category of a project; links a project to its AFD (QC error list).",
    "afd": "AFD masters (named QC error lists).",
    "qc_afd": "Categories, errors and points of each AFD.",
    "task_work_tracker": "One row per tracker entry (agent production). is_active = 0 means deleted.",
    "tracker_records": "Row hashes of tracker files, used for the duplicate check (written by Node QC).",
    "temp_qc": "One row per agent per day: assigned hours (08:00 job) and daily QC score.",
    "user_monthly_tracker": "Monthly goal per user (target, extra hours, working days, goal_locked).",
    "project_monthly_tracker": "Monthly target per project.",
    "api_call_logs": "Log of tracker add / delete calls.",
    "qc_records": "One QC per tracker: score, errors, result and files.",
    "qc_correction_history": "One row per correction cycle of a QC record.",
    "qc_rework_history": "One row per rework cycle of a QC record.",
    "qc_audit": "Manager audits of a QA's QC work.",
    "qc_performance": "Written only by the Node tracker process in JSON mode.",
    "qa_work_tracker": "QA hours per activity (QC, rework QC, feedback, reporting, manual entries).",
    "roster_month": "One roster per person per month with its approval status and version.",
    "roster_day": "One row per person per day of the roster (linked through roster_month_id).",
    "roster_leave": "Leaves (rostered or not, half day, affects target).",
    "roster_change_request": "Draft, pending, approved, rejected and cancelled roster changes.",
    "roster_version_snapshot": "JSON snapshot of each approved roster version.",
    "roster_audit_log": "History of every roster action.",
    "roster_week_lock": "Locked Monday-Sunday weeks.",
    "org_holiday": "Holiday master.",
    "kra_day_note": "KRA note per user per day.",
    "kra_day_override": "Not used by the current code.",
    "kra_month_input": "Not used by the current code.",
    "sop_topic": "SOP library topics (created by the code if missing).",
    "sop_item": "SOP library links and files.",
    "report_email_recipient": "Who receives each report email (To / CC and per-report flags).",
}

COLUMN_NOTES = {
    ("tfs_user", "user_password"): "Encrypted with ENCRYPTION_KEY (Flask .env).",
    ("tfs_user", "user_tenure"): "Text, e.g. 1, 0.75, 0.5. Scales targets and daily hours.",
    ("tfs_user", "project_manager_id"): "ID list like [12].",
    ("tfs_user", "asst_manager_id"): "ID list like [12].",
    ("tfs_user", "team_leader_id"): "ID list like [192].",
    ("tfs_user", "qa_id"): "ID list like [114].",
    ("tfs_user", "deactivated_at"): "Leaving day; tracker entries are allowed up to this day.",
    ("tfs_user", "is_delete"): "1 = live, 0 = deleted.",
    ("tfs_user", "joining_date"): "Tracker Joining Date (start of roster and tracker).",
    ("tfs_user", "gemini_api_key"): "Agent's own Gemini key, encrypted by Node QC.",
    ("project", "project_pprt"): "JSON array of Cloudinary file URLs.",
    ("project", "project_sop_links"): "JSON array of {title, url} (added by the code).",
    ("task", "task_target"): "Records per hour.",
    ("task", "task_team_id"): "JSON array of agent IDs who can use the task.",
    ("task", "important_columns"): "JSON array of column names: duplicate check and Task EOD merge.",
    ("task", "qc_percentage"): "QC sample percentage.",
    ("task_work_tracker", "tenure_target"): "task_target x tenure (tenure at least 1) at add time.",
    ("task_work_tracker", "billable_hours"): "production / tenure_target.",
    ("task_work_tracker", "qc_status"): "0 = not QC'd yet.",
    ("task_work_tracker", "tracker_file"): "Cloudinary URL of the agent's file.",
    ("qc_records", "status"): "regular / correction / rework.",
    ("qc_records", "error_list"): "JSON list of marked errors.",
    ("qc_records", "qc_file_path"): "Sample file URL.",
    ("qc_records", "whole_file_path"): "Agent's file that was checked.",
    ("roster_day", "day_type"): "Working, WeekOff, Holiday, Leave, PreJoin or Left.",
    ("roster_change_request", "batch_id"): "Empty while the change is a draft; set on Submit.",
}

LINKS = [
    ["tfs_user.role_id", "user_role.role_id", "Role of the user"],
    ["tfs_user.team_id", "team.team_id", "Team of the user"],
    ["tfs_user.designation_id", "user_designation.designation_id", "Job title"],
    ["tfs_user.qa_id / asst_manager_id / team_leader_id / project_manager_id", "tfs_user.user_id",
     "Reporting lines (ID lists, matched in code)"],
    ["user_permission.user_id", "tfs_user.user_id", "Permission flags"],
    ["project.project_category_id", "project_category.project_category_id", "Category of the project"],
    ["project_category.afd_id", "afd.afd_id", "QC error list used by the project"],
    ["task.project_id", "project.project_id", "Tasks of a project"],
    ["task_work_tracker.user_id / project_id / task_id", "tfs_user / project / task", "Who, which project and task"],
    ["temp_qc.user_id", "tfs_user.user_id", "Daily hours and QC of an agent"],
    ["qc_records.tracker_id", "task_work_tracker.tracker_id", "The tracker that was QC'd"],
    ["qc_records.agent_id / qa_user_id", "tfs_user.user_id", "Agent and QA of the QC"],
    ["qc_correction_history.qc_record_id", "qc_records.id", "Correction cycles (real foreign key)"],
    ["qc_rework_history.qc_record_id", "qc_records.id", "Rework cycles (real foreign key)"],
    ["qc_audit.qc_record_id", "qc_records.id", "Audit of a QC"],
    ["qa_work_tracker.qc_record_id", "qc_records.id", "QA hours earned for a QC"],
    ["roster_month.user_id", "tfs_user.user_id", "Roster of a person"],
    ["roster_day.roster_month_id", "roster_month.roster_month_id", "Days of a roster month"],
    ["roster_change_request.user_id", "tfs_user.user_id", "Requested roster changes"],
    ["sop_item.sop_topic_id", "sop_topic.sop_topic_id", "Items of an SOP topic"],
]


def fetch_schema(cursor):
    cursor.execute(
        "SELECT TABLE_NAME, TABLE_COMMENT FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME"
    )
    tables = [row[0] for row in cursor.fetchall()]
    cursor.execute(
        "SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_KEY, EXTRA "
        "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() ORDER BY TABLE_NAME, ORDINAL_POSITION"
    )
    columns: dict[str, list] = {}
    for table, name, ctype, nullable, default, key, extra in cursor.fetchall():
        columns.setdefault(table, []).append((name, ctype, nullable, default, key, extra))
    cursor.execute(
        "SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) "
        "FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND INDEX_NAME <> 'PRIMARY' "
        "GROUP BY TABLE_NAME, INDEX_NAME, NON_UNIQUE ORDER BY TABLE_NAME, INDEX_NAME"
    )
    indexes: dict[str, list] = {}
    for table, index, non_unique, cols in cursor.fetchall():
        indexes.setdefault(table, []).append(f"{'' if non_unique else 'UNIQUE '}{index} ({cols})")
    return tables, columns, indexes


def as_text(value) -> str:
    if isinstance(value, (bytes, bytearray)):
        return value.decode()
    return "" if value is None else str(value)


def column_rows(table: str, cols: list) -> list[list[str]]:
    rows = []
    for name, ctype, nullable, default, key, extra in cols:
        name, ctype, key, extra = as_text(name), as_text(ctype), as_text(key), as_text(extra)
        flags = []
        if key == "PRI":
            flags.append("PK")
        elif key == "UNI":
            flags.append("unique")
        elif key == "MUL":
            flags.append("index")
        if "auto_increment" in extra:
            flags.append("auto")
        default_text = as_text(default)
        rows.append([
            name,
            ctype,
            "yes" if as_text(nullable) == "YES" else "no",
            default_text[:30],
            ", ".join(flags),
            COLUMN_NOTES.get((table, name), ""),
        ])
    return rows


def build_spec(database: str, tables, columns, indexes) -> dict:
    blocks = [
        ("h", "1. About this document"),
        ("bullets", [
            f"Taken from the structure of database {database} on {date.today():%d %b %Y}. After a migration, "
            "update the affected tables in this document.",
            "Live database: mytfs on the VPS. Local copy: tfs_hrms. Tables added by the code on first use exist "
            "only after that code has run.",
            "Only two real foreign keys exist; every other link between tables is kept by the code (section 2).",
            "Soft delete: tfs_user and sop_* use is_delete (1 = live); most other tables use is_active (1 = active).",
        ]),
        ("h", "2. How the tables link"),
        ("table", ["From", "To", "Meaning"], LINKS),
        ("h", "3. Tables by area"),
    ]
    placed = set()
    number = 0
    areas = [(area, [t for t in names if t in columns]) for area, names in AREAS]
    others = [t for t in tables if not any(t in names for _, names in AREAS)]
    if others:
        areas.append(("Other", others))
    for area, names in areas:
        if not names:
            continue
        number += 1
        blocks.append(("h2", f"3.{number} {area}"))
        blocks.append(("table", ["Table", "Holds"], [[t, TABLE_NOTES.get(t, "")] for t in names]))
        placed.update(names)
    blocks.append(("h", "4. Columns of every table"))
    for table in tables:
        blocks.append(("h2", table))
        if TABLE_NOTES.get(table):
            blocks.append(("p", TABLE_NOTES[table]))
        blocks.append(("table", ["Column", "Type", "Null", "Default", "Key", "Meaning"],
                       column_rows(table, columns.get(table, []))))
        if indexes.get(table):
            blocks.append(("p", "Indexes: " + "; ".join(indexes[table])))
    return {
        "number": "08",
        "title": "Database Schema",
        "audience": "Developers",
        "blocks": blocks,
    }


def main() -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DATABASE()")
        database = cursor.fetchone()[0]
        tables, columns, indexes = fetch_schema(cursor)
    finally:
        cursor.close()
        conn.close()
    spec = build_spec(database, tables, columns, indexes)
    out = HERE / "handover_content_db.py"
    out.write_text(
        '"""Handover document 08: Database Schema. Generated by build_db_schema.py - do not edit by hand."""\n\n'
        f"DATABASE_SCHEMA = {pformat(spec, width=110, sort_dicts=False)}\n",
        encoding="utf-8",
    )
    print(f"wrote {out.name}: {len(tables)} tables from {database}")


if __name__ == "__main__":
    main()

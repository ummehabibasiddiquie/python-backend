# routes/qa_tracker.py
# Persist QA work hours in qa_work_tracker (not billable, no tenure).
from __future__ import annotations

import calendar
import json
import re
import uuid
from collections import defaultdict
from datetime import datetime, timedelta

from flask import Blueprint, request

from config import get_db_connection
from utils.response import api_response
from utils.roster_helpers import get_role_context
from utils.qc_sla import (
    QC_FORM_SLA_EFFECTIVE_FROM_SQL,
    is_qc_late,
    load_holidays_around,
    parse_dt,
    qc_deadline,
    sla_applies_to_submission,
    sla_hours_for_submission,
)
from utils.time_ist import IST, now_ist, now_str, today_str
from utils.qa_targets import (
    QA_NEW_TARGETS_EFFECTIVE_FROM,
    parse_qa_target_ranges,
    report_record_counts,
    resolve_qa_targets,
)
from utils.qa_column_counts import ensure_qc_object_count_column, fill_missing_range_counts

qa_tracker_bp = Blueprint("qa_tracker", __name__)

EXPECTED_HOURS = {
    "qc_tasks": 4.5,
    "feedback": 1.5,
    "rework_qc": 1.5,
    "reporting": 1.5,
}
EXPECTED_TOTAL = 9.0
MONTH_ABBR = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
MANUAL_ACTIVITIES = ("feedback", "reporting")
MANUAL_KINDS = ("feedback", "training", "reporting", "other")
MANUAL_KIND_TO_ACTIVITY = {
    "feedback": "feedback",
    "training": "feedback",
    "reporting": "reporting",
    "other": "reporting",
}
QC_ACTIVITIES = ("qc_tasks", "rework_qc")
QA_DELETE_WINDOW_HOURS = 24
QA_TRACKER_GO_LIVE = QA_NEW_TARGETS_EFFECTIVE_FROM.strftime("%Y-%m-%d")
# One-time: apply current task QA targets to already-saved rows on this date.
# Later target edits stay frozen on older rows.
QA_ONE_TIME_TARGET_REBUILD_DATE = QA_TRACKER_GO_LIVE
_TODAY_TARGET_REBUILD_DONE = False


def _clamp_tracker_start(start_date: str | None) -> str:
    start = _parse_date(start_date) or QA_TRACKER_GO_LIVE
    return start if start >= QA_TRACKER_GO_LIVE else QA_TRACKER_GO_LIVE


def _resolve_report_range(start_date: str | None, end_date: str | None) -> tuple[str, str] | None:
    """Return (start, end) on/after go-live, or None if the selected window is entirely before it."""
    start = _parse_date(start_date)
    end = _parse_date(end_date) or start
    if not start:
        start = end or today_str()[:10]
    if not end:
        end = start
    if end < start:
        start, end = end, start
    if end < QA_TRACKER_GO_LIVE:
        return None
    if start < QA_TRACKER_GO_LIVE:
        start = QA_TRACKER_GO_LIVE
    if start > end:
        return None
    return start, end


def _purge_pre_golive_rows(cursor) -> None:
    cursor.execute(
        "DELETE FROM qa_work_tracker WHERE work_date < %s",
        (QA_TRACKER_GO_LIVE,),
    )


def _active_tracker_where(start_date: str, end_date: str) -> tuple[str, list]:
    start_date = _clamp_tracker_start(start_date)
    end_date = _parse_date(end_date) or start_date
    where = """
        qwt.is_active=1
        AND qwt.work_date >= %s
        AND qwt.work_date BETWEEN %s AND %s
        AND NOT (qwt.source_table='manual' AND qwt.hours <= 0)
    """
    return where, [QA_TRACKER_GO_LIVE, start_date, end_date]


def _rebuild_today_hours_once(cursor, conn) -> None:
    """Apply current task QA targets to today's already-saved QC hours once.

    After this, later target edits only affect files saved after the change.
    """
    global _TODAY_TARGET_REBUILD_DONE
    if _TODAY_TARGET_REBUILD_DONE:
        return
    today = today_str()[:10]
    if today != QA_ONE_TIME_TARGET_REBUILD_DATE:
        _TODAY_TARGET_REBUILD_DONE = True
        return
    rebuild_september_qa_hours(cursor, today, today)
    conn.commit()
    _TODAY_TARGET_REBUILD_DONE = True


def _prepare_tracker_read(cursor, conn, manager, logged_in_user_id, requested, start_date, end_date) -> None:
    _purge_pre_golive_rows(cursor)
    _deactivate_zero_manual_rows(cursor)
    conn.commit()
    try:
        _rebuild_today_hours_once(cursor, conn)
    except Exception:
        conn.rollback()
        import traceback
        traceback.print_exc()
    sync_ids = _resolve_sync_user_ids(cursor, manager, logged_in_user_id, requested)
    if not sync_ids:
        return
    try:
        _sync_month_from_qc(cursor, sync_ids, start_date, end_date)
        conn.commit()
    except Exception:
        conn.rollback()
        import traceback
        traceback.print_exc()



def _month_bounds(month_year: str | None) -> tuple[str, str, str] | None:
    """Accept YYYY-MM or SEP2026. Returns (start_date, end_date, SEP2026)."""
    raw = str(month_year or "").strip().upper().replace(" ", "")
    if not raw:
        return None
    year = month = None
    m = re.match(r"^(\d{4})-(\d{2})$", raw)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
    else:
        m = re.match(r"^([A-Z]{3})(\d{4})$", raw)
        if m and m.group(1) in MONTH_ABBR:
            month = MONTH_ABBR.index(m.group(1)) + 1
            year = int(m.group(2))
    if not year or not month or month < 1 or month > 12:
        return None
    last = calendar.monthrange(year, month)[1]
    return (
        f"{year:04d}-{month:02d}-01",
        f"{year:04d}-{month:02d}-{last:02d}",
        f"{MONTH_ABBR[month - 1]}{year}",
    )


def _parse_date(value) -> str | None:
    raw = str(value or "").strip()[:10]
    if not raw:
        return None
    try:
        datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        return None
    return raw


def _date_str(value) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value or "")[:10]


def _fmt_dt(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    text = str(value).strip()
    if not text or text.lower() in ("none", "null", "nat"):
        return ""
    if text.startswith("0000-00-00"):
        return ""
    return text[:19] if len(text) >= 19 and text[4] == "-" else text


def _latest_qc_info(cursor, qa_user_id=None) -> dict:
    sql = "SELECT MAX(DATE(created_at)) AS d FROM qc_records WHERE qa_user_id IS NOT NULL"
    params: list = []
    if qa_user_id:
        sql += " AND qa_user_id=%s"
        params.append(int(qa_user_id))
    cursor.execute(sql, tuple(params))
    row = cursor.fetchone() or {}
    latest_date = _date_str(row.get("d")) if row.get("d") else None
    latest_yyyy_mm = latest_date[:7] if latest_date else None
    bounds = _month_bounds(latest_yyyy_mm) if latest_yyyy_mm else None
    return {
        "latest_work_date": latest_date,
        "latest_month_yyyy_mm": latest_yyyy_mm,
        "latest_month_year": bounds[2] if bounds else None,
    }


def _active_qa_user_ids(cursor) -> list[int]:
    cursor.execute(
        """
        SELECT u.user_id
        FROM tfs_user u
        JOIN user_role r ON r.role_id = u.role_id
        WHERE u.is_active=1 AND u.is_delete=1
          AND (LOWER(TRIM(r.role_name)) = 'qa' OR LOWER(TRIM(r.role_name)) LIKE '%qa%')
        """
    )
    return [int(r["user_id"]) for r in (cursor.fetchall() or []) if r.get("user_id")]


def _resolve_sync_user_ids(cursor, manager: bool, logged_in_user_id: int, requested) -> list[int]:
    if requested not in (None, "", 0, "0"):
        return [int(requested)]
    if not manager:
        return [int(logged_in_user_id)]
    return _active_qa_user_ids(cursor)


def _is_manager(role_name: str, role_id=None) -> bool:
    if _int(role_id) == 7:
        return False
    if _int(role_id) in (1, 2, 3, 4):
        return True
    r = (role_name or "").strip().lower()
    return r in ("admin", "super admin", "project manager", "assistant manager")


def _ctx_is_manager(ctx: dict) -> bool:
    return _is_manager(ctx.get("user_role_name") or "", ctx.get("user_role_id"))


def _ctx_can_view_as_manager(ctx: dict) -> bool:
    if _ctx_is_manager(ctx):
        return True
    if _int(ctx.get("user_role_id")) == 7:
        return True
    return (ctx.get("user_role_name") or "").strip().lower() in ("assistant team leader", "team leader")


def _is_qa_role(role_name: str, role_id=None) -> bool:
    if _int(role_id) == 5:
        return True
    r = (role_name or "").strip().lower()
    return r == "qa" or "qa" in r


def _user_is_qa(cursor, user_id: int) -> bool:
    ctx = get_role_context(cursor, int(user_id))
    return _is_qa_role(ctx.get("user_role_name") or "", ctx.get("user_role_id"))


def _float(value, default=0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value, default=0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _round4(value) -> float:
    return round(_float(value), 4)


def _as_ist_dt(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            return dt.replace(tzinfo=IST)
        return dt.astimezone(IST)
    text = _fmt_dt(value)
    if not text:
        return None
    try:
        dt = datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=IST)
    except ValueError:
        return None


def _within_delete_window(created_at) -> bool:
    dt = _as_ist_dt(created_at)
    if not dt:
        return False
    return (now_ist() - dt) <= timedelta(hours=QA_DELETE_WINDOW_HOURS)


def _manual_detail_text(sub_activity: str, agent_name: str, project_name: str, notes: str) -> str:
    if sub_activity in ("feedback", "training"):
        return agent_name or ""
    if sub_activity == "reporting":
        return project_name or ""
    if sub_activity == "other":
        return notes or ""
    return notes or ""


def _resolve_manual_kind(data: dict, existing: dict | None = None) -> str:
    existing = existing or {}
    for key in ("sub_activity", "activity_type"):
        raw = data.get(key)
        if raw is None or str(raw).strip() == "":
            continue
        kind = str(raw).strip().lower()
        if kind in MANUAL_KINDS:
            return kind
    existing_sub = str(existing.get("sub_activity") or "").strip().lower()
    if existing_sub in MANUAL_KINDS:
        return existing_sub
    existing_activity = str(existing.get("activity_type") or "").strip().lower()
    if existing_activity in MANUAL_KINDS:
        return existing_activity
    return ""


def _validate_manual_details(data: dict, existing: dict | None = None):
    existing = existing or {}
    kind = _resolve_manual_kind(data, existing)
    if kind not in MANUAL_KINDS:
        return None, api_response(400, "Select Feedback, Training, Reporting, or Other")

    activity_type = MANUAL_KIND_TO_ACTIVITY[kind]
    sub_activity = kind

    if "agent_id" in data:
        agent_id = _int(data.get("agent_id"))
    else:
        agent_id = _int(existing.get("agent_id"))
    if "project_id" in data:
        project_id = _int(data.get("project_id"))
    else:
        project_id = _int(existing.get("project_id"))

    if "notes" in data:
        notes_in = data.get("notes")
    else:
        notes_in = existing.get("notes")
    notes = (str(notes_in).strip() or None) if notes_in is not None else None

    if kind in ("feedback", "training"):
        if not agent_id:
            return None, api_response(400, "Select an agent")
        project_id = None
    elif kind == "reporting":
        agent_id = None
        if not project_id:
            return None, api_response(400, "Select a project")
    else:
        agent_id = None
        project_id = None
        if not notes:
            return None, api_response(400, "Enter what you did")

    return {
        "activity_type": activity_type,
        "sub_activity": sub_activity,
        "agent_id": agent_id or None,
        "project_id": project_id or None,
        "notes": notes,
    }, None


def _manual_entry_dict(row: dict, viewer_id=None, viewer_is_manager: bool = False) -> dict:
    owner_id = _int(row.get("qa_user_id"))
    created = row.get("created_at")
    can_edit = bool(viewer_is_manager)
    can_delete = bool(viewer_is_manager) or (
        viewer_id is not None and owner_id == int(viewer_id) and _within_delete_window(created)
    )
    sub_activity = str(row.get("sub_activity") or "").strip().lower() or None
    agent_name = row.get("related_agent_name") or ""
    project_name = row.get("project_name") or ""
    notes = row.get("notes") or ""
    return {
        "qa_tracker_id": row.get("qa_tracker_id"),
        "qa_user_id": owner_id,
        "qa_user_name": row.get("qa_user_name") or row.get("user_name") or "",
        "work_date": _date_str(row.get("work_date")),
        "activity_type": row.get("activity_type"),
        "sub_activity": sub_activity,
        "agent_id": _int(row.get("agent_id")) or None,
        "agent_name": agent_name,
        "project_id": _int(row.get("project_id")) or None,
        "project_name": project_name,
        "detail": _manual_detail_text(sub_activity or "", agent_name, project_name, notes),
        "hours": _round4(row.get("hours")),
        "notes": notes,
        "created_at": _fmt_dt(created),
        "updated_at": _fmt_dt(row.get("updated_at")),
        "can_delete": can_delete,
        "can_edit": can_edit,
    }


def _qa_users_list(cursor) -> list:
    cursor.execute(
        """
        SELECT u.user_id, u.user_name
        FROM tfs_user u
        JOIN user_role r ON r.role_id = u.role_id
        WHERE u.is_active=1 AND u.is_delete=1
          AND (LOWER(TRIM(r.role_name)) = 'qa' OR LOWER(TRIM(r.role_name)) LIKE '%qa%')
        ORDER BY u.user_name
        """
    )
    return cursor.fetchall() or []


def _fetch_manual_detail_rows(cursor, where: str, params: list) -> list[dict]:
    cursor.execute(
        f"""
        SELECT
            qwt.qa_tracker_id,
            qwt.qa_user_id,
            qa.user_name AS qa_user_name,
            qwt.work_date,
            qwt.activity_type,
            qwt.sub_activity,
            qwt.hours,
            qwt.notes,
            qwt.project_id,
            p.project_name,
            qwt.agent_id,
            fb_agent.user_name AS related_agent_name,
            qwt.created_at,
            qwt.updated_at
        FROM qa_work_tracker qwt
        LEFT JOIN tfs_user qa ON qa.user_id = qwt.qa_user_id
        LEFT JOIN project p ON p.project_id = qwt.project_id
        LEFT JOIN tfs_user fb_agent ON fb_agent.user_id = qwt.agent_id
        WHERE {where}
          AND qwt.activity_type IN ('feedback','reporting')
          AND qwt.hours > 0
        ORDER BY qwt.work_date DESC, qwt.created_at ASC, qwt.qa_tracker_id
        """,
        tuple(params),
    )
    return [
        _manual_entry_dict(r)
        for r in (cursor.fetchall() or [])
        if _round4(r.get("hours")) > 0
    ]


def _deactivate_zero_manual_rows(cursor) -> None:
    cursor.execute(
        """
        UPDATE qa_work_tracker
        SET is_active=0, updated_at=%s
        WHERE is_active=1
          AND source_table='manual'
          AND activity_type IN ('feedback','reporting')
          AND hours <= 0
        """,
        (now_str(),),
    )


def _apply_range_counts(cursor, rec: dict, work_date: str | None) -> tuple[int, int]:
    fill_missing_range_counts(cursor, rec, work_date)
    return report_record_counts(rec)


def _calc_hours(
    qc_count,
    actual_target,
    *,
    qa_minutes_per_file=None,
    qa_minutes_per_record=None,
    qa_target_ranges=None,
    object_count=None,
    work_date=None,
    is_rework: bool = False,
) -> tuple[float, float, float]:
    resolved = resolve_qa_targets(
        task_target=actual_target,
        qa_minutes_per_file=qa_minutes_per_file,
        qa_minutes_per_record=qa_minutes_per_record,
        qa_target_ranges=qa_target_ranges,
        object_count=object_count,
        qc_generated_count=qc_count,
        work_date=work_date,
        is_rework=is_rework,
    )
    return resolved["actual_target"], resolved["qa_target"], resolved["hours"]


def _hours_from_qc_rec(
    rec: dict, work_date: str | None = None, is_rework: bool = False
) -> tuple[float, float, float]:
    return _calc_hours(
        rec.get("qc_generated_count"),
        rec.get("task_target") if rec.get("task_target") is not None else rec.get("actual_target"),
        qa_minutes_per_file=rec.get("qa_minutes_per_file"),
        qa_minutes_per_record=rec.get("qa_minutes_per_record"),
        qa_target_ranges=rec.get("qa_target_ranges"),
        object_count=rec.get("object_count"),
        work_date=work_date if work_date is not None else rec.get("work_date"),
        is_rework=is_rework,
    )

def _require_user(data: dict):
    logged_in_user_id = data.get("logged_in_user_id")
    if not logged_in_user_id:
        return None, None, api_response(400, "logged_in_user_id is required")
    return int(logged_in_user_id), data, None


def _resolve_target_qa(cursor, logged_in_user_id: int, requested_qa_user_id) -> tuple[int | None, dict, object | None]:
    ctx = get_role_context(cursor, logged_in_user_id)
    role_name = ctx.get("user_role_name") or ""
    if not role_name:
        return None, ctx, api_response(404, "User not found")

    if requested_qa_user_id in (None, "", 0, "0"):
        target_id = logged_in_user_id
    else:
        target_id = int(requested_qa_user_id)
        if target_id != logged_in_user_id and not _ctx_can_view_as_manager(ctx):
            return None, ctx, api_response(403, "Not authorized to view another user's QA tracker")
    return target_id, ctx, None


def _snapshot_has_usable_qa_target(raw: dict) -> bool:
    if parse_qa_target_ranges(raw.get("qa_target_ranges")):
        return True
    if _float(raw.get("qa_minutes_per_file")) > 0:
        return True
    if _float(raw.get("qa_minutes_per_record")) > 0:
        return True
    return False


def _is_legacy_hours_snapshot(raw) -> bool:
    """True when hours were stored with the old formula or with no QA target yet."""
    if raw is None or raw == "":
        return True
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="ignore")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return True
    if not isinstance(raw, dict):
        return True
    if raw.get("target_mode") in ("flat", "none"):
        return True
    if raw.get("frozen") in (1, True, "1") and "qa_minutes_per_file" not in raw and "qa_target_ranges" not in raw:
        return True
    if not _snapshot_has_usable_qa_target(raw):
        return True
    return False


def _existing_qc_snapshot(cursor, source_table, source_id, activity_type):
    cursor.execute(
        """
        SELECT target_snapshot, hours
        FROM qa_work_tracker
        WHERE source_table=%s AND source_id=%s AND activity_type=%s
        LIMIT 1
        """,
        (source_table, int(source_id), activity_type),
    )
    return cursor.fetchone()


def _target_snapshot(rec: dict, work_date: str | None, is_rework: bool = False) -> str:
    """Target inputs used the first time this QA row is stored."""
    ranges = rec.get("qa_target_ranges")
    if isinstance(ranges, (bytes, bytearray)):
        ranges = ranges.decode("utf-8", errors="ignore")
    payload = {
        "task_target": rec.get("task_target"),
        "qa_minutes_per_file": rec.get("qa_minutes_per_file"),
        "qa_minutes_per_record": rec.get("qa_minutes_per_record"),
        "qa_target_ranges": ranges,
        "qa_count_column": rec.get("qa_count_column"),
        "object_count": rec.get("object_count"),
        "work_date": str(work_date)[:10] if work_date else None,
        "is_rework": is_rework,
    }
    return json.dumps(payload, default=str)


_SNAPSHOT_COLUMN_READY = False


def ensure_target_snapshot_column(cursor) -> None:
    global _SNAPSHOT_COLUMN_READY
    if _SNAPSHOT_COLUMN_READY:
        return
    cursor.execute("SHOW COLUMNS FROM qa_work_tracker LIKE 'target_snapshot'")
    if not cursor.fetchone():
        cursor.execute(
            """
            ALTER TABLE qa_work_tracker
            ADD COLUMN target_snapshot JSON NULL AFTER hours
            """
        )
    cursor.execute(
        """
        UPDATE qa_work_tracker
        SET target_snapshot = JSON_OBJECT(
            'actual_target', actual_target,
            'qa_target', qa_target,
            'hours', hours,
            'frozen', 1
        )
        WHERE target_snapshot IS NULL
          AND activity_type IN ('qc_tasks', 'rework_qc')
        """
    )
    _SNAPSHOT_COLUMN_READY = True


def _upsert_qc_row(cursor, row: dict, now: str, overwrite_target: bool = False) -> int:
    """Insert or update a QC-sourced tracker row. Unique on (source_table, source_id, activity_type).

    Hours and targets are written only on insert. A later task-target change must not
    rewrite past days (same idea as agent tracker storing actual_target at submit time).
    """
    ensure_target_snapshot_column(cursor)
    source_id = int(row["source_id"])
    if not overwrite_target:
        existing = _existing_qc_snapshot(
            cursor, row["source_table"], source_id, row["activity_type"]
        )
        if existing is not None:
            snap = existing.get("target_snapshot")
            if isinstance(snap, (bytes, bytearray)):
                snap = snap.decode("utf-8", errors="ignore")
            if isinstance(snap, str):
                try:
                    snap = json.loads(snap)
                except Exception:
                    snap = {}
            if not isinstance(snap, dict):
                snap = {}
            if (
                _float(existing.get("hours")) <= 0
                or _is_legacy_hours_snapshot(existing.get("target_snapshot"))
                or (row["activity_type"] == "rework_qc" and not snap.get("is_rework"))
            ):
                overwrite_target = True
    if overwrite_target:
        target_sql = """
            actual_target=VALUES(actual_target),
            qa_target=VALUES(qa_target),
            hours=VALUES(hours),
            target_snapshot=VALUES(target_snapshot),"""
    else:
        target_sql = """
            target_snapshot=COALESCE(target_snapshot, VALUES(target_snapshot)),"""
    cursor.execute(
        f"""
        INSERT INTO qa_work_tracker (
            qa_user_id, work_date, activity_type, project_id, task_id,
            qc_record_id, tracker_id, source_table, source_id,
            file_record_count, qc_generated_count, actual_target, qa_target,
            hours, target_snapshot, qc_status, is_active, created_at, updated_at
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,%s,%s)
        ON DUPLICATE KEY UPDATE
            qa_user_id=VALUES(qa_user_id),
            work_date=VALUES(work_date),
            project_id=VALUES(project_id),
            task_id=VALUES(task_id),
            qc_record_id=VALUES(qc_record_id),
            tracker_id=VALUES(tracker_id),
            file_record_count=VALUES(file_record_count),
            qc_generated_count=VALUES(qc_generated_count),
            {target_sql}
            qc_status=VALUES(qc_status),
            is_active=1,
            updated_at=VALUES(updated_at),
            qa_tracker_id=LAST_INSERT_ID(qa_tracker_id)
        """,
        (
            int(row["qa_user_id"]),
            row["work_date"],
            row["activity_type"],
            row.get("project_id"),
            row.get("task_id"),
            row.get("qc_record_id"),
            row.get("tracker_id"),
            row["source_table"],
            source_id,
            _int(row.get("file_record_count")),
            _int(row.get("qc_generated_count")),
            row["actual_target"],
            row["qa_target"],
            row["hours"],
            row.get("target_snapshot"),
            row.get("qc_status"),
            now,
            now,
        ),
    )
    return int(cursor.lastrowid)


def _collect_qc_sources(cursor, qa_user_id: int, work_date: str) -> list[dict]:
    """Build tracker rows from existing QC tables for this QA user and date.

    First-time QC (file scored regular / rework / correction) → qc_tasks.
    Hours go to rework_qc only after the agent sends the file back and QA QCs it again.
    """
    rows: list[dict] = []
    ensure_qc_object_count_column(cursor)
    task_target_cols = """
            COALESCE(t.task_target, 0) AS task_target,
            t.qa_minutes_per_file,
            t.qa_minutes_per_record,
            t.qa_target_ranges,
            t.qa_count_column,
            qr.object_count,
            qr.qc_object_count,
            qr.whole_file_path
    """

    cursor.execute(
        f"""
        SELECT
            qr.id AS qc_record_id,
            qr.qa_user_id,
            qr.agent_id,
            qr.project_id,
            qr.task_id,
            qr.tracker_id,
            qr.status,
            qr.qc_status,
            COALESCE(qr.file_record_count, 0) AS file_record_count,
            COALESCE(qr.qc_generated_count, 0) AS qc_generated_count,
            {task_target_cols},
            p.project_name,
            t.task_name
        FROM qc_records qr
        LEFT JOIN task t ON t.task_id = qr.task_id
        LEFT JOIN project p ON p.project_id = qr.project_id
        WHERE qr.qa_user_id=%s
          AND DATE(qr.created_at)=%s
        """,
        (qa_user_id, work_date),
    )
    for rec in cursor.fetchall() or []:
        file_count, qc_count = _apply_range_counts(cursor, rec, work_date)
        actual, qa_target, hours = _hours_from_qc_rec(rec, work_date, is_rework=False)
        rows.append(
            {
                "qa_user_id": qa_user_id,
                "work_date": work_date,
                "activity_type": "qc_tasks",
                "project_id": rec.get("project_id"),
                "task_id": rec.get("task_id"),
                "qc_record_id": rec.get("qc_record_id"),
                "tracker_id": rec.get("tracker_id"),
                "source_table": "qc_records",
                "source_id": rec.get("qc_record_id"),
                "file_record_count": file_count,
                "qc_generated_count": qc_count,
                "object_count": rec.get("object_count"),
                "actual_target": actual,
                "qa_target": qa_target,
                "hours": hours,
                "target_snapshot": _target_snapshot(rec, work_date, is_rework=False),
                "qc_status": rec.get("status") or rec.get("qc_status"),
            }
        )

    cursor.execute(
        f"""
        SELECT
            rh.qc_rework_id AS source_id,
            qr.id AS qc_record_id,
            qr.qa_user_id,
            qr.project_id,
            qr.task_id,
            qr.tracker_id,
            qr.status,
            COALESCE(rh.file_record_count, qr.file_record_count, 0) AS file_record_count,
            COALESCE(rh.qc_data_generated_count, qr.qc_generated_count, 0) AS qc_generated_count,
            {task_target_cols}
        FROM qc_rework_history rh
        JOIN qc_records qr ON qr.id = rh.qc_record_id
        LEFT JOIN task t ON t.task_id = qr.task_id
        WHERE qr.qa_user_id=%s
          AND DATE(rh.updated_at)=%s
          AND LOWER(TRIM(COALESCE(rh.rework_file_qc_status, ''))) = 'completed'
          AND rh.rework_file_path IS NOT NULL
          AND TRIM(rh.rework_file_path) <> ''
        """,
        (qa_user_id, work_date),
    )
    for rec in cursor.fetchall() or []:
        file_count, qc_count = _apply_range_counts(cursor, rec, work_date)
        actual, qa_target, hours = _hours_from_qc_rec(rec, work_date, is_rework=True)
        rows.append(
            {
                "qa_user_id": qa_user_id,
                "work_date": work_date,
                "activity_type": "rework_qc",
                "project_id": rec.get("project_id"),
                "task_id": rec.get("task_id"),
                "qc_record_id": rec.get("qc_record_id"),
                "tracker_id": rec.get("tracker_id"),
                "source_table": "qc_rework_history",
                "source_id": rec.get("source_id"),
                "file_record_count": file_count,
                "qc_generated_count": qc_count,
                "object_count": rec.get("object_count"),
                "actual_target": actual,
                "qa_target": qa_target,
                "hours": hours,
                "target_snapshot": _target_snapshot(rec, work_date, is_rework=True),
                "qc_status": "rework",
            }
        )

    cursor.execute(
        f"""
        SELECT
            ch.qc_correction_id AS source_id,
            qr.id AS qc_record_id,
            qr.qa_user_id,
            qr.project_id,
            qr.task_id,
            qr.tracker_id,
            qr.status,
            COALESCE(qr.file_record_count, 0) AS file_record_count,
            COALESCE(qr.qc_generated_count, 0) AS qc_generated_count,
            {task_target_cols}
        FROM qc_correction_history ch
        JOIN qc_records qr ON qr.id = ch.qc_record_id
        LEFT JOIN task t ON t.task_id = qr.task_id
        WHERE qr.qa_user_id=%s
          AND DATE(ch.updated_at)=%s
          AND LOWER(TRIM(COALESCE(ch.correction_file_qc_status, ''))) = 'completed'
          AND ch.correction_file_path IS NOT NULL
          AND TRIM(ch.correction_file_path) <> ''
        """,
        (qa_user_id, work_date),
    )
    for rec in cursor.fetchall() or []:
        file_count, qc_count = _apply_range_counts(cursor, rec, work_date)
        actual, qa_target, hours = _hours_from_qc_rec(rec, work_date, is_rework=True)
        rows.append(
            {
                "qa_user_id": qa_user_id,
                "work_date": work_date,
                "activity_type": "rework_qc",
                "project_id": rec.get("project_id"),
                "task_id": rec.get("task_id"),
                "qc_record_id": rec.get("qc_record_id"),
                "tracker_id": rec.get("tracker_id"),
                "source_table": "qc_correction_history",
                "source_id": rec.get("source_id"),
                "file_record_count": file_count,
                "qc_generated_count": qc_count,
                "object_count": rec.get("object_count"),
                "actual_target": actual,
                "qa_target": qa_target,
                "hours": hours,
                "target_snapshot": _target_snapshot(rec, work_date, is_rework=True),
                "qc_status": "correction",
            }
        )

    return rows


def _qc_user_dates(cursor, qa_user_ids: list[int], start_date: str, end_date: str) -> list[tuple[int, str]]:
    if not qa_user_ids:
        return []
    placeholders = ",".join(["%s"] * len(qa_user_ids))
    ids = tuple(int(uid) for uid in qa_user_ids)
    params = ids + (start_date, end_date) + ids + (start_date, end_date) + ids + (start_date, end_date)
    cursor.execute(
        f"""
        SELECT DISTINCT qa_user_id, d FROM (
            SELECT qa_user_id, DATE(created_at) AS d
            FROM qc_records
            WHERE qa_user_id IN ({placeholders}) AND DATE(created_at) BETWEEN %s AND %s
            UNION
            SELECT qr.qa_user_id, DATE(rh.updated_at) AS d
            FROM qc_rework_history rh
            JOIN qc_records qr ON qr.id = rh.qc_record_id
            WHERE qr.qa_user_id IN ({placeholders})
              AND DATE(rh.updated_at) BETWEEN %s AND %s
              AND LOWER(TRIM(COALESCE(rh.rework_file_qc_status, ''))) = 'completed'
              AND rh.rework_file_path IS NOT NULL
              AND TRIM(rh.rework_file_path) <> ''
            UNION
            SELECT qr.qa_user_id, DATE(ch.updated_at) AS d
            FROM qc_correction_history ch
            JOIN qc_records qr ON qr.id = ch.qc_record_id
            WHERE qr.qa_user_id IN ({placeholders})
              AND DATE(ch.updated_at) BETWEEN %s AND %s
              AND LOWER(TRIM(COALESCE(ch.correction_file_qc_status, ''))) = 'completed'
              AND ch.correction_file_path IS NOT NULL
              AND TRIM(ch.correction_file_path) <> ''
        ) src
        WHERE d IS NOT NULL
        """,
        params,
    )
    out = []
    for row in cursor.fetchall() or []:
        uid = _int(row.get("qa_user_id"))
        work_date = _date_str(row.get("d"))
        if uid and work_date:
            out.append((uid, work_date))
    return out


def rebuild_september_qa_hours(cursor, start_date: str | None = None, end_date: str | None = None) -> int:
    """Recalculate QA hours from go-live onward using the task targets configured now."""
    start_date = _clamp_tracker_start(start_date or QA_TRACKER_GO_LIVE)
    if not end_date:
        end_date = today_str()[:10]
    cursor.execute(
        """
        SELECT DISTINCT qa_user_id
        FROM qc_records
        WHERE qa_user_id IS NOT NULL
        """
    )
    ids = [int(r["qa_user_id"]) for r in (cursor.fetchall() or []) if r.get("qa_user_id")]
    pairs = _qc_user_dates(cursor, ids, start_date, end_date)
    for uid, work_date in pairs:
        _sync_qc_rows(cursor, uid, work_date, overwrite_target=True)
    return len(pairs)


def _sync_month_from_qc(cursor, qa_user_ids: list[int], start_date: str, end_date: str) -> int:
    start_date = _clamp_tracker_start(start_date)
    end_date = _parse_date(end_date) or start_date
    if start_date > end_date:
        return 0
    pairs = _qc_user_dates(cursor, qa_user_ids, start_date, end_date)
    for uid, work_date in pairs:
        _sync_qc_rows(cursor, uid, work_date)
    return len(pairs)


def _sync_qc_rows(cursor, qa_user_id: int, work_date: str, overwrite_target: bool = False) -> int:
    work_date = _parse_date(work_date) or ""
    if not work_date or work_date < QA_TRACKER_GO_LIVE:
        return 0
    sources = _collect_qc_sources(cursor, qa_user_id, work_date)
    keep_keys = set()
    now = now_str()
    for row in sources:
        if row.get("source_id") is None:
            continue
        key = (row["source_table"], int(row["source_id"]), row["activity_type"])
        if key in keep_keys:
            continue
        keep_keys.add(key)
        _upsert_qc_row(cursor, row, now, overwrite_target=overwrite_target)

    cursor.execute(
        """
        SELECT qa_tracker_id, source_table, source_id, activity_type
        FROM qa_work_tracker
        WHERE qa_user_id=%s
          AND work_date=%s
          AND activity_type IN ('qc_tasks', 'rework_qc')
          AND is_active=1
        """,
        (qa_user_id, work_date),
    )
    for existing in cursor.fetchall() or []:
        key = (
            existing.get("source_table"),
            _int(existing.get("source_id")),
            existing.get("activity_type"),
        )
        if key not in keep_keys:
            cursor.execute(
                "UPDATE qa_work_tracker SET is_active=0, updated_at=%s WHERE qa_tracker_id=%s",
                (now, int(existing["qa_tracker_id"])),
            )
    return len(sources)


def _fetch_day_payload(
    cursor,
    qa_user_id: int,
    work_date: str,
    viewer_id=None,
    viewer_is_manager: bool = False,
) -> dict:
    cursor.execute(
        """
        SELECT
            qwt.*,
            p.project_name,
            t.task_name,
            agent.user_name AS agent_name,
            fb_agent.user_name AS related_agent_name,
            COALESCE(
                NULLIF(TRIM(CAST(twt.date_time AS CHAR)), ''),
                CAST(qr.date_of_file_submission AS CHAR)
            ) AS file_submitted_at,
            CAST(qr.created_at AS CHAR) AS qc_created_at,
            CAST(qr.updated_at AS CHAR) AS qc_updated_at,
            COALESCE(
                NULLIF(TRIM(CAST(twt.date_time AS CHAR)), ''),
                CAST(qr.date_of_file_submission AS CHAR),
                CAST(qr.created_at AS CHAR),
                CAST(qwt.created_at AS CHAR)
            ) AS tracker_time,
            twt.shift AS tracker_shift
        FROM qa_work_tracker qwt
        LEFT JOIN project p ON p.project_id = qwt.project_id
        LEFT JOIN task t ON t.task_id = qwt.task_id
        LEFT JOIN qc_records qr
          ON qr.id = COALESCE(
              qwt.qc_record_id,
              IF(qwt.source_table = 'qc_records', qwt.source_id, NULL)
          )
        LEFT JOIN tfs_user agent ON agent.user_id = qr.agent_id
        LEFT JOIN tfs_user fb_agent ON fb_agent.user_id = qwt.agent_id
        LEFT JOIN task_work_tracker twt
          ON twt.tracker_id = COALESCE(qwt.tracker_id, qr.tracker_id)
        WHERE qwt.qa_user_id=%s
          AND qwt.work_date=%s
          AND qwt.is_active=1
        ORDER BY qwt.activity_type, p.project_name, t.task_name, qwt.qa_tracker_id
        """,
        (qa_user_id, work_date),
    )
    rows = cursor.fetchall() or []

    holidays = load_holidays_around(
        cursor,
        work_date,
        *[r.get("file_submitted_at") for r in rows],
        *[r.get("qc_created_at") for r in rows],
        *[r.get("qc_updated_at") for r in rows],
    )

    buckets = {
        "qc_tasks": {"hours": 0.0, "expected": EXPECTED_HOURS["qc_tasks"], "files": 0, "file_records": 0, "qc_records": 0},
        "rework_qc": {"hours": 0.0, "expected": EXPECTED_HOURS["rework_qc"], "files": 0, "file_records": 0, "qc_records": 0},
        "feedback": {"hours": 0.0, "expected": EXPECTED_HOURS["feedback"]},
        "reporting": {"hours": 0.0, "expected": EXPECTED_HOURS["reporting"]},
    }
    files = []
    late_files = 0
    projects_map = defaultdict(
        lambda: {
            "project_id": None,
            "project_name": "",
            "task_id": None,
            "task_name": "",
            "qc_hours": 0.0,
            "rework_hours": 0.0,
            "qc_files": 0,
            "rework_files": 0,
            "file_records": 0,
            "qc_records": 0,
            "late_files": 0,
            "actual_target": 0.0,
            "qa_target": 0.0,
            "files": [],
        }
    )

    for r in rows:
        activity = r.get("activity_type")
        hours = _round4(r.get("hours"))
        if activity in buckets:
            buckets[activity]["hours"] = _round4(buckets[activity]["hours"] + hours)
        if activity in QC_ACTIVITIES:
            buckets[activity]["files"] += 1
            buckets[activity]["file_records"] += _int(r.get("file_record_count"))
            buckets[activity]["qc_records"] += _int(r.get("qc_generated_count"))

            submitted_at = r.get("file_submitted_at")
            qc_created = parse_dt(r.get("qc_created_at"))
            qc_updated = parse_dt(r.get("qc_updated_at"))
            qc_done = qc_created
            if activity == "rework_qc" and qc_updated and (not qc_done or qc_updated > qc_done):
                qc_done = qc_updated
            # Late QC SLA only from Sep 2026 (old temp_qc months excluded)
            applies = sla_applies_to_submission(submitted_at)
            sla_hours = sla_hours_for_submission(r.get("tracker_shift"), submitted_at)
            deadline = qc_deadline(submitted_at, holidays, hours=sla_hours) if applies else None
            late = (
                is_qc_late(
                    submitted_at,
                    qc_done.strftime("%Y-%m-%d %H:%M:%S") if qc_done else None,
                    holidays,
                    hours=sla_hours,
                )
                if applies
                else False
            )
            if late:
                late_files += 1

            file_row = {
                "qa_tracker_id": r.get("qa_tracker_id"),
                "activity_type": activity,
                "project_id": r.get("project_id"),
                "project_name": r.get("project_name"),
                "task_id": r.get("task_id"),
                "task_name": r.get("task_name"),
                "agent_name": r.get("agent_name"),
                "qc_record_id": r.get("qc_record_id"),
                "tracker_id": r.get("tracker_id"),
                "tracker_time": _fmt_dt(r.get("tracker_time")) or _fmt_dt(r.get("created_at")),
                "file_submitted_at": _fmt_dt(submitted_at),
                "qc_done_at": qc_done.strftime("%Y-%m-%d %H:%M:%S") if qc_done else "",
                "qc_deadline": deadline.strftime("%Y-%m-%d %H:%M:%S") if deadline else "",
                "is_late": bool(late),
                "sla_applies": bool(applies),
                "qc_status": r.get("qc_status"),
                "file_record_count": _int(r.get("file_record_count")),
                "qc_generated_count": _int(r.get("qc_generated_count")),
                "actual_target": _round4(r.get("actual_target")),
                "qa_target": _round4(r.get("qa_target")),
                "hours": hours,
            }
            files.append(file_row)
            key = (r.get("project_id"), r.get("task_id"))
            proj = projects_map[key]
            proj["project_id"] = r.get("project_id")
            proj["project_name"] = r.get("project_name") or "—"
            proj["task_id"] = r.get("task_id")
            proj["task_name"] = r.get("task_name") or "—"
            proj["actual_target"] = _round4(r.get("actual_target"))
            proj["qa_target"] = _round4(r.get("qa_target"))
            proj["file_records"] += _int(r.get("file_record_count"))
            proj["qc_records"] += _int(r.get("qc_generated_count"))
            if late:
                proj["late_files"] += 1
            proj["files"].append(file_row)
            if activity == "qc_tasks":
                proj["qc_hours"] = _round4(proj["qc_hours"] + hours)
                proj["qc_files"] += 1
            else:
                proj["rework_hours"] = _round4(proj["rework_hours"] + hours)
                proj["rework_files"] += 1

    total_hours = _round4(sum(b["hours"] for b in buckets.values()))
    manual_entries = []
    for r in rows:
        if r.get("activity_type") not in MANUAL_ACTIVITIES:
            continue
        hours = _round4(r.get("hours"))
        if hours <= 0:
            continue
        manual_entries.append(_manual_entry_dict(r, viewer_id, viewer_is_manager))
    return {
        "work_date": work_date,
        "qa_user_id": qa_user_id,
        "expected": {**EXPECTED_HOURS, "total": EXPECTED_TOTAL},
        "buckets": buckets,
        "total_hours": total_hours,
        "late_files": late_files,
        "projects": list(projects_map.values()),
        "files": files,
        "feedback_hours": buckets["feedback"]["hours"],
        "reporting_hours": buckets["reporting"]["hours"],
        "manual_entries": manual_entries,
        "notes": next((r.get("notes") or "" for r in rows if r.get("activity_type") in MANUAL_ACTIVITIES and r.get("notes")), "")
        or next((r.get("notes") or "" for r in rows if r.get("notes")), ""),
    }


def _qc_file_sla_rows(cursor, where: str, params: list) -> list[dict]:
    """Per QC/rework file timestamps for late counting (same WHERE as list/monthly).

    Only includes submissions from QC_FORM_SLA_EFFECTIVE_FROM (Sep 2026) onward.
    """
    cursor.execute(
        f"""
        SELECT
            qwt.qa_user_id,
            qwt.work_date,
            qwt.project_id,
            qwt.task_id,
            qwt.activity_type,
            COALESCE(
                NULLIF(TRIM(CAST(twt.date_time AS CHAR)), ''),
                CAST(qr.date_of_file_submission AS CHAR)
            ) AS file_submitted_at,
            CAST(qr.created_at AS CHAR) AS qc_created_at,
            CAST(qr.updated_at AS CHAR) AS qc_updated_at,
            twt.shift AS tracker_shift
        FROM qa_work_tracker qwt
        LEFT JOIN qc_records qr
          ON qr.id = COALESCE(
              qwt.qc_record_id,
              IF(qwt.source_table = 'qc_records', qwt.source_id, NULL)
          )
        LEFT JOIN task_work_tracker twt
          ON twt.tracker_id = COALESCE(qwt.tracker_id, qr.tracker_id)
        WHERE {where}
          AND qwt.activity_type IN ('qc_tasks', 'rework_qc')
          AND DATE(
            COALESCE(
              NULLIF(TRIM(CAST(twt.date_time AS CHAR)), ''),
              CAST(qr.date_of_file_submission AS CHAR)
            )
          ) >= %s
        """,
        tuple([*params, QC_FORM_SLA_EFFECTIVE_FROM_SQL]),
    )
    return cursor.fetchall() or []


def _annotate_late_counts(cursor, rows: list[dict], where: str, params: list, *, by_day: bool) -> None:
    """Mutate day or monthly rows in-place with late_files (and project late_files).

    Pre-Sep 2026 submissions are excluded (old temp_qc flow).
    """
    if not rows:
        return
    sla_rows = _qc_file_sla_rows(cursor, where, params)
    holidays = load_holidays_around(
        cursor,
        *[r.get("work_date") for r in sla_rows],
        *[r.get("file_submitted_at") for r in sla_rows],
        *[r.get("qc_created_at") for r in sla_rows],
    )

    # key -> late count; project key -> late count
    late_by_key: dict = defaultdict(int)
    late_by_proj: dict = defaultdict(int)

    for r in sla_rows:
        submitted_at = r.get("file_submitted_at")
        if not sla_applies_to_submission(submitted_at):
            continue
        qc_created = parse_dt(r.get("qc_created_at"))
        qc_updated = parse_dt(r.get("qc_updated_at"))
        qc_done = qc_created
        if r.get("activity_type") == "rework_qc" and qc_updated and (not qc_done or qc_updated > qc_done):
            qc_done = qc_updated
        if not is_qc_late(
            submitted_at,
            qc_done.strftime("%Y-%m-%d %H:%M:%S") if qc_done else None,
            holidays,
            hours=sla_hours_for_submission(r.get("tracker_shift"), submitted_at),
        ):
            continue
        qa_id = _int(r.get("qa_user_id"))
        wd = _date_str(r.get("work_date"))
        if by_day:
            late_by_key[(qa_id, wd)] += 1
            late_by_proj[(qa_id, wd, r.get("project_id"), r.get("task_id"))] += 1
        else:
            late_by_key[qa_id] += 1
            late_by_proj[(qa_id, r.get("project_id"), r.get("task_id"))] += 1

    for row in rows:
        qa_id = _int(row.get("qa_user_id"))
        if by_day:
            wd = row.get("work_date") or ""
            row["late_files"] = late_by_key.get((qa_id, wd), 0)
            for p in row.get("projects") or []:
                p["late_files"] = late_by_proj.get(
                    (qa_id, wd, p.get("project_id"), p.get("task_id")), 0
                )
        else:
            row["late_files"] = late_by_key.get(qa_id, 0)
            for p in row.get("projects") or []:
                p["late_files"] = late_by_proj.get(
                    (qa_id, p.get("project_id"), p.get("task_id")), 0
                )


@qa_tracker_bp.route("/sync", methods=["POST"])
def sync_qa_tracker():
    data = request.get_json(silent=True) or {}
    logged_in_user_id, _, err = _require_user(data)
    if err:
        return err

    work_date = _parse_date(data.get("work_date")) or today_str()
    if work_date < QA_TRACKER_GO_LIVE:
        return api_response(400, f"QA report starts from {QA_TRACKER_GO_LIVE}")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        target_id, _, auth_err = _resolve_target_qa(cursor, logged_in_user_id, data.get("qa_user_id"))
        if auth_err:
            return auth_err
        synced = _sync_qc_rows(cursor, target_id, work_date)
        conn.commit()
        return api_response(200, "QA tracker synced", {"synced_rows": synced, "work_date": work_date, "qa_user_id": target_id})
    except Exception as e:
        conn.rollback()
        return api_response(500, f"Error syncing QA tracker: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@qa_tracker_bp.route("/rebuild_hours", methods=["POST"])
def qa_tracker_rebuild_hours():
    data = request.get_json(silent=True) or {}
    logged_in_user_id, _, err = _require_user(data)
    if err:
        return err

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ctx = get_role_context(cursor, logged_in_user_id)
        if not _ctx_is_manager(ctx):
            return api_response(403, "Only managers can rebuild QA hours")
        rebuilt = rebuild_september_qa_hours(cursor)
        conn.commit()
        return api_response(
            200,
            "QA hours rebuilt from go-live using current task targets",
            {"pairs": rebuilt, "start_date": QA_TRACKER_GO_LIVE},
        )
    except Exception as e:
        conn.rollback()
        return api_response(500, f"Error rebuilding QA hours: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@qa_tracker_bp.route("/add_entry", methods=["POST"])
def qa_tracker_add_entry():
    data = request.get_json(silent=True) or {}
    logged_in_user_id, _, err = _require_user(data)
    if err:
        return err

    today = today_str()
    requested_date = _parse_date(data.get("work_date")) or today
    if requested_date > today:
        return api_response(400, "Tracker cannot be added for a future date")
    if requested_date < QA_TRACKER_GO_LIVE:
        return api_response(400, f"QA report starts from {QA_TRACKER_GO_LIVE}")
    details, detail_err = _validate_manual_details(data)
    if detail_err:
        return detail_err
    hours = _round4(data.get("hours"))
    if hours <= 0:
        return api_response(400, "Hours must be greater than 0")
    if hours > 24:
        return api_response(400, "Hours cannot be more than 24 in one entry")
    requested_qa = data.get("qa_user_id")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        from utils.roster_helpers import reject_read_only_actor
        deny = reject_read_only_actor(cursor, logged_in_user_id)
        if deny:
            return deny
        target_id, ctx, auth_err = _resolve_target_qa(cursor, logged_in_user_id, requested_qa)
        if auth_err:
            return auth_err
        manager = _ctx_is_manager(ctx)
        if manager:
            if requested_qa in (None, "", 0, "0"):
                return api_response(400, "Select a QA to add hours for")
            if not _user_is_qa(cursor, target_id):
                return api_response(400, "Tracker can only be added for a QA")
        else:
            if not _user_is_qa(cursor, logged_in_user_id):
                return api_response(403, "Only QA can add this tracker")
            if target_id != logged_in_user_id:
                return api_response(403, "Not authorized to add hours for another user")
            if requested_date != today:
                return api_response(400, "Tracker can only be added for today")
        work_date = requested_date if manager else today

        now = now_str()
        temp_source_id = (uuid.uuid4().int % 2147483646) + 1
        cursor.execute(
            """
            INSERT INTO qa_work_tracker (
                qa_user_id, work_date, activity_type, sub_activity, project_id, agent_id,
                source_table, source_id, hours, notes, is_active, created_at, updated_at
            ) VALUES (%s,%s,%s,%s,%s,%s,'manual',%s,%s,%s,1,%s,%s)
            """,
            (
                target_id,
                work_date,
                details["activity_type"],
                details["sub_activity"],
                details["project_id"],
                details["agent_id"],
                temp_source_id,
                hours,
                details["notes"],
                now,
                now,
            ),
        )
        new_id = int(cursor.lastrowid)
        cursor.execute(
            "UPDATE qa_work_tracker SET source_id=%s WHERE qa_tracker_id=%s",
            (new_id, new_id),
        )
        conn.commit()
        payload = _fetch_day_payload(
            cursor, target_id, work_date, logged_in_user_id, manager
        )
        return api_response(200, "Hours added", payload)
    except Exception as e:
        conn.rollback()
        return api_response(500, f"Error adding QA hours: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@qa_tracker_bp.route("/delete_entry", methods=["POST"])
def qa_tracker_delete_entry():
    data = request.get_json(silent=True) or {}
    logged_in_user_id, _, err = _require_user(data)
    if err:
        return err

    qa_tracker_id = _int(data.get("qa_tracker_id"))
    if not qa_tracker_id:
        return api_response(400, "qa_tracker_id is required")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        from utils.roster_helpers import reject_read_only_actor
        deny = reject_read_only_actor(cursor, logged_in_user_id)
        if deny:
            return deny
        cursor.execute(
            """
            SELECT qa_tracker_id, qa_user_id, work_date, activity_type, created_at
            FROM qa_work_tracker
            WHERE qa_tracker_id=%s AND is_active=1
            LIMIT 1
            """,
            (qa_tracker_id,),
        )
        row = cursor.fetchone()
        if not row:
            return api_response(404, "Entry not found")
        if row.get("activity_type") not in MANUAL_ACTIVITIES:
            return api_response(400, "Only Feedback and Reporting entries can be deleted")

        ctx = get_role_context(cursor, logged_in_user_id)
        owner_id = int(row["qa_user_id"])
        manager = _ctx_is_manager(ctx)
        if owner_id != logged_in_user_id and not manager:
            return api_response(403, "Not authorized to delete this entry")
        if not manager and not _within_delete_window(row.get("created_at")):
            return api_response(403, "Entries can only be deleted within 24 hours")

        cursor.execute(
            "UPDATE qa_work_tracker SET is_active=0, updated_at=%s WHERE qa_tracker_id=%s",
            (now_str(), qa_tracker_id),
        )
        conn.commit()
        work_date = _date_str(row.get("work_date"))
        payload = _fetch_day_payload(cursor, owner_id, work_date, logged_in_user_id, manager)
        return api_response(200, "Entry deleted", payload)
    except Exception as e:
        conn.rollback()
        return api_response(500, f"Error deleting QA hours: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@qa_tracker_bp.route("/update_entry", methods=["POST"])
def qa_tracker_update_entry():
    data = request.get_json(silent=True) or {}
    logged_in_user_id, _, err = _require_user(data)
    if err:
        return err

    qa_tracker_id = _int(data.get("qa_tracker_id"))
    if not qa_tracker_id:
        return api_response(400, "qa_tracker_id is required")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        from utils.roster_helpers import reject_read_only_actor
        deny = reject_read_only_actor(cursor, logged_in_user_id)
        if deny:
            return deny
        ctx = get_role_context(cursor, logged_in_user_id)
        if not _ctx_is_manager(ctx):
            return api_response(403, "Only managers can update Feedback and Reporting entries")

        cursor.execute(
            """
            SELECT qa_tracker_id, qa_user_id, work_date, activity_type, sub_activity,
                   hours, notes, project_id, agent_id
            FROM qa_work_tracker
            WHERE qa_tracker_id=%s AND is_active=1
            LIMIT 1
            """,
            (qa_tracker_id,),
        )
        row = cursor.fetchone()
        if not row:
            return api_response(404, "Entry not found")
        if row.get("activity_type") not in MANUAL_ACTIVITIES:
            return api_response(400, "Only Feedback and Reporting entries can be updated")
        if not _user_is_qa(cursor, int(row["qa_user_id"])):
            return api_response(400, "Tracker can only be updated for a QA")

        details, detail_err = _validate_manual_details(data, row)
        if detail_err:
            return detail_err
        work_date = _parse_date(data.get("work_date")) or _date_str(row.get("work_date"))
        if work_date > today_str():
            return api_response(400, "Tracker cannot be added for a future date")
        if work_date < QA_TRACKER_GO_LIVE:
            return api_response(400, f"QA report starts from {QA_TRACKER_GO_LIVE}")
        hours = _round4(data.get("hours") if data.get("hours") is not None else row.get("hours"))
        if hours <= 0:
            return api_response(400, "Hours must be greater than 0")
        if hours > 24:
            return api_response(400, "Hours cannot be more than 24 in one entry")

        cursor.execute(
            """
            UPDATE qa_work_tracker
            SET work_date=%s, activity_type=%s, sub_activity=%s, project_id=%s, agent_id=%s,
                hours=%s, notes=%s, updated_at=%s
            WHERE qa_tracker_id=%s
            """,
            (
                work_date,
                details["activity_type"],
                details["sub_activity"],
                details["project_id"],
                details["agent_id"],
                hours,
                details["notes"],
                now_str(),
                qa_tracker_id,
            ),
        )
        conn.commit()
        owner_id = int(row["qa_user_id"])
        payload = _fetch_day_payload(cursor, owner_id, work_date, logged_in_user_id, True)
        cursor.execute(
            """
            SELECT
                qwt.qa_tracker_id,
                qwt.qa_user_id,
                qa.user_name AS qa_user_name,
                qwt.work_date,
                qwt.activity_type,
                qwt.sub_activity,
                qwt.hours,
                qwt.notes,
                qwt.project_id,
                p.project_name,
                qwt.agent_id,
                fb_agent.user_name AS related_agent_name,
                qwt.created_at,
                qwt.updated_at
            FROM qa_work_tracker qwt
            LEFT JOIN tfs_user qa ON qa.user_id = qwt.qa_user_id
            LEFT JOIN project p ON p.project_id = qwt.project_id
            LEFT JOIN tfs_user fb_agent ON fb_agent.user_id = qwt.agent_id
            WHERE qwt.qa_tracker_id=%s
            LIMIT 1
            """,
            (qa_tracker_id,),
        )
        updated = cursor.fetchone() or {**row, **details, "work_date": work_date, "hours": hours}
        payload["entry"] = _manual_entry_dict(updated, logged_in_user_id, True)
        return api_response(200, "Entry updated", payload)
    except Exception as e:
        conn.rollback()
        return api_response(500, f"Error updating QA hours: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@qa_tracker_bp.route("/entries", methods=["POST"])
def qa_tracker_entries():
    data = request.get_json(silent=True) or {}
    logged_in_user_id, _, err = _require_user(data)
    if err:
        return err

    start_date = _parse_date(data.get("start_date")) or today_str()
    end_date = _parse_date(data.get("end_date")) or start_date
    resolved = _resolve_report_range(start_date, end_date)
    if not resolved:
        return api_response(
            200,
            "QA tracker entries fetched",
            {"start_date": start_date, "end_date": end_date, "entries": [], "qa_users": []},
        )
    start_date, end_date = resolved

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ctx = get_role_context(cursor, logged_in_user_id)
        role_name = ctx.get("user_role_name") or ""
        if not role_name:
            return api_response(404, "User not found")
        manager = _ctx_can_view_as_manager(ctx)
        can_write = _ctx_is_manager(ctx)
        requested = data.get("qa_user_id")
        _purge_pre_golive_rows(cursor)
        _deactivate_zero_manual_rows(cursor)
        conn.commit()
        params = [QA_TRACKER_GO_LIVE, start_date, end_date]
        where = """
            qwt.is_active=1
            AND qwt.source_table='manual'
            AND qwt.activity_type IN ('feedback','reporting')
            AND qwt.hours > 0
            AND qwt.work_date >= %s
            AND qwt.work_date BETWEEN %s AND %s
        """
        if manager:
            if requested not in (None, "", 0, "0"):
                where += " AND qwt.qa_user_id=%s"
                params.append(int(requested))
        else:
            where += " AND qwt.qa_user_id=%s"
            params.append(logged_in_user_id)

        activity_type = str(data.get("activity_type") or "").strip().lower()
        if activity_type in MANUAL_ACTIVITIES:
            where += " AND qwt.activity_type=%s"
            params.append(activity_type)

        cursor.execute(
            f"""
            SELECT
                qwt.qa_tracker_id,
                qwt.qa_user_id,
                qa.user_name AS qa_user_name,
                qwt.work_date,
                qwt.activity_type,
                qwt.sub_activity,
                qwt.hours,
                qwt.notes,
                qwt.project_id,
                p.project_name,
                qwt.agent_id,
                fb_agent.user_name AS related_agent_name,
                qwt.created_at,
                qwt.updated_at
            FROM qa_work_tracker qwt
            LEFT JOIN tfs_user qa ON qa.user_id = qwt.qa_user_id
            LEFT JOIN project p ON p.project_id = qwt.project_id
            LEFT JOIN tfs_user fb_agent ON fb_agent.user_id = qwt.agent_id
            WHERE {where}
            ORDER BY qwt.work_date DESC, qwt.created_at DESC, qwt.qa_tracker_id DESC
            """,
            tuple(params),
        )
        rows = cursor.fetchall() or []
        entries = [_manual_entry_dict(r, logged_in_user_id, can_write) for r in rows]
        qa_users = _qa_users_list(cursor) if manager else []
        return api_response(
            200,
            "QA tracker entries fetched",
            {
                "start_date": start_date,
                "end_date": end_date,
                "entries": entries,
                "qa_users": qa_users,
            },
        )
    except Exception as e:
        return api_response(500, f"Error fetching QA tracker entries: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@qa_tracker_bp.route("/save", methods=["POST"])
def save_qa_tracker():
    return qa_tracker_add_entry()


@qa_tracker_bp.route("/day", methods=["POST"])
def qa_tracker_day():
    data = request.get_json(silent=True) or {}
    logged_in_user_id, _, err = _require_user(data)
    if err:
        return err

    work_date = _parse_date(data.get("work_date")) or today_str()
    if work_date < QA_TRACKER_GO_LIVE:
        return api_response(400, f"QA report starts from {QA_TRACKER_GO_LIVE}")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    target_id = None
    try:
        target_id, _, auth_err = _resolve_target_qa(cursor, logged_in_user_id, data.get("qa_user_id"))
        if auth_err:
            return auth_err
        _purge_pre_golive_rows(cursor)
        try:
            _rebuild_today_hours_once(cursor, conn)
        except Exception:
            conn.rollback()
            import traceback
            traceback.print_exc()
        _sync_qc_rows(cursor, target_id, work_date)
        conn.commit()
        ctx = get_role_context(cursor, logged_in_user_id)
        payload = _fetch_day_payload(
            cursor, target_id, work_date, logged_in_user_id, _ctx_is_manager(ctx)
        )
        return api_response(200, "QA tracker day fetched", payload)
    except Exception as e:
        conn.rollback()
        if target_id:
            try:
                ctx = get_role_context(cursor, logged_in_user_id)
                payload = _fetch_day_payload(
                    cursor,
                    target_id,
                    work_date,
                    logged_in_user_id,
                    _ctx_is_manager(ctx),
                )
                return api_response(200, "QA tracker day fetched", payload)
            except Exception:
                pass
        return api_response(500, f"Error fetching QA tracker: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@qa_tracker_bp.route("/list", methods=["POST"])
def qa_tracker_list():
    data = request.get_json(silent=True) or {}
    logged_in_user_id, _, err = _require_user(data)
    if err:
        return err

    month_bounds = _month_bounds(data.get("month_year"))
    if month_bounds:
        start_date, end_date, _ = month_bounds
    else:
        start_date = _parse_date(data.get("start_date")) or today_str()
        end_date = _parse_date(data.get("end_date")) or start_date
    resolved = _resolve_report_range(start_date, end_date)
    if not resolved:
        return api_response(
            200,
            "QA tracker list fetched",
            {
                "start_date": start_date,
                "end_date": end_date,
                "month_year": (_month_bounds(data.get("month_year")) or (None, None, None))[2],
                "expected": {**EXPECTED_HOURS, "total": EXPECTED_TOTAL},
                "rows": [],
                "qa_users": [],
            },
        )
    start_date, end_date = resolved

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ctx = get_role_context(cursor, logged_in_user_id)
        role_name = ctx.get("user_role_name") or ""
        if not role_name:
            return api_response(404, "User not found")

        manager = _ctx_can_view_as_manager(ctx)
        requested = data.get("qa_user_id")
        where, params = _active_tracker_where(start_date, end_date)

        if manager:
            if requested not in (None, "", 0, "0"):
                where += " AND qwt.qa_user_id=%s"
                params.append(int(requested))
        else:
            where += " AND qwt.qa_user_id=%s"
            params.append(logged_in_user_id)

        _prepare_tracker_read(
            cursor, conn, manager, logged_in_user_id, requested, start_date, end_date
        )

        cursor.execute(
            f"""
            SELECT
                qwt.qa_user_id,
                qa.user_name AS qa_user_name,
                qwt.work_date,
                qwt.activity_type,
                qwt.project_id,
                p.project_name,
                qwt.task_id,
                t.task_name,
                SUM(qwt.hours) AS hours,
                SUM(CASE WHEN qwt.activity_type IN ('qc_tasks','rework_qc') THEN 1 ELSE 0 END) AS files,
                SUM(qwt.file_record_count) AS file_records,
                SUM(qwt.qc_generated_count) AS qc_records
            FROM qa_work_tracker qwt
            LEFT JOIN tfs_user qa ON qa.user_id = qwt.qa_user_id
            LEFT JOIN project p ON p.project_id = qwt.project_id
            LEFT JOIN task t ON t.task_id = qwt.task_id
            WHERE {where}
            GROUP BY
                qwt.qa_user_id, qa.user_name, qwt.work_date, qwt.activity_type,
                qwt.project_id, p.project_name, qwt.task_id, t.task_name
            ORDER BY qwt.work_date DESC, qa.user_name, p.project_name
            """,
            tuple(params),
        )
        raw = cursor.fetchall() or []

        days = {}
        for r in raw:
            work_date = r.get("work_date")
            wd = work_date.strftime("%Y-%m-%d") if hasattr(work_date, "strftime") else str(work_date or "")[:10]
            qa_id = int(r.get("qa_user_id"))
            key = (qa_id, wd)
            if key not in days:
                days[key] = {
                    "qa_user_id": qa_id,
                    "qa_user_name": r.get("qa_user_name"),
                    "work_date": wd,
                    "qc_hours": 0.0,
                    "rework_hours": 0.0,
                    "feedback_hours": 0.0,
                    "reporting_hours": 0.0,
                    "total_hours": 0.0,
                    "qc_files": 0,
                    "rework_files": 0,
                    "qc_records": 0,
                    "file_records": 0,
                    "late_files": 0,
                    "expected_total": EXPECTED_TOTAL,
                    "projects": {},
                    "manual_entries": [],
                }
            day = days[key]
            activity = r.get("activity_type")
            hours = _round4(r.get("hours"))
            if activity == "qc_tasks":
                day["qc_hours"] = _round4(day["qc_hours"] + hours)
                day["qc_files"] += _int(r.get("files"))
            elif activity == "rework_qc":
                day["rework_hours"] = _round4(day["rework_hours"] + hours)
                day["rework_files"] += _int(r.get("files"))
            elif activity == "feedback":
                day["feedback_hours"] = _round4(day["feedback_hours"] + hours)
            elif activity == "reporting":
                day["reporting_hours"] = _round4(day["reporting_hours"] + hours)
            day["qc_records"] += _int(r.get("qc_records"))
            day["file_records"] += _int(r.get("file_records"))

            if activity in QC_ACTIVITIES and r.get("project_id") is not None:
                pk = (r.get("project_id"), r.get("task_id"))
                proj = day["projects"].setdefault(
                    pk,
                    {
                        "project_id": r.get("project_id"),
                        "project_name": r.get("project_name") or "—",
                        "task_id": r.get("task_id"),
                        "task_name": r.get("task_name") or "—",
                        "qc_hours": 0.0,
                        "rework_hours": 0.0,
                        "files": 0,
                        "file_records": 0,
                        "qc_records": 0,
                        "late_files": 0,
                    },
                )
                if activity == "qc_tasks":
                    proj["qc_hours"] = _round4(proj["qc_hours"] + hours)
                else:
                    proj["rework_hours"] = _round4(proj["rework_hours"] + hours)
                proj["files"] += _int(r.get("files"))
                proj["file_records"] += _int(r.get("file_records"))
                proj["qc_records"] += _int(r.get("qc_records"))

        for entry in _fetch_manual_detail_rows(cursor, where, params):
            wd = entry.get("work_date") or ""
            qa_id = _int(entry.get("qa_user_id"))
            key = (qa_id, wd)
            if key in days:
                days[key].setdefault("manual_entries", []).append(entry)

        result = []
        for day in days.values():
            day["total_hours"] = _round4(
                day["qc_hours"] + day["rework_hours"] + day["feedback_hours"] + day["reporting_hours"]
            )
            if (
                day["total_hours"] == 0
                and day["qc_files"] == 0
                and day["rework_files"] == 0
            ):
                continue
            day["projects"] = list(day["projects"].values())
            result.append(day)

        _annotate_late_counts(cursor, result, where, params, by_day=True)

        qa_users = []
        if manager:
            cursor.execute(
                """
                SELECT u.user_id, u.user_name
                FROM tfs_user u
                JOIN user_role r ON r.role_id = u.role_id
                WHERE u.is_active=1 AND u.is_delete=1
                  AND (LOWER(TRIM(r.role_name)) = 'qa' OR LOWER(TRIM(r.role_name)) LIKE '%qa%')
                ORDER BY u.user_name
                """
            )
            qa_users = cursor.fetchall() or []

        return api_response(
            200,
            "QA tracker list fetched",
            {
                "start_date": start_date,
                "end_date": end_date,
                "month_year": (_month_bounds(data.get("month_year")) or (None, None, None))[2],
                "expected": {**EXPECTED_HOURS, "total": EXPECTED_TOTAL},
                "rows": result,
                "qa_users": qa_users,
            },
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return api_response(500, f"Error listing QA tracker: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@qa_tracker_bp.route("/monthly", methods=["POST"])
def qa_tracker_monthly():
    data = request.get_json(silent=True) or {}
    logged_in_user_id, _, err = _require_user(data)
    if err:
        return err

    bounds = _month_bounds(data.get("month_year"))
    if not bounds:
        today = today_str()
        bounds = _month_bounds(today[:7])
    if not bounds:
        return api_response(400, "month_year is required (YYYY-MM or SEP2026)")
    start_date, end_date, month_label = bounds
    req_start = _parse_date(data.get("start_date"))
    req_end = _parse_date(data.get("end_date"))
    if req_start and req_start > start_date:
        start_date = req_start
    if req_end and req_end < end_date:
        end_date = req_end
    resolved = _resolve_report_range(start_date, end_date)
    if not resolved:
        return api_response(
            200,
            "QA tracker monthly fetched",
            {
                "month_year": month_label,
                "start_date": start_date,
                "end_date": end_date,
                "expected": {**EXPECTED_HOURS, "total": EXPECTED_TOTAL},
                "rows": [],
                "qa_users": [],
            },
        )
    start_date, end_date = resolved

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ctx = get_role_context(cursor, logged_in_user_id)
        role_name = ctx.get("user_role_name") or ""
        if not role_name:
            return api_response(404, "User not found")

        manager = _ctx_can_view_as_manager(ctx)
        requested = data.get("qa_user_id")
        where, params = _active_tracker_where(start_date, end_date)

        if manager:
            if requested not in (None, "", 0, "0"):
                where += " AND qwt.qa_user_id=%s"
                params.append(int(requested))
        else:
            where += " AND qwt.qa_user_id=%s"
            params.append(logged_in_user_id)

        _prepare_tracker_read(
            cursor, conn, manager, logged_in_user_id, requested, start_date, end_date
        )

        cursor.execute(
            f"""
            SELECT
                qwt.qa_user_id,
                qa.user_name AS qa_user_name,
                qwt.activity_type,
                qwt.project_id,
                p.project_name,
                qwt.task_id,
                t.task_name,
                SUM(qwt.hours) AS hours,
                SUM(CASE WHEN qwt.activity_type IN ('qc_tasks','rework_qc') THEN 1 ELSE 0 END) AS files,
                SUM(qwt.file_record_count) AS file_records,
                SUM(qwt.qc_generated_count) AS qc_records,
                COUNT(DISTINCT qwt.work_date) AS days_in_group
            FROM qa_work_tracker qwt
            LEFT JOIN tfs_user qa ON qa.user_id = qwt.qa_user_id
            LEFT JOIN project p ON p.project_id = qwt.project_id
            LEFT JOIN task t ON t.task_id = qwt.task_id
            WHERE {where}
            GROUP BY
                qwt.qa_user_id, qa.user_name, qwt.activity_type,
                qwt.project_id, p.project_name, qwt.task_id, t.task_name
            ORDER BY qa.user_name, p.project_name
            """,
            tuple(params),
        )
        raw = cursor.fetchall() or []

        users = {}
        for r in raw:
            qa_id = int(r.get("qa_user_id"))
            if qa_id not in users:
                users[qa_id] = {
                    "qa_user_id": qa_id,
                    "qa_user_name": r.get("qa_user_name"),
                    "month_year": month_label,
                    "qc_hours": 0.0,
                    "rework_hours": 0.0,
                    "feedback_hours": 0.0,
                    "reporting_hours": 0.0,
                    "total_hours": 0.0,
                    "qc_files": 0,
                    "rework_files": 0,
                    "qc_records": 0,
                    "file_records": 0,
                    "late_files": 0,
                    "days_worked": 0,
                    "expected_hours": 0.0,
                    "pending_hours": 0.0,
                    "projects": {},
                    "manual_entries": [],
                    "_dates": set(),
                }
            row = users[qa_id]
            activity = r.get("activity_type")
            hours = _round4(r.get("hours"))
            if activity == "qc_tasks":
                row["qc_hours"] = _round4(row["qc_hours"] + hours)
                row["qc_files"] += _int(r.get("files"))
            elif activity == "rework_qc":
                row["rework_hours"] = _round4(row["rework_hours"] + hours)
                row["rework_files"] += _int(r.get("files"))
            elif activity == "feedback":
                row["feedback_hours"] = _round4(row["feedback_hours"] + hours)
            elif activity == "reporting":
                row["reporting_hours"] = _round4(row["reporting_hours"] + hours)
            row["qc_records"] += _int(r.get("qc_records"))
            row["file_records"] += _int(r.get("file_records"))

            if activity in QC_ACTIVITIES and r.get("project_id") is not None:
                pk = (r.get("project_id"), r.get("task_id"))
                proj = row["projects"].setdefault(
                    pk,
                    {
                        "project_id": r.get("project_id"),
                        "project_name": r.get("project_name") or "—",
                        "task_id": r.get("task_id"),
                        "task_name": r.get("task_name") or "—",
                        "qc_hours": 0.0,
                        "rework_hours": 0.0,
                        "files": 0,
                        "file_records": 0,
                        "qc_records": 0,
                        "late_files": 0,
                    },
                )
                if activity == "qc_tasks":
                    proj["qc_hours"] = _round4(proj["qc_hours"] + hours)
                else:
                    proj["rework_hours"] = _round4(proj["rework_hours"] + hours)
                proj["files"] += _int(r.get("files"))
                proj["file_records"] += _int(r.get("file_records"))
                proj["qc_records"] += _int(r.get("qc_records"))

        for entry in _fetch_manual_detail_rows(cursor, where, params):
            qa_id = _int(entry.get("qa_user_id"))
            if qa_id in users:
                users[qa_id].setdefault("manual_entries", []).append(entry)

        cursor.execute(
            f"""
            SELECT qa_user_id, COUNT(DISTINCT work_date) AS days_worked
            FROM qa_work_tracker qwt
            WHERE {where}
            GROUP BY qa_user_id
            """,
            tuple(params),
        )
        days_map = {int(r["qa_user_id"]): _int(r.get("days_worked")) for r in (cursor.fetchall() or [])}

        result = []
        for row in users.values():
            days_worked = days_map.get(row["qa_user_id"], 0)
            row["days_worked"] = days_worked
            row["expected_hours"] = _round4(days_worked * EXPECTED_TOTAL)
            row["total_hours"] = _round4(
                row["qc_hours"] + row["rework_hours"] + row["feedback_hours"] + row["reporting_hours"]
            )
            row["pending_hours"] = _round4(row["expected_hours"] - row["total_hours"])
            row["projects"] = list(row["projects"].values())
            row.pop("_dates", None)
            if (
                row["total_hours"] == 0
                and row["qc_files"] == 0
                and row["rework_files"] == 0
            ):
                continue
            result.append(row)

        _annotate_late_counts(cursor, result, where, params, by_day=False)

        qa_users = []
        if manager:
            cursor.execute(
                """
                SELECT u.user_id, u.user_name
                FROM tfs_user u
                JOIN user_role r ON r.role_id = u.role_id
                WHERE u.is_active=1 AND u.is_delete=1
                  AND (LOWER(TRIM(r.role_name)) = 'qa' OR LOWER(TRIM(r.role_name)) LIKE '%qa%')
                ORDER BY u.user_name
                """
            )
            qa_users = cursor.fetchall() or []

        return api_response(
            200,
            "QA tracker monthly fetched",
            {
                "month_year": month_label,
                "start_date": start_date,
                "end_date": end_date,
                "expected_per_day": EXPECTED_TOTAL,
                "expected": {**EXPECTED_HOURS, "total": EXPECTED_TOTAL},
                "rows": result,
                "qa_users": qa_users,
            },
        )
    except Exception as e:
        return api_response(500, f"Error fetching QA monthly tracker: {str(e)}")
    finally:
        cursor.close()
        conn.close()


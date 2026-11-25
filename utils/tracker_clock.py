from __future__ import annotations

from datetime import datetime

from utils.response import api_response
from utils.time_ist import now_ist

CLOCK_SESSION_SQL = """
CREATE TABLE IF NOT EXISTS tracker_clock_session (
    user_id INT NOT NULL PRIMARY KEY,
    project_id INT NOT NULL,
    task_id INT NOT NULL,
    shift VARCHAR(16) NOT NULL,
    clock_in_at DATETIME NOT NULL,
    clock_out_at DATETIME NULL,
    worked_hours INT NULL,
    updated_at DATETIME NULL
)
"""

_clock_columns_ready = False

# Same IDs as QC: Training (7) and Sample (8) keep the old tracker (no clock).
CLOCK_EXEMPT_PROJECT_IDS = (7, 8)
CLOCK_EXEMPT_NAMES = frozenset({"training", "sample"})


def is_clock_exempt_project(project_id=None, project_name=None, cursor=None) -> bool:
    try:
        if int(project_id) in CLOCK_EXEMPT_PROJECT_IDS:
            return True
    except (TypeError, ValueError):
        pass
    name = (project_name or "").strip().lower()
    if not name and cursor and project_id:
        try:
            cursor.execute("SELECT project_name FROM project WHERE project_id=%s", (int(project_id),))
            row = cursor.fetchone() or {}
            name = str(row.get("project_name") or "").strip().lower()
        except Exception:
            name = ""
    return name in CLOCK_EXEMPT_NAMES


def ensure_clock_session_table(cursor) -> None:
    cursor.execute(CLOCK_SESSION_SQL)


def ensure_tracker_clock_columns(cursor) -> None:
    global _clock_columns_ready
    if _clock_columns_ready:
        return
    cursor.execute("SHOW COLUMNS FROM task_work_tracker LIKE 'clock_in_at'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE task_work_tracker ADD COLUMN clock_in_at DATETIME NULL")
    cursor.execute("SHOW COLUMNS FROM task_work_tracker LIKE 'clock_out_at'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE task_work_tracker ADD COLUMN clock_out_at DATETIME NULL")
    cursor.execute("SHOW COLUMNS FROM task_work_tracker LIKE 'worked_hours'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE task_work_tracker ADD COLUMN worked_hours INT NULL")
    _clock_columns_ready = True


def _naive(dt) -> datetime:
    if isinstance(dt, datetime):
        return dt.replace(tzinfo=None) if dt.tzinfo else dt
    return datetime.strptime(str(dt)[:19], "%Y-%m-%d %H:%M:%S")


def nearest_worked_hours(clock_in_at, clock_out_at) -> int:
    start = _naive(clock_in_at)
    end = _naive(clock_out_at)
    seconds = max(0, (end - start).total_seconds())
    minutes = seconds / 60.0
    hours = int((minutes + 30) // 60)
    return max(1, hours)


def session_row(cursor, user_id: int):
    ensure_clock_session_table(cursor)
    cursor.execute(
        """
        SELECT user_id, project_id, task_id, shift, clock_in_at, clock_out_at, worked_hours
        FROM tracker_clock_session
        WHERE user_id=%s
        """,
        (int(user_id),),
    )
    return cursor.fetchone()


def reject_if_clock_locked(cursor, user_id) -> tuple | None:
    """Block edit/delete of other trackers while clocked in. Submit (/tracker/add) clocks out itself."""
    if not user_id:
        return None
    try:
        from flask import request
        path = (request.path or "").replace("\\", "/").rstrip("/")
        if path.endswith("/tracker/add") or path.endswith("/add"):
            return None
    except Exception:
        pass
    row = session_row(cursor, int(user_id))
    if row and row.get("clock_in_at") and not row.get("clock_out_at"):
        return api_response(403, "Clock out of your current tracker session before doing anything else on Tracker")
    return None


def serialize_session(row) -> dict | None:
    if not row:
        return None

    def fmt(val):
        if val is None:
            return None
        if hasattr(val, "strftime"):
            return val.strftime("%Y-%m-%d %H:%M:%S")
        return str(val)[:19]

    return {
        "user_id": row.get("user_id"),
        "project_id": row.get("project_id"),
        "task_id": row.get("task_id"),
        "shift": row.get("shift"),
        "clock_in_at": fmt(row.get("clock_in_at")),
        "clock_out_at": fmt(row.get("clock_out_at")),
        "worked_hours": row.get("worked_hours"),
        "server_now": now_ist().strftime("%Y-%m-%d %H:%M:%S"),
        "is_clocked_in": bool(row.get("clock_in_at") and not row.get("clock_out_at")),
        "is_clocked_out": bool(row.get("clock_out_at")),
    }

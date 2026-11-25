from datetime import timedelta

from flask import Blueprint, current_app, make_response, request

from config import get_db_connection
from utils.response import api_response
from utils.roster_helpers import get_role_context, reject_if_operations, reject_if_read_only
from utils.tracker_clock import (
    ensure_clock_session_table,
    is_clock_exempt_project,
    nearest_worked_hours,
    serialize_session,
    session_row,
)
from utils.time_ist import now_ist

tracker_clock_bp = Blueprint("tracker_clock", __name__)


def _cors_preflight():
    resp = make_response("", 204)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    resp.headers["Access-Control-Max-Age"] = "86400"
    return resp


@tracker_clock_bp.after_request
def _clock_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return response


def _user_id(data):
    raw = data.get("logged_in_user_id") or data.get("user_id")
    if not raw:
        return None, api_response(400, "logged_in_user_id is required")
    try:
        return int(raw), None
    except (TypeError, ValueError):
        return None, api_response(400, "logged_in_user_id is required")


@tracker_clock_bp.route("/status", methods=["POST"])
def clock_status():
    data = request.get_json(silent=True) or {}
    user_id, err = _user_id(data)
    if err:
        return err
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ensure_clock_session_table(cursor)
        today = now_ist().strftime("%Y-%m-%d")
        cursor.execute(
            """
            SELECT date_time, updated_date
            FROM task_work_tracker
            WHERE user_id=%s AND is_active=1
              AND tracker_file IS NOT NULL AND TRIM(tracker_file) <> ''
              AND project_id NOT IN (7, 8)
              AND DATE(COALESCE(updated_date, date_time)) = %s
            """,
            (user_id, today),
        )
        file_at = []
        for row in cursor.fetchall() or []:
            stamp = row.get("updated_date") or row.get("date_time")
            if stamp:
                file_at.append(stamp.strftime("%Y-%m-%d %H:%M:%S") if hasattr(stamp, "strftime") else str(stamp)[:19])
        conn.commit()
        return api_response(200, "Clock session", {
            "session": serialize_session(session_row(cursor, user_id)),
            "file_at": file_at,
        })
    except Exception as exc:
        return api_response(500, f"Failed to load clock session: {exc}")
    finally:
        cursor.close()
        conn.close()


@tracker_clock_bp.route("/in", methods=["POST"])
def clock_in():
    data = request.get_json(silent=True) or {}
    user_id, err = _user_id(data)
    if err:
        return err
    try:
        project_id = int(data.get("project_id"))
        task_id = int(data.get("task_id"))
    except (TypeError, ValueError):
        return api_response(400, "Project and task are required before clock-in")
    shift = str(data.get("shift") or "DAY").strip().upper()
    if shift not in ("DAY", "NIGHT"):
        return api_response(400, "Shift must be DAY or NIGHT")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ctx = get_role_context(cursor, user_id)
        read_only_err = reject_if_read_only(ctx.get("user_role_name"), ctx.get("user_role_id"))
        if read_only_err:
            return read_only_err
        ops_err = reject_if_operations(ctx.get("user_role_name"), ctx.get("user_role_id"))
        if ops_err:
            return ops_err
        if is_clock_exempt_project(project_id=project_id, cursor=cursor):
            return api_response(400, "Clock-in is not used for Training and Sample. Add the tracker as usual.")
        ensure_clock_session_table(cursor)
        existing = session_row(cursor, user_id)
        if existing and existing.get("clock_in_at") and not existing.get("clock_out_at"):
            return api_response(400, "You are already clocked in", {"session": serialize_session(existing)})
        if existing and existing.get("clock_out_at"):
            return api_response(
                400,
                "Clocked-out session is waiting to be submitted. Submit that tracker first.",
                {"session": serialize_session(existing)},
            )
        cursor.execute("SELECT task_id FROM task WHERE task_id=%s", (task_id,))
        if not cursor.fetchone():
            return api_response(404, "Task not found")
        now = now_ist().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            INSERT INTO tracker_clock_session
            (user_id, project_id, task_id, shift, clock_in_at, clock_out_at, worked_hours, updated_at)
            VALUES (%s,%s,%s,%s,%s,NULL,NULL,%s)
            """,
            (user_id, project_id, task_id, shift, now, now),
        )
        conn.commit()
        return api_response(200, "Clocked in", {"session": serialize_session(session_row(cursor, user_id))})
    except Exception as exc:
        conn.rollback()
        return api_response(500, f"Failed to clock in: {exc}")
    finally:
        cursor.close()
        conn.close()


@tracker_clock_bp.route("/out", methods=["POST"])
def clock_out():
    data = request.get_json(silent=True) or {}
    user_id, err = _user_id(data)
    if err:
        return err
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ctx = get_role_context(cursor, user_id)
        read_only_err = reject_if_read_only(ctx.get("user_role_name"), ctx.get("user_role_id"))
        if read_only_err:
            return read_only_err
        ensure_clock_session_table(cursor)
        existing = session_row(cursor, user_id)
        if not existing or not existing.get("clock_in_at"):
            return api_response(400, "You are not clocked in")
        if existing.get("clock_out_at"):
            return api_response(200, "Already clocked out", {"session": serialize_session(existing)})
        now_s = now_ist().strftime("%Y-%m-%d %H:%M:%S")
        hours = nearest_worked_hours(existing["clock_in_at"], now_s)
        cursor.execute(
            """
            UPDATE tracker_clock_session
            SET clock_out_at=%s, worked_hours=%s, updated_at=%s
            WHERE user_id=%s
            """,
            (now_s, hours, now_s, user_id),
        )
        conn.commit()
        return api_response(200, "Clocked out", {"session": serialize_session(session_row(cursor, user_id))})
    except Exception as exc:
        conn.rollback()
        return api_response(500, f"Failed to clock out: {exc}")
    finally:
        cursor.close()
        conn.close()


@tracker_clock_bp.route("/test_elapsed", methods=["POST", "OPTIONS"])
def test_elapsed():
    """Local testing only (Flask debug). Backdates clock_in_at so hours can be tested without waiting."""
    if request.method == "OPTIONS":
        return _cors_preflight()
    if not current_app.debug:
        return api_response(404, "Not found")
    data = request.get_json(silent=True) or {}
    user_id, err = _user_id(data)
    if err:
        return err
    try:
        minutes = float(data.get("minutes") or 0)
    except (TypeError, ValueError):
        minutes = 0
    if minutes <= 0:
        return api_response(400, "minutes is required")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ensure_clock_session_table(cursor)
        existing = session_row(cursor, user_id)
        if not existing or not existing.get("clock_in_at") or existing.get("clock_out_at"):
            return api_response(400, "Clock in first, then jump the timer")
        start = now_ist() - timedelta(minutes=minutes)
        start_s = start.strftime("%Y-%m-%d %H:%M:%S")
        now_s = now_ist().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            UPDATE tracker_clock_session
            SET clock_in_at=%s, updated_at=%s
            WHERE user_id=%s
            """,
            (start_s, now_s, user_id),
        )
        conn.commit()
        return api_response(200, "Timer jumped for testing", {"session": serialize_session(session_row(cursor, user_id))})
    except Exception as exc:
        conn.rollback()
        return api_response(500, f"Failed to jump timer: {exc}")
    finally:
        cursor.close()
        conn.close()


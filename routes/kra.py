# routes/kra.py

from datetime import date

from flask import Blueprint, request, send_file

from config import get_db_connection
from utils.kra import (
    KRA_GO_LIVE_MONTH,
    build_kra_report,
    is_kra_month_allowed,
    kra_period_end,
    save_kra_notes,
)
from utils.kra_excel import build_kra_workbook
from utils.response import api_response
from utils.roster_helpers import (
    get_role_context,
    month_year_label,
    parse_month_year,
    require_logged_in_user,
    team_leader_scope_params,
    team_leader_scope_sql,
)
from utils.user_status import sql_listing_leaver_clause

kra_bp = Blueprint("kra", __name__)


def _logged_in(data):
    user_id, err = require_logged_in_user(data)
    if err:
        return None, api_response(err.get("status", 400), err.get("error", "Authentication required"))
    return user_id, None


def _month(data):
    raw = (data.get("month_year") or "").strip()
    if not raw:
        return None, None, None, api_response(400, "month_year is required (e.g. SEP2026)")
    try:
        year, month = parse_month_year(raw)
    except ValueError as exc:
        return None, None, None, api_response(400, str(exc))
    label = month_year_label(year, month)
    if not is_kra_month_allowed(label):
        return None, None, None, api_response(
            400,
            f"KRA is available from {KRA_GO_LIVE_MONTH} onwards",
        )
    return year, month, label, None


def _agent_role_id(cursor):
    cursor.execute(
        """
        SELECT role_id
        FROM user_role
        WHERE LOWER(TRIM(role_name)) = 'agent'
        LIMIT 1
        """
    )
    row = cursor.fetchone() or {}
    return row.get("role_id")


def _scope_clause(role_name: str, logged_in_user_id: int):
    role_name = (role_name or "").strip().lower()
    if role_name in ("admin", "super admin", "project manager"):
        return "", []
    if role_name == "agent":
        return " AND u.user_id = %s", [int(logged_in_user_id)]
    if role_name in ("assistant team leader", "team leader"):
        return f" AND {team_leader_scope_sql('u')}", team_leader_scope_params(logged_in_user_id)
    mid = str(int(logged_in_user_id))
    return (
        """
        AND (
            JSON_CONTAINS(u.project_manager_id, %s)
            OR JSON_CONTAINS(u.asst_manager_id, %s)
            OR JSON_CONTAINS(u.qa_id, %s)
            OR u.user_id = %s
        )
        """,
        [mid, mid, mid, int(logged_in_user_id)],
    )


def _can_view(cursor, actor_id: int, target_user_id: int) -> tuple[bool, str, bool]:
    ctx = get_role_context(cursor, int(actor_id))
    role_name = ctx.get("user_role_name") or ""
    if not role_name:
        return False, "", False
    agent_role_id = _agent_role_id(cursor)
    if not agent_role_id:
        return False, role_name, False
    clause, params = _scope_clause(role_name, actor_id)
    cursor.execute(
        f"""
        SELECT u.user_id
        FROM tfs_user u
        WHERE u.is_delete = 1
          AND u.role_id = %s
          AND u.user_id = %s
          AND {sql_listing_leaver_clause("u", months=3)}
          {clause}
        LIMIT 1
        """,
        tuple([agent_role_id, int(target_user_id), *params]),
    )
    allowed = cursor.fetchone() is not None
    allow_policy = role_name != "agent"
    return allowed, role_name, allow_policy


@kra_bp.route("/users", methods=["POST"])
def list_kra_users():
    data = request.get_json(silent=True) or {}
    actor_id, err = _logged_in(data)
    if err:
        return err

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ctx = get_role_context(cursor, actor_id)
        role_name = ctx.get("user_role_name") or ""
        if not role_name:
            return api_response(404, "User not found")
        agent_role_id = _agent_role_id(cursor)
        if not agent_role_id:
            return api_response(500, "Agent role not found")
        clause, params = _scope_clause(role_name, actor_id)
        cursor.execute(
            f"""
            SELECT u.user_id, u.user_name, t.team_name
            FROM tfs_user u
            LEFT JOIN team t ON t.team_id = u.team_id
            WHERE u.is_delete = 1
              AND u.role_id = %s
              AND {sql_listing_leaver_clause("u", months=3)}
              {clause}
            ORDER BY
              CASE WHEN t.team_name IS NULL OR TRIM(t.team_name) = '' THEN 1 ELSE 0 END,
              t.team_name,
              u.user_name
            """,
            tuple([agent_role_id, *params]),
        )
        rows = cursor.fetchall() or []
        return api_response(200, "Users fetched", {
            "users": rows,
            "go_live_month": KRA_GO_LIVE_MONTH,
        })
    except Exception as exc:
        return api_response(500, f"Could not list users: {exc}")
    finally:
        cursor.close()
        conn.close()


@kra_bp.route("/report", methods=["POST"])
def kra_report():
    data = request.get_json(silent=True) or {}
    actor_id, err = _logged_in(data)
    if err:
        return err
    year, month, month_year, err = _month(data)
    if err:
        return err
    target_id = data.get("user_id") or actor_id

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        allowed, _role_name, _allow_policy = _can_view(cursor, actor_id, int(target_id))
        if not allowed:
            return api_response(403, "You cannot view this agent's KRA")
        report = build_kra_report(cursor, int(target_id), year, month, month_year)
        return api_response(200, "KRA report", report)
    except Exception as exc:
        return api_response(500, f"Could not build KRA: {exc}")
    finally:
        cursor.close()
        conn.close()


@kra_bp.route("/save_notes", methods=["POST"])
def kra_save_notes():
    data = request.get_json(silent=True) or {}
    actor_id, err = _logged_in(data)
    if err:
        return err
    year, month, month_year, err = _month(data)
    if err:
        return err
    target_id = data.get("user_id") or actor_id

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        allowed, _role_name, _allow_policy = _can_view(cursor, actor_id, int(target_id))
        if not allowed:
            return api_response(403, "You cannot update notes for this agent's KRA")
        period_start = date(year, month, 1)
        period_end = kra_period_end(year, month)
        save_kra_notes(
            cursor,
            actor_id,
            int(target_id),
            data.get("notes") or [],
            period_start=period_start,
            period_end=period_end,
        )
        conn.commit()
        report = build_kra_report(cursor, int(target_id), year, month, month_year)
        return api_response(200, "Notes saved", report)
    except Exception as exc:
        conn.rollback()
        return api_response(500, f"Could not save notes: {exc}")
    finally:
        cursor.close()
        conn.close()


@kra_bp.route("/export", methods=["POST"])
def kra_export():
    data = request.get_json(silent=True) or {}
    actor_id, err = _logged_in(data)
    if err:
        return err
    year, month, month_year, err = _month(data)
    if err:
        return err
    target_id = data.get("user_id") or actor_id

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        allowed, role_name, _allow_policy = _can_view(cursor, actor_id, int(target_id))
        if not allowed:
            return api_response(403, "You cannot export this agent's KRA")
        
        # Log diagnostic info
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"KRA Export - Actor: {actor_id}, Role: {role_name}, Target: {target_id}, Month: {month_year}")
        
        report = build_kra_report(cursor, int(target_id), year, month, month_year)
        
        # Log report structure
        logger.info(f"KRA Report - Days count: {len(report.get('days', []))}, Counts: {report.get('counts', {})}")
        
        output, filename = build_kra_workbook(report)
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as exc:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"KRA Export error: {str(exc)}", exc_info=True)
        return api_response(500, f"Could not export KRA: {exc}")
    finally:
        cursor.close()
        conn.close()

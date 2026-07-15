from flask import Blueprint, request, jsonify
from datetime import datetime
from config import get_db_connection

qc_bp = Blueprint("qc", __name__)

QC_DATE_COL = "date"  # change if your column name is different

def response(status, message, data=None, code=200):
    return jsonify({"status": status, "message": message, "data": data}), code

def get_user_role(cursor, user_id: int) -> str | None:
    """Get the role name for a given user_id"""
    cursor.execute("""
        SELECT r.role_name
        FROM tfs_user u
        JOIN user_role r ON r.role_id = u.role_id
        WHERE u.user_id=%s AND u.is_active=1 AND u.is_delete=1
    """, (user_id,))
    row = cursor.fetchone()
    if not row:
        return None
    return (row.get("role_name") or "").strip().lower()

# ---------------------------
# DAILY ASSIGNED HOURS (cron + manual)
# ---------------------------
@qc_bp.route("/assign-daily-hours", methods=["GET", "POST"])
def assign_daily_hours():
    """
    Scheduled job endpoint.
    - Local/crontab: assign_daily_hours.py → POST
    - Vercel Cron: GET /qc/assign-daily-hours (Vercel always uses GET)

    Assigns hours per agent from roster Working/Half + user tenure.
    Optional env CRON_SECRET: require Authorization: Bearer <secret>.
    """
    import os
    from utils.roster_helpers import assigned_hours_for_roster_day, month_year_label

    cron_secret = (os.getenv("CRON_SECRET") or "").strip()
    if cron_secret:
        auth = (request.headers.get("Authorization") or "").strip()
        if auth != f"Bearer {cron_secret}":
            return response(False, "Unauthorized", None, 401)

    now = datetime.now()

    # Developer fix: Set specific date if needed
    # Uncomment and change the date below to assign hours for a specific date
    # if now.strftime("%Y-%m-%d") == "2025-04-15":
    # now = datetime.strptime("2026-04-20", "%Y-%m-%d")
    # print("Now:",now)

    today = now.date()
    today_str = today.strftime("%Y-%m-%d")
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    month_year = month_year_label(today.year, today.month)

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        # Active agents + today's roster day (if any)
        cur.execute(
            """
            SELECT
                u.user_id,
                u.user_tenure,
                rd.day_type,
                rd.working_type,
                rd.roster_day_id,
                COALESCE(rl.is_half_day, 0) AS is_half_day
            FROM tfs_user u
            JOIN user_role ur ON u.role_id = ur.role_id
            LEFT JOIN roster_month rm
                ON rm.user_id = u.user_id
               AND rm.is_active = 1
               AND UPPER(rm.month_year) = UPPER(%s)
            LEFT JOIN roster_day rd
                ON rd.roster_month_id = rm.roster_month_id
               AND rd.is_active = 1
               AND DATE(rd.roster_date) = %s
            LEFT JOIN roster_leave rl
                ON rl.leave_id = rd.leave_id
               AND rl.is_active = 1
            WHERE LOWER(TRIM(ur.role_name)) = 'agent'
              AND u.is_active = 1
              AND u.is_delete = 1
            """,
            (month_year, today_str),
        )
        agent_rows = cur.fetchall() or []

        if not agent_rows:
            return response(True, "No active agents found to assign hours.", None, 200)

        sql = f"""
            INSERT INTO temp_qc (user_id, assigned_hours, {QC_DATE_COL}, updated_date)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                assigned_hours = VALUES(assigned_hours),
                updated_date = VALUES(updated_date)
        """

        data_to_insert = []
        summary = {"full": 0, "half": 0, "zero": 0}
        for row in agent_rows:
            is_half_leave = bool(int(row.get("is_half_day") or 0))
            hours = assigned_hours_for_roster_day(
                row.get("user_tenure"),
                day_type=row.get("day_type"),
                working_type=row.get("working_type"),
                has_roster_day=row.get("roster_day_id") is not None,
                is_half_leave=is_half_leave,
            )
            data_to_insert.append((int(row["user_id"]), hours, today_str, now_str))
            if hours <= 0:
                summary["zero"] += 1
            elif (row.get("working_type") or "Full") == "Half" or is_half_leave:
                summary["half"] += 1
            else:
                summary["full"] += 1

        cur.executemany(sql, data_to_insert)
        conn.commit()

        return response(
            True,
            (
                f"Assigned roster/tenure-based hours to {len(data_to_insert)} agents for {today_str} "
                f"(full={summary['full']}, half={summary['half']}, off/leave={summary['zero']})."
            ),
            {
                "date": today_str,
                "month_year": month_year,
                "assigned_count": len(data_to_insert),
                **summary,
            },
            200,
        )

    except Exception as e:
        if conn:
            conn.rollback()
        return response(False, f"An error occurred: {str(e)}", None, 500)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# ---------------------------
# UPSERT (EXISTING)
# ---------------------------
@qc_bp.route("/temp-qc", methods=["POST"])
def upsert_temp_qc():
    data = request.get_json(silent=True) or {}

    user_id = data.get("user_id")
    qc_date = (data.get("date") or "").strip()  # YYYY-MM-DD
    logged_in_user_id = data.get("logged_in_user_id")

    # OPTIONAL fields (can come separately)
    qc_score = data.get("qc_score")            # can be missing
    assigned_hours = data.get("assigned_hours") # can be missing

    if not user_id:
        return response(False, "user_id is required", None, 400)

    if not qc_date:
        return response(False, "date is required (YYYY-MM-DD)", None, 400)

    if not logged_in_user_id:
        return response(False, "logged_in_user_id is required", None, 400)

    try:
        datetime.strptime(qc_date, "%Y-%m-%d")
    except ValueError:
        return response(False, "Invalid date format. Use YYYY-MM-DD", None, 400)

    # At least one of qc_score/assigned_hours should be provided
    if qc_score is None and assigned_hours is None:
        return response(False, "Provide qc_score or assigned_hours (at least one).", None, 400)

    # Permission check: Only Admin, Super Admin, Assistant Manager and Project Manager can update assigned_hours
    if assigned_hours is not None:
        conn = None
        cur = None
        try:
            conn = get_db_connection()
            cur = conn.cursor(dictionary=True)
            
            user_role = get_user_role(cur, int(logged_in_user_id))
            
            # Allowed roles for assigned_hours: admin, super admin, project manager, assistant manager
            allowed_roles = ["admin", "super admin", "project manager", "assistant manager"]
            
            if user_role not in allowed_roles:
                return response(False, "Permission denied. Only Admin, Super Admin, Assistant Manager and Project Manager can update assigned hours.", None, 403)
                
        except Exception as e:
            if conn:
                conn.rollback()
            return response(False, f"Permission check failed: {str(e)}", None, 500)
        finally:
            try:
                if cur: cur.close()
                if conn: conn.close()
            except:
                pass

    updated_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        sql = f"""
            INSERT INTO temp_qc (user_id, qc_score, assigned_hours, {QC_DATE_COL}, updated_date)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                qc_score = COALESCE(VALUES(qc_score), qc_score),
                assigned_hours = COALESCE(VALUES(assigned_hours), assigned_hours),
                updated_date = VALUES(updated_date)
        """

        cur.execute(sql, (user_id, qc_score, assigned_hours, qc_date, updated_date))
        conn.commit()

        return response(True, "QC saved successfully", {"user_id": user_id, "date": qc_date}, 200)

    except Exception as e:
        if conn:
            conn.rollback()
        return response(False, f"QC save failed: {str(e)}", None, 500)

    finally:
        try:
            if cur: cur.close()
            if conn: conn.close()
        except:
            pass
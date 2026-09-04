# routes/user_monthly_report.py

from flask import Blueprint, request
from config import get_db_connection
from utils.response import api_response
from utils.qc_auto_score import AUTO_QC_DAYS_WITHOUT_EXISTING_SCORE_SQL
from utils.time_ist import now_str
from datetime import datetime, timedelta

user_monthly_report_bp = Blueprint("user_monthly_report", __name__)

# task_work_tracker.date_time is TEXT like "YYYY-MM-DD HH:MM:SS"
TRACKER_DT = "CAST(twt.date_time AS DATETIME)"
TRACKER_YEAR_MONTH = f"(YEAR({TRACKER_DT})*100 + MONTH({TRACKER_DT}))"


def month_year_to_yyyymm_sql(month_year_col: str) -> str:
    return f"""
    CAST(
        CONCAT(
            RIGHT({month_year_col},4),
            LPAD(
                CASE LEFT(UPPER({month_year_col}),3)
                    WHEN 'JAN' THEN 1
                    WHEN 'FEB' THEN 2
                    WHEN 'MAR' THEN 3
                    WHEN 'APR' THEN 4
                    WHEN 'MAY' THEN 5
                    WHEN 'JUN' THEN 6
                    WHEN 'JUL' THEN 7
                    WHEN 'AUG' THEN 8
                    WHEN 'SEP' THEN 9
                    WHEN 'OCT' THEN 10
                    WHEN 'NOV' THEN 11
                    WHEN 'DEC' THEN 12
                END,
                2,
                '0'
            )
        ) AS UNSIGNED
    )
    """


# ---------------------------
# Single helper (role_name + agent_role_id)
# ---------------------------
def get_role_context(cursor, user_id: int) -> dict:
    """
    Returns:
      {
        "user_role_id": int|None,
        "user_role_name": str,
        "agent_role_id": int|None
      }
    """
    cursor.execute(
        """
        SELECT
            u.role_id AS user_role_id,
            r.role_name AS user_role_name,
            (
                SELECT ur2.role_id
                FROM user_role ur2
                WHERE LOWER(TRIM(ur2.role_name)) = 'agent'
                LIMIT 1
            ) AS agent_role_id
        FROM tfs_user u
        JOIN user_role r ON r.role_id = u.role_id
        WHERE u.user_id=%s AND u.is_active=1 AND u.is_delete=1
        """,
        (int(user_id),),
    )
    row = cursor.fetchone() or {}
    return {
        "user_role_id": row.get("user_role_id"),
        "user_role_name": (row.get("user_role_name") or "").strip().lower(),
        "agent_role_id": row.get("agent_role_id"),
    }


# ---------------------------
# LIST USERS (for user monthly tracker page)
# - For current month: returns all active users (so managers can add goals)
# - For past months: returns users who have monthly targets for that month
# ---------------------------
@user_monthly_report_bp.route("/list_users", methods=["POST"])
def list_users_for_monthly_tracker():
    data = request.get_json(silent=True) or {}

    logged_in_user_id = data.get("logged_in_user_id")
    month_year = (data.get("month_year") or "").strip()  # OPTIONAL (MonYYYY)
    filter_team_id = data.get("team_id")  # OPTIONAL

    if not logged_in_user_id:
        return api_response(400, "logged_in_user_id is required", None)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        ctx = get_role_context(cursor, int(logged_in_user_id))
        my_role_name = (ctx.get("user_role_name") or "").lower()
        agent_role_id = ctx.get("agent_role_id")

        if not agent_role_id:
            return api_response(500, "Agent role not found in user_role table", None)
        
        # Determine if requested month is current month
        is_current_month = False
        if month_year:
            dt = datetime.strptime(month_year, "%b%Y")
            now = datetime.now()
            is_current_month = (dt.month == now.month and dt.year == now.year)
        else:
            is_current_month = True  # Default to current month

        # ---------------- Base WHERE: only agent rows ----------------
        if is_current_month:
            # For current month: show only active users
            user_where = """
                WHERE u.is_delete=1
                AND u.is_active=1
                AND u.role_id=%s
            """
        else:
            # For past months: show users based on tracker data (no is_active check)
            user_where = """
                WHERE u.is_delete=1
                AND u.role_id=%s
            """

        user_params = [agent_role_id]

        if filter_team_id:
            user_where += " AND u.team_id=%s"
            user_params.append(int(filter_team_id))

        if my_role_name in ("admin", "super admin", "project manager"):
            pass
        elif my_role_name == "agent":
            user_where += " AND u.user_id=%s"
            user_params.append(int(logged_in_user_id))
        else:
            mid = str(logged_in_user_id)
            user_where += """
                AND (
                    JSON_CONTAINS(u.project_manager_id, %s)
                    OR JSON_CONTAINS(u.asst_manager_id, %s)
                    OR JSON_CONTAINS(u.qa_id, %s)
                )
            """
            user_params.extend([str(mid), str(mid), str(mid)])

        # ---------------- Joins: based on current vs past month ----------------
        if month_year and not is_current_month:
            # Past month: INNER JOIN with user_monthly_tracker to show only users with targets
            umt_join = """
                INNER JOIN user_monthly_tracker umt
                ON umt.user_id = u.user_id
                AND umt.is_active=1
                AND umt.month_year=%s
            """
            final_params = [month_year]
        else:
            # Current month or no month specified: no tracker join needed
            umt_join = ""
            final_params = []

        final_params.extend(user_params)

        # ---------------- Main query ----------------
        query = f"""
            SELECT
                u.user_id,
                u.user_name,
                t.team_name
            FROM tfs_user u
            LEFT JOIN team t ON u.team_id = t.team_id
            {umt_join}
            {user_where}
            GROUP BY
                u.user_id,
                u.user_name,
                t.team_name
            ORDER BY
              CASE WHEN t.team_name IS NULL OR TRIM(t.team_name) = '' THEN 1 ELSE 0 END,
              t.team_name ASC,
              CASE
                WHEN LOWER(TRIM(u.user_name)) = LOWER(TRIM(IFNULL(t.team_name, ''))) THEN 0
                ELSE 1
              END,
              u.user_name ASC
        """

        cursor.execute(query, tuple(final_params))
        rows = cursor.fetchall()

        return api_response(200, "Users fetched successfully", rows)

    except Exception as e:
        return api_response(500, f"List users failed: {str(e)}", None)

    finally:
        cursor.close()
        conn.close()


# ---------------------------
# LIST
# Changes:
# - month_year optional: if missing -> default current month (MONYYYY) so pending_days works
# - only agent rows (managers/qa won't appear as rows)
# - monthly_total_target = monthly_target + extra_assigned_hours
# - pending_days = working_days(from UMT) - distinct worked days till today (month-wise)
# - do NOT return working_days or working_days_till_today separately
# - Show users based on monthly targets availability for the month
# - When month_year provided: only show users who have monthly targets for that month
# - Deactivated users still appear if they have monthly targets for the selected month
# - user_monthly_tracker is INNER JOIN (required) - only users with monthly targets appear
# ---------------------------
@user_monthly_report_bp.route("/list", methods=["POST"])
def list_user_monthly_targets():
    data = request.get_json(silent=True) or {}

    logged_in_user_id = data.get("logged_in_user_id")
    month_year = (data.get("month_year") or "").strip()  # OPTIONAL (MonYYYY)
    filter_user_id = data.get("user_id")  # OPTIONAL
    filter_team_id = data.get("team_id")  # OPTIONAL

    if not logged_in_user_id:
        return api_response(400, "logged_in_user_id is required", None)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        ctx = get_role_context(cursor, int(logged_in_user_id))
        my_role_name = (ctx.get("user_role_name") or "").lower()
        agent_role_id = ctx.get("agent_role_id")

        if not agent_role_id:
            return api_response(500, "Agent role not found in user_role table", None)
        
        if month_year:
            dt = datetime.strptime(month_year, "%b%Y")  # Mar2026
            month_start = dt.replace(day=1)
        else:
            now = datetime.now()
            month_start = now.replace(day=1)

        month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(seconds=1)

        month_start_str = month_start.strftime("%Y-%m-%d %H:%M:%S")
        month_end_str = month_end.strftime("%Y-%m-%d %H:%M:%S")

        # ---------------- Base WHERE: only agent rows ----------------
        # Remove is_active check to show deactivated users if they have tracker data
        user_where = """
            WHERE u.is_delete=1
            AND u.role_id=%s
        """

        user_params = [agent_role_id]

        if filter_user_id:
            user_where += " AND u.user_id=%s"
            user_params.append(int(filter_user_id))

        if filter_team_id:
            user_where += " AND u.team_id=%s"
            user_params.append(int(filter_team_id))

        if my_role_name in ("admin", "super admin", "project manager"):
            pass
        elif my_role_name == "agent":
            user_where += " AND u.user_id=%s"
            user_params.append(int(logged_in_user_id))
        else:
            mid = str(logged_in_user_id)
            user_where += """
                AND (
                    JSON_CONTAINS(u.project_manager_id, %s)
                    OR JSON_CONTAINS(u.asst_manager_id, %s)
                    OR JSON_CONTAINS(u.qa_id, %s)
                )
            """

            user_params.extend([str(mid), str(mid), str(mid)])

        # ---------------- Joins: month_year optional ----------------
        # temp_qc.date is TEXT 'YYYY-MM-DD'
        if month_year:
            # Use INNER JOIN with user_monthly_tracker to get users who have monthly targets for this month
            umt_join = """
                INNER JOIN user_monthly_tracker umt
                ON umt.user_id = u.user_id
                AND umt.is_active=1
                AND umt.month_year=%s
            """

            twt_join = f"""
                LEFT JOIN task_work_tracker twt
                ON twt.user_id = u.user_id
                AND twt.is_active=1
                AND {TRACKER_YEAR_MONTH}=%s
            """

            qc_join = f"""
                LEFT JOIN (
                    SELECT
                        x.user_id,
                        ROUND(AVG(x.daily_qc_avg),2) AS avg_qc_score,
                        COUNT(*) AS qc_days_count
                    FROM
                    (
                        -- OLD SYSTEM (temp_qc already has one record/day)
                        SELECT
                            tq.user_id,
                            tq.date AS qc_date,
                            tq.qc_score AS daily_qc_avg
                        FROM temp_qc tq
                        WHERE tq.qc_score IS NOT NULL

                        UNION ALL

                        -- NEW SYSTEM (many files/day)
                        SELECT
                            qr.agent_id AS user_id,
                            DATE(qr.date_of_file_submission) AS qc_date,
                            ROUND(AVG(qr.qc_score),2) AS daily_qc_avg
                        FROM qc_records qr
                        WHERE qr.qc_score IS NOT NULL
                        GROUP BY
                            qr.agent_id,
                            DATE(qr.date_of_file_submission)

                        UNION ALL

                        {AUTO_QC_DAYS_WITHOUT_EXISTING_SCORE_SQL}

                    ) x

                    WHERE DATE_FORMAT(
                            STR_TO_DATE(x.qc_date,'%Y-%m-%d'),
                            '%Y%m'
                        )
                        = %s

                    GROUP BY x.user_id

                ) qc
                ON qc.user_id=u.user_id
            """
        else:
            umt_join = """
                LEFT JOIN user_monthly_tracker umt
                ON umt.user_id=u.user_id
                AND umt.is_active=1
            """

            twt_join = """
                LEFT JOIN task_work_tracker twt
                ON twt.user_id=u.user_id
                AND twt.is_active=1
            """

            qc_join = f"""
                LEFT JOIN (
                    SELECT
                        x.user_id,
                        ROUND(AVG(x.daily_qc_avg),2) AS avg_qc_score,
                        COUNT(*) AS qc_days_count
                    FROM
                    (
                        -- OLD QC system
                        SELECT
                            tq.user_id,
                            tq.date AS qc_date,
                            tq.qc_score AS daily_qc_avg
                        FROM temp_qc tq
                        WHERE tq.qc_score IS NOT NULL

                        UNION ALL

                        -- NEW QC system
                        SELECT
                            qr.agent_id AS user_id,
                            DATE(qr.date_of_file_submission) AS qc_date,
                            ROUND(AVG(qr.qc_score),2) AS daily_qc_avg
                        FROM qc_records qr
                        WHERE qr.qc_score IS NOT NULL
                        GROUP BY
                            qr.agent_id,
                            DATE(qr.date_of_file_submission)

                        UNION ALL

                        {AUTO_QC_DAYS_WITHOUT_EXISTING_SCORE_SQL}

                    ) x
                    GROUP BY x.user_id
                ) qc
                ON qc.user_id=u.user_id
            """

        # ---------------- Main query ----------------
        # Use COALESCE for month_year only when month_year is provided
        month_year_coalesce = f"COALESCE(umt.month_year, '{month_year}')" if month_year else "umt.month_year"
        
        query = f"""
            SELECT
                u.user_id,
                u.user_name,
                t.team_name,
                umt.user_monthly_tracker_id,
                {month_year_coalesce} AS month_year,
                umt.working_days,
                COALESCE(CAST(umt.monthly_target AS DECIMAL(10,2)), 0) AS monthly_target,
                COALESCE(umt.extra_assigned_hours, 0) AS extra_assigned_hours,
                (
                    COALESCE(CAST(umt.monthly_target AS DECIMAL(10,2)), 0)
                    + COALESCE(umt.extra_assigned_hours, 0)
                ) AS monthly_total_target,

                COALESCE(SUM(COALESCE(twt.production, 0) / NULLIF(twt.tenure_target, 0)), 0) AS total_billable_hours,
                COALESCE(SUM(twt.production), 0) AS total_production,
                COUNT(twt.tracker_id) AS tracker_rows,

                -- QC monthly avg and qc-days count
                qc.avg_qc_score AS avg_qc_score,
                COALESCE(qc.qc_days_count, 0) AS qc_days_count,

                (
                    COALESCE(CAST(umt.monthly_target AS DECIMAL(10,2)), 0)
                    + COALESCE(umt.extra_assigned_hours, 0)
                ) - COALESCE(SUM(COALESCE(twt.production, 0) / NULLIF(twt.tenure_target, 0)), 0) AS pending_target
            FROM tfs_user u
            LEFT JOIN team t ON u.team_id = t.team_id
            {umt_join}
            {twt_join}
            {qc_join}
            {user_where}
            GROUP BY
                u.user_id,
                u.user_name,
                t.team_name,
                umt.user_monthly_tracker_id,
                umt.month_year,
                umt.working_days,
                umt.monthly_target,
                umt.extra_assigned_hours,
                qc.avg_qc_score,
                qc.qc_days_count
            ORDER BY
              CASE WHEN t.team_name IS NULL OR TRIM(t.team_name) = '' THEN 1 ELSE 0 END,
              t.team_name ASC,
              CASE
                WHEN LOWER(TRIM(u.user_name)) = LOWER(TRIM(IFNULL(t.team_name, ''))) THEN 0
                ELSE 1
              END,
              u.user_name ASC
        """

        # Params order:
        # if month_year: umt_join(%s), twt_join(%s), qc_join(%s), then user_where params
        if month_year:

            month_dt = datetime.strptime(month_year, "%b%Y")
            yyyymm = month_dt.strftime("%Y%m")

            final_params = [
                month_year,  # umt
                yyyymm,      # twt
                yyyymm       # qc
            ]
        else:
            final_params=[]

        final_params.extend(user_params)
        print(f"DEBUG: Final params: {final_params}")

        cursor.execute(query, tuple(final_params))
        rows = cursor.fetchall()

        return api_response(200, "User monthly targets fetched successfully", rows)

    except Exception as e:
        return api_response(500, f"List failed: {str(e)}", None)

    finally:
        cursor.close()
        conn.close()

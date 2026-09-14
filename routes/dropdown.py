from flask import Blueprint, request
from utils.response import api_response
from config import get_db_connection
from datetime import datetime, timedelta
from utils.user_status import (
    resolve_dropdown_period_start,
    sql_listing_leaver_clause,
    sql_visible_user_clause,
)

dropdown_bp = Blueprint("dropdown", __name__)

ROLE_BASED_USER_DROPDOWNS = (
    "super admin",
    "admin",
    "project manager",
    "assistant manager",
    "assistant team leader",
    "team leader",  # legacy alias → treated as assistant team leader
    "qa",
    "agent"
)

# These role dropdowns list only active users (no leaver visibility window).
# Assistant Manager keeps leaver visibility so assignment stays possible
# when current AMs were recently deactivated (Reporting To still hides inactive names).
ACTIVE_ONLY_USER_DROPDOWNS = (
    "super admin",
    "admin",
    "project manager",
    "assistant team leader",
    "team leader",
)

def get_user_role(cursor, user_id: int) -> str | None:
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


def multi_id_match_sql(col: str) -> str:
    # supports: 78 / 78,81 / [78] / [78,81] / ["78","81"] / spaces
    cleaned = f"REPLACE(REPLACE(REPLACE(REPLACE({col},'[',''),']',''),'\"',''),' ','')"
    return f"({col} = %s OR FIND_IN_SET(%s, {cleaned}) > 0)"


# ---------------- GET DROPDOWN DATA ---------------- #
@dropdown_bp.route("/get", methods=["POST"])
def get():
    data = request.get_json()
    if not data or "dropdown_type" not in data:
        return api_response(400, "dropdown_type is required")

    dropdown_type = (data["dropdown_type"] or "").strip().lower()
    if dropdown_type == "team leader":
        dropdown_type = "assistant team leader"

    # Agent lists (no period): rolling 3-month leaver window.
    # With date_from / month_year: period-based (past-month history).
    period_start = resolve_dropdown_period_start(data)
    has_period = bool(
        data.get("date_from")
        or data.get("start_date")
        or data.get("from_date")
        or data.get("month_year")
    )
    if has_period:
        visible_users_sql = sql_visible_user_clause("u")
        visible_users_params: list = [period_start]
    else:
        visible_users_sql = sql_listing_leaver_clause("u", months=3)
        visible_users_params = []

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # -------------------- DESIGNATIONS -------------------- #
        if dropdown_type == "designations":
            query = f"""
                SELECT designation_id, designation AS label
                FROM user_designation
                WHERE is_active = 1
                ORDER BY designation
            """
            params = []

            cursor.execute(query, params)
            result = cursor.fetchall()

            for item in result:
                if item.get("label"):
                    item["label"] = item["label"].title()

            return api_response(200, "Dropdown data fetched successfully", result)

        # -------------------- USER ROLES -------------------- #
        if dropdown_type == "user roles":
            query = """
                SELECT role_id, role_name AS label
                FROM user_role
                WHERE is_active = 1
                ORDER BY role_name
            """
            params = []

            cursor.execute(query, params)
            result = cursor.fetchall()

            for item in result:
                if item.get("label"):
                    item["label"] = item["label"].title()

            return api_response(200, "Dropdown data fetched successfully", result)

        # -------------------- TEAMS -------------------- #
        if dropdown_type == "teams":
            query = """
                SELECT team_id, team_name AS label
                FROM team
                WHERE is_active = 1
                ORDER BY team_name
            """
            params = []

            cursor.execute(query, params)
            result = cursor.fetchall()

            for item in result:
                if item.get("label"):
                    item["label"] = item["label"].title()

            return api_response(200, "Dropdown data fetched successfully", result)

        # -------------------- PROJECT CATEGORIES -------------------- #
        if dropdown_type == "project categories":
            query = """
                SELECT project_category_id, project_category_name AS label
                FROM project_category
                WHERE is_active = 1
                ORDER BY project_category_name
            """
            cursor.execute(query)
            result = cursor.fetchall()

            for item in result:
                if item.get("label"):
                    item["label"] = item["label"].title()

            return api_response(200, "Dropdown data fetched successfully", result)

        # -------------------- AFD -------------------- #
        if dropdown_type == "afd":
            query = """
                SELECT afd_id, afd_name AS label
                FROM afd
                WHERE is_active = 1
                ORDER BY afd_name
            """
            cursor.execute(query)
            result = cursor.fetchall()

            for item in result:
                if item.get("label"):
                    item["label"] = item["label"].title()

            return api_response(200, "Dropdown data fetched successfully", result)

        # -------------------- ROLE-BASED USER LIST -------------------- #
        if dropdown_type in ROLE_BASED_USER_DROPDOWNS:
            project_id = data.get("project_id")
            if dropdown_type == "agent" and project_id:
                # Only return agents assigned to this project (robust for all formats)
                v = str(project_id)
                query = f"""
                    SELECT
                        u.user_id,
                        u.user_name AS label,
                        u.user_tenure
                    FROM tfs_user u
                    JOIN user_role r ON r.role_id = u.role_id
                    JOIN project p ON p.project_id = %s
                    WHERE u.is_delete = 1
                      AND r.is_active = 1
                      AND LOWER(r.role_name) = %s
                      AND {visible_users_sql}
                      AND (
                        FIND_IN_SET(CAST(u.user_id AS CHAR), REPLACE(REPLACE(REPLACE(REPLACE(p.project_team_id,'[',''),']',''), '"', ''),' ','')) > 0
                      )
                    ORDER BY u.user_name
                """
                params = (project_id, dropdown_type, *visible_users_params)
                cursor.execute(query, params)
                result = cursor.fetchall()
                for item in result:
                    if item.get("label"):
                        item["label"] = item["label"].title()
                return api_response(200, "Dropdown data fetched successfully", result)
            elif dropdown_type == "assistant manager" and project_id:
                # Only return assistant managers assigned to this project (active only)
                query = f"""
                    SELECT
                        u.user_id,
                        u.user_name AS label
                    FROM tfs_user u
                    JOIN user_role r ON r.role_id = u.role_id
                    JOIN project p ON p.project_id = %s
                    WHERE u.is_delete = 1
                      AND r.is_active = 1
                      AND LOWER(r.role_name) = %s
                      AND u.is_active = 1
                      AND (
                        FIND_IN_SET(CAST(u.user_id AS CHAR), REPLACE(REPLACE(REPLACE(REPLACE(p.asst_project_manager_id,'[',''),']',''), '"', ''),' ','')) > 0
                      )
                    ORDER BY u.user_name
                """
                params = (project_id, dropdown_type)
                cursor.execute(query, params)
                result = cursor.fetchall()
                for item in result:
                    if item.get("label"):
                        item["label"] = item["label"].title()
                return api_response(200, "Dropdown data fetched successfully", result)
            elif dropdown_type == "agent":

                logged_in_user_id = data.get("logged_in_user_id")
                team_id = data.get("team_id")
                clean_team = "REPLACE(REPLACE(REPLACE(REPLACE(u.team_id,'[',''),']',''), '\"',''),' ','')"

                if not logged_in_user_id:
                    return api_response(400, "logged_in_user_id is required")

                user_role = get_user_role(cursor, logged_in_user_id)

                clean_pm = "REPLACE(REPLACE(REPLACE(REPLACE(u.project_manager_id,'[',''),']',''), '\"',''),' ','')"
                clean_am = "REPLACE(REPLACE(REPLACE(REPLACE(u.asst_manager_id,'[',''),']',''), '\"',''),' ','')"
                clean_qa = "REPLACE(REPLACE(REPLACE(REPLACE(u.qa_id,'[',''),']',''), '\"',''),' ','')"

                # ---------------- ADMIN / SUPER ADMIN ---------------- #
                if user_role in ["admin", "super admin", "project manager"]:
                    query = f"""
                        SELECT u.user_id, u.user_name AS label, u.user_tenure
                        FROM tfs_user u
                        JOIN user_role r ON r.role_id = u.role_id
                        WHERE u.is_delete = 1
                        AND r.is_active = 1
                        AND LOWER(r.role_name) = 'agent'
                        AND {visible_users_sql}
                    """
                    params = list(visible_users_params)

                    if team_id:
                        query += f" AND FIND_IN_SET(%s, {clean_team})"
                        params.append(team_id)

                    query += " ORDER BY u.user_name"

                # ---------------- PROJECT MANAGER ---------------- #
                elif user_role in ["manager"]:
                    query = f"""
                        SELECT u.user_id, u.user_name AS label, u.user_tenure
                        FROM tfs_user u
                        JOIN user_role r ON r.role_id = u.role_id
                        WHERE u.is_delete = 1
                        AND r.is_active = 1
                        AND LOWER(r.role_name) = 'agent'
                        AND {visible_users_sql}
                        AND FIND_IN_SET(%s, {clean_pm})
                    """

                    params = [*visible_users_params, logged_in_user_id]

                    if team_id:
                        query += f" AND FIND_IN_SET(%s, {clean_team})"
                        params.append(team_id)

                    query += " ORDER BY u.user_name"

                # ---------------- ASSISTANT MANAGER ---------------- #
                elif user_role == "assistant manager":
                    query = f"""
                        SELECT u.user_id, u.user_name AS label, u.user_tenure
                        FROM tfs_user u
                        JOIN user_role r ON r.role_id = u.role_id
                        WHERE u.is_delete = 1
                        AND r.is_active = 1
                        AND LOWER(r.role_name) = 'agent'
                        AND {visible_users_sql}
                        AND FIND_IN_SET(%s, {clean_am})
                        ORDER BY u.user_name
                    """
                    params = (*visible_users_params, logged_in_user_id)

                # ---------------- TEAM LEADER (assignees OR same team, view-only) ---------------- #
                elif user_role in ("assistant team leader", "team leader"):
                    from utils.roster_helpers import team_leader_scope_sql, team_leader_scope_params
                    query = f"""
                        SELECT u.user_id, u.user_name AS label, u.user_tenure
                        FROM tfs_user u
                        JOIN user_role r ON r.role_id = u.role_id
                        WHERE u.is_delete = 1
                        AND r.is_active = 1
                        AND LOWER(r.role_name) = 'agent'
                        AND {visible_users_sql}
                        AND {team_leader_scope_sql("u")}
                        ORDER BY u.user_name
                    """
                    params = (*visible_users_params, *team_leader_scope_params(logged_in_user_id))

                # ---------------- QA ---------------- #
                elif user_role == "qa":
                    query = f"""
                        SELECT u.user_id, u.user_name AS label, u.user_tenure
                        FROM tfs_user u
                        JOIN user_role r ON r.role_id = u.role_id
                        WHERE u.is_delete = 1
                        AND r.is_active = 1
                        AND LOWER(r.role_name) = 'agent'
                        AND {visible_users_sql}
                        AND FIND_IN_SET(%s, {clean_qa})
                        ORDER BY u.user_name
                    """
                    params = (*visible_users_params, logged_in_user_id)

                else:
                    return api_response(403, "Not allowed")

                cursor.execute(query, params)
                result = cursor.fetchall()

                for item in result:
                    if item.get("label"):
                        item["label"] = item["label"].title()

                return api_response(200, "Dropdown data fetched successfully", result)
            else:
                # Admin / Super Admin / Project Manager / Assistant Manager: active only.
                # QA / other role dropdowns: include leavers while leave date >= period start.
                if dropdown_type in ACTIVE_ONLY_USER_DROPDOWNS:
                    query = f"""
                        SELECT
                            u.user_id,
                            u.user_name AS label
                        FROM tfs_user u
                        JOIN user_role r ON r.role_id = u.role_id
                        WHERE u.is_delete = 1
                          AND r.is_active = 1
                          AND LOWER(r.role_name) = %s
                          AND u.is_active = 1
                        ORDER BY u.user_name
                    """
                    params = (dropdown_type,)
                else:
                    query = f"""
                        SELECT
                            u.user_id,
                            u.user_name AS label
                        FROM tfs_user u
                        JOIN user_role r ON r.role_id = u.role_id
                        WHERE u.is_delete = 1
                          AND r.is_active = 1
                          AND LOWER(r.role_name) = %s
                          AND {visible_users_sql}
                        ORDER BY u.user_name
                    """
                    params = (dropdown_type, *visible_users_params)
                cursor.execute(query, params)
                result = cursor.fetchall()
                for item in result:
                    if item.get("label"):
                        item["label"] = item["label"].title()
                return api_response(200, "Dropdown data fetched successfully", result)

        # -------------------- PROJECTS WITH TASKS -------------------- #
        if dropdown_type == "projects with tasks":
            user_id = data.get("user_id")
            logged_in_user_id = data.get("logged_in_user_id")
            if user_id:
                # Only return projects/tasks assigned to this user (regardless of role, including agent logic)
                v = str(user_id)
                params = [v, v]
                where_sql = "WHERE p.is_active = 1 AND " + multi_id_match_sql("p.project_team_id")
                task_join_extra = " AND " + multi_id_match_sql("t.task_team_id")
                task_params = [v, v]
                query = f"""
                    SELECT
                        p.project_id,
                        p.project_name,
                        p.ai_evaluation,
                        p.duplicate_check,
                        t.task_id,
                        t.task_name,
                        t.task_target
                    FROM project p
                    LEFT JOIN task t
                        ON t.project_id = p.project_id
                        AND t.is_active = 1
                        {task_join_extra}
                    {where_sql}
                    ORDER BY p.project_name, t.task_name
                """
                cursor.execute(query, tuple(params + task_params))
                rows = cursor.fetchall()
            else:
                # Use logged_in_user_id and role-based filtering
                if not logged_in_user_id:
                    return api_response(400, "logged_in_user_id or user_id is required for projects with tasks")
                filter_id = int(logged_in_user_id)
                user_role = get_user_role(cursor, filter_id)
                if not user_role:
                    return api_response(404, "User not found")
                params: list = []
                where_sql = "WHERE p.is_active = 1"
                if user_role in ["admin", "super admin", "project manager"]:
                    pass
                elif user_role == "qa":
                    v = str(filter_id)
                    where_sql += " AND " + multi_id_match_sql("p.project_qa_id")
                    params.extend([v, v])
                elif user_role in ["manager"]:
                    v = str(filter_id)
                    where_sql += " AND " + multi_id_match_sql("p.project_manager_id")
                    params.extend([v, v])
                elif user_role == "assistant manager":
                    v = str(filter_id)
                    where_sql += " AND " + multi_id_match_sql("p.asst_project_manager_id")
                    params.extend([v, v])
                elif user_role in ("assistant team leader", "team leader"):
                    from utils.roster_helpers import team_leader_scope_sql, team_leader_scope_params
                    v = str(filter_id)
                    clean_team = "REPLACE(REPLACE(REPLACE(REPLACE(p.project_team_id,'[',''),']',''),'\"',''),' ','')"
                    where_sql += f""" AND EXISTS (
                        SELECT 1 FROM tfs_user tu
                        WHERE tu.is_delete = 1
                          AND {team_leader_scope_sql("tu")}
                          AND FIND_IN_SET(CAST(tu.user_id AS CHAR), {clean_team}) > 0
                    )"""
                    params.extend(team_leader_scope_params(filter_id))
                elif user_role == "agent":
                    v = str(filter_id)
                    where_sql += " AND " + multi_id_match_sql("p.project_team_id")
                    params.extend([v, v])
                else:
                    v = str(filter_id)
                    where_sql += " AND " + multi_id_match_sql("p.project_team_id")
                    params.extend([v, v])
                # Optional: filter tasks by task_team_id for agent
                task_join_extra = ""
                task_params: list = []
                if user_role == "agent":
                    v = str(filter_id)
                    task_join_extra = " AND " + multi_id_match_sql("t.task_team_id")
                    task_params.extend([v, v])
                query = f"""
                    SELECT
                        p.project_id,
                        p.project_name,
                        p.ai_evaluation,
                        p.duplicate_check,
                        t.task_id,
                        t.task_name,
                        t.task_target
                    FROM project p
                    LEFT JOIN task t
                        ON t.project_id = p.project_id
                        AND t.is_active = 1
                        {task_join_extra}
                    {where_sql}
                    ORDER BY p.project_name, t.task_name
                """
                cursor.execute(query, tuple(params + task_params))
                rows = cursor.fetchall()

            projects_map = {}
            for row in rows:
                pid = row["project_id"]
                if pid not in projects_map:
                    projects_map[pid] = {
                        "project_id": pid,
                        "project_name": row["project_name"],
                        "requires_ai_evaluation": bool(row.get("ai_evaluation", 0)),
                        "requires_duplicate_check": bool(row.get("duplicate_check", 0)),
                        "tasks": []
                    }

                if row.get("task_id"):
                    projects_map[pid]["tasks"].append({
                        "task_id": row["task_id"],
                        "label": row["task_name"],
                        "task_target": row["task_target"]
                    })

            return api_response(200, "Dropdown data fetched successfully", list(projects_map.values()))

        # -------------------- INVALID -------------------- #
        return api_response(400, "Invalid dropdown_type")

    except Exception as e:
        return api_response(500, f"Failed to fetch dropdown data: {str(e)}")

    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

from flask import Blueprint, request
from config import get_db_connection
from utils.response import api_response
from datetime import datetime

qc_history_user_bp = Blueprint("qc_history_user", __name__)


@qc_history_user_bp.route("/view_qc_history_user_based", methods=["POST"])
def view_qc_history_user_based():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        data = request.json
        logged_in_user_id = data.get("logged_in_user_id")

        if not logged_in_user_id:
            return api_response(400, "logged_in_user_id is required")

        # ✅ 1. Get role
        cursor.execute("""
            SELECT ur.role_name
            FROM tfs_user u
            JOIN user_role ur ON u.role_id = ur.role_id
            WHERE u.user_id = %s
        """, (logged_in_user_id,))
        user = cursor.fetchone()

        if not user:
            return api_response(404, "User not found")

        role = user["role_name"].strip().lower()

        # 2. Base Query
        base_query = """
        SELECT
            qr.*,
            u.user_name AS agent_name,
            u.team_id AS user_team_id,
            t.team_name,
            p.project_name,
            task.task_name,
            qa.user_name AS qa_agent_name,
            am.user_name AS assistant_manager_name,
            DATE(qr.date_of_file_submission) as work_date_only,
            ur_agent.role_name as agent_role
        FROM qc_records qr
        LEFT JOIN task_work_tracker twt ON qr.tracker_id = twt.tracker_id
        LEFT JOIN tfs_user u ON u.user_id = twt.user_id
        LEFT JOIN user_role ur_agent ON u.role_id = ur_agent.role_id
        LEFT JOIN team t ON u.team_id = t.team_id
        LEFT JOIN project p ON p.project_id = twt.project_id
        LEFT JOIN task task ON task.task_id = twt.task_id
        LEFT JOIN tfs_user qa ON qa.user_id = qr.qa_user_id
        LEFT JOIN tfs_user am ON u.asst_manager_id LIKE CONCAT('%', am.user_id, '%')
        """

        params = []
        where_clauses = []

        # 3. Role-based filtering (JSON ARRAY SUPPORT)
        if any(r in role for r in ["admin", "super admin", "project manager"]):
            # Admin, Super Admin, and Project Manager get all records
            pass

        elif "qa" in role:
            # QA only gets records of users where they are the assigned QA, records they evaluated themselves, or their own records
            where_clauses.append("(JSON_CONTAINS(u.qa_id, %s) OR qr.qa_user_id = %s OR u.user_id = %s)")
            params.extend([f"{logged_in_user_id}", logged_in_user_id, logged_in_user_id])

        elif "assistant manager" in role:
            where_clauses.append("(JSON_CONTAINS(u.asst_manager_id, %s) OR u.user_id = %s)")
            params.extend([f"{logged_in_user_id}", logged_in_user_id])

        else:
            where_clauses.append("u.user_id = %s")
            params.append(logged_in_user_id)

        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        base_query += " ORDER BY qr.id DESC"

        print("QUERY:", base_query)
        print("PARAMS:", params)

        # ✅ 4. Execute
        cursor.execute(base_query, tuple(params))
        qc_records = cursor.fetchall()

        if not qc_records:
            return api_response(200, "No QC records found", {"count": 0, "records": []})

        qc_record_ids = [r["id"] for r in qc_records]

        # 5. Reworks
        cursor.execute(f"""
            SELECT 
                *,
                rework_status as review_status
            FROM qc_rework_history
            WHERE qc_record_id IN ({','.join(['%s'] * len(qc_record_ids))})
            ORDER BY qc_rework_id DESC
        """, tuple(qc_record_ids))
        reworks = cursor.fetchall()

        # 6. Corrections
        cursor.execute(f"""
            SELECT 
                *,
                correction_status as review_status
            FROM qc_correction_history
            WHERE qc_record_id IN ({','.join(['%s'] * len(qc_record_ids))})
            ORDER BY qc_correction_id DESC
        """, tuple(qc_record_ids))
        corrections = cursor.fetchall()

        # 7. Mapping
        rework_map = {}
        for r in reworks:
            rework_map.setdefault(r["qc_record_id"], []).append(r)

        correction_map = {}
        for c in corrections:
            correction_map.setdefault(c["qc_record_id"], []).append(c)

        # 8. Merge
        final_data = []
        for record in qc_records:
            record["qc_rework"] = rework_map.get(record["id"], [])
            record["qc_correction"] = correction_map.get(record["id"], [])
            final_data.append(record)

        return api_response(
            200,
            "QC history fetched successfully",
            {
                "count": len(final_data),
                "records": final_data
            }
        )

    except Exception as e:
        return api_response(500, f"Error: {str(e)}")

    finally:
        cursor.close()
        conn.close()

@qc_history_user_bp.route("/consolidated_qc_report", methods=["POST"])
def consolidated_qc_report():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        data = request.json
        logged_in_user_id = data.get("logged_in_user_id")
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        # ✅ Default to current month if dates not provided
        if not start_date and not end_date:
            now = datetime.now()
            start_date = now.replace(day=1).strftime("%Y-%m-%d")
            end_date = now.strftime("%Y-%m-%d")

        if not logged_in_user_id:
            return api_response(400, "logged_in_user_id is required")

        # 1. Get role
        cursor.execute("""
            SELECT ur.role_name
            FROM tfs_user u
            JOIN user_role ur ON u.role_id = ur.role_id
            WHERE u.user_id = %s
        """, (logged_in_user_id,))
        user = cursor.fetchone()

        if not user:
            return api_response(404, "User not found")

        role = user["role_name"].strip().lower()

        # 2. Base Query for individual records
        base_query = """
        SELECT
            qr.id,
            qr.assistant_manager_id,
            qr.qa_user_id,
            qr.agent_id,
            qr.project_id,
            qr.task_id,
            qr.tracker_id,
            DATE(qr.date_of_file_submission) as work_date_only,
            qr.date_of_file_submission,
            qr.qc_score,
            qr.status,
            qr.qc_status,
            qr.file_record_count,
            qr.qc_generated_count,
            qr.error_list,
            qr.created_at as evaluation_date,
            qr.updated_at,
            u.user_name AS agent_name,
            u.team_id AS user_team_id,
            t.team_name,
            p.project_name,
            task.task_name,
            qa.user_name AS qa_name,
            am.user_name AS team_lead,
            ur_agent.role_name as agent_role
        FROM qc_records qr
        LEFT JOIN task_work_tracker twt ON qr.tracker_id = twt.tracker_id
        LEFT JOIN tfs_user u ON u.user_id = twt.user_id
        LEFT JOIN user_role ur_agent ON u.role_id = ur_agent.role_id
        LEFT JOIN team t ON u.team_id = t.team_id
        LEFT JOIN project p ON p.project_id = twt.project_id
        LEFT JOIN task task ON task.task_id = twt.task_id
        LEFT JOIN tfs_user qa ON qa.user_id = qr.qa_user_id
        LEFT JOIN tfs_user am ON u.asst_manager_id LIKE CONCAT('%', am.user_id, '%')
        """

        params = []
        where_clauses = []

        # 3. Role-based filtering (JSON ARRAY SUPPORT)
        if any(r in role for r in ["admin", "super admin", "project manager"]):
            # Admin, Super Admin, and Project Manager get all records
            pass

        elif "qa" in role:
            # QA only gets records of users where they are the assigned QA, records they evaluated themselves, or their own records
            where_clauses.append("(JSON_CONTAINS(u.qa_id, %s) OR qr.qa_user_id = %s OR u.user_id = %s)")
            params.extend([f"{logged_in_user_id}", logged_in_user_id, logged_in_user_id])

        elif "assistant manager" in role:
            where_clauses.append("(JSON_CONTAINS(u.asst_manager_id, %s) OR u.user_id = %s)")
            params.extend([f"{logged_in_user_id}", logged_in_user_id])

        else:
            where_clauses.append("u.user_id = %s")
            params.append(logged_in_user_id)

        # 3b. Date Filter on Work Date (date_of_file_submission)
        if start_date and end_date:
            where_clauses.append("DATE(qr.date_of_file_submission) BETWEEN %s AND %s")
            params.extend([start_date, end_date])
        elif start_date:
            where_clauses.append("DATE(qr.date_of_file_submission) >= %s")
            params.append(start_date)
        elif end_date:
            where_clauses.append("DATE(qr.date_of_file_submission) <= %s")
            params.append(end_date)

        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        base_query += " ORDER BY qr.date_of_file_submission DESC, qr.id DESC"

        # 4. Execute
        cursor.execute(base_query, tuple(params))
        qc_records = cursor.fetchall()

        if not qc_records:
            return api_response(200, "No QC records found", {"count": 0, "records": []})

        # 5. Consolidate records by user, date, and project
        consolidated_records = {}
        
        # Mapping to store reworks and corrections for consolidated records
        consolidated_reworks = {}
        consolidated_corrections = {}
        
        # Get individual record IDs to fetch reworks and corrections
        qc_record_ids = [r["id"] for r in qc_records]
        
        # Fetch reworks
        cursor.execute(f"""
            SELECT *, rework_status as review_status 
            FROM qc_rework_history 
            WHERE qc_record_id IN ({','.join(['%s'] * len(qc_record_ids))})
        """, tuple(qc_record_ids))
        all_reworks = cursor.fetchall()
        
        # Fetch corrections
        cursor.execute(f"""
            SELECT *, correction_status as review_status 
            FROM qc_correction_history 
            WHERE qc_record_id IN ({','.join(['%s'] * len(qc_record_ids))})
        """, tuple(qc_record_ids))
        all_corrections = cursor.fetchall()
        
        # Map reworks/corrections by record ID
        rework_map = {}
        for r in all_reworks:
            rework_map.setdefault(r["qc_record_id"], []).append(r)
            
        correction_map = {}
        for c in all_corrections:
            correction_map.setdefault(c["qc_record_id"], []).append(c)
        
        for record in qc_records:
            # Create grouping key: user_id + date + project_id + task_id
            work_date_str = record["work_date_only"].strftime("%Y-%m-%d") if record["work_date_only"] else "None"
            group_key = f"{record['agent_id']}_{work_date_str}_{record['project_id']}_{record['task_id']}"
            
            if group_key not in consolidated_records:
                consolidated_records[group_key] = {
                    "evaluation_date": record["evaluation_date"],
                    "work_date": work_date_str,
                    "team_lead": record["team_lead"],
                    "agent_name": record["agent_name"],
                    "project_name": record["project_name"],
                    "task_name": record["task_name"],
                    "records": 0,
                    "qc_records": 0,
                    "no_of_errors": 0,
                    "final_qc_score": 0,
                    "error_type": [],
                    "qa_name": record["qa_name"],
                    "qc_score_sum": 0,
                    "qc_score_count": 0,
                }
            
            consolidated = consolidated_records[group_key]
            
            # Sum counts
            file_count = int(record["file_record_count"]) if record["file_record_count"] is not None else 0
            qc_count = int(record["qc_generated_count"]) if record["qc_generated_count"] is not None else 0
            consolidated["records"] += file_count
            consolidated["qc_records"] += qc_count
            
            # Average score
            if record["qc_score"] is not None:
                consolidated["qc_score_sum"] += float(record["qc_score"])
                consolidated["qc_score_count"] += 1
            
            # Merge error types
            if record["error_list"]:
                try:
                    import json
                    error_list = json.loads(record["error_list"]) if isinstance(record["error_list"], str) else record["error_list"]
                    if isinstance(error_list, list):
                        # Add to the total error count for this consolidated row
                        consolidated["no_of_errors"] += len(error_list)
                        
                        # Extract error types
                        for error in error_list:
                            if isinstance(error, dict):
                                # Prioritize subcategory or error over category for more specific info
                                error_type = error.get("subcategory") or error.get("error") or error.get("category") or "Unknown"
                                if error_type and error_type not in consolidated["error_type"]:
                                    consolidated["error_type"].append(error_type)
                except (json.JSONDecodeError, TypeError):
                    pass
        
        # Finalize
        final_data = []
        for consolidated in consolidated_records.values():
            if consolidated["qc_score_count"] > 0:
                consolidated["final_qc_score"] = round(consolidated["qc_score_sum"] / consolidated["qc_score_count"], 2)
            
            consolidated.pop("qc_score_sum", None)
            consolidated.pop("qc_score_count", None)
            final_data.append(consolidated)

        # Sort by work date descending
        final_data.sort(key=lambda x: x["work_date"] or "", reverse=True)

        return api_response(
            200,
            "QC consolidated history fetched successfully",
            {
                "count": len(final_data),
                "records": final_data
            }
        )

    except Exception as e:
        return api_response(500, f"Error: {str(e)}")

    finally:
        cursor.close()
        conn.close()
from flask import Blueprint, request
from config import get_db_connection
from utils.response import api_response

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

        # 2. Base Query for individual records (needed for consolidation)
        base_query = """
        SELECT
            qr.id,
            qr.assistant_manager_id,
            qr.qa_user_id,
            qr.agent_id,
            qr.project_id,
            qr.task_id,
            qr.tracker_id,
            qr.whole_file_path,
            qr.qc_file_path,
            qr.date_of_file_submission,
            qr.qc_score,
            qr.status,
            qr.qc_status,
            qr.file_record_count,
            qr.qc_generated_count,
            qr.error_list,
            qr.created_at,
            qr.updated_at,
            u.user_name AS agent_name,
            u.team_id AS user_team_id,
            t.team_name,
            p.project_name,
            task.task_name,
            qa.user_name AS qa_agent_name,
            am.user_name AS assistant_manager_name
        FROM qc_records qr
        LEFT JOIN task_work_tracker twt ON qr.tracker_id = twt.tracker_id
        LEFT JOIN tfs_user u ON u.user_id = twt.user_id
        LEFT JOIN team t ON u.team_id = t.team_id
        LEFT JOIN project p ON p.project_id = twt.project_id
        LEFT JOIN task task ON task.task_id = twt.task_id
        LEFT JOIN tfs_user qa ON qa.user_id = qr.qa_user_id
        LEFT JOIN tfs_user am ON u.asst_manager_id LIKE CONCAT('%', am.user_id, '%')
        """

        params = []

        # 3. Role-based filtering (JSON ARRAY SUPPORT)
        if "admin" in role:
            pass

        elif "project manager" in role:
            base_query += """
            WHERE (
                JSON_CONTAINS(u.project_manager_id, %s)
                OR u.user_id = %s
            )
            """
            params.extend([f"{logged_in_user_id}", logged_in_user_id])

        elif "assistant manager" in role:
            base_query += """
            WHERE (
                JSON_CONTAINS(u.asst_manager_id, %s)
                OR u.user_id = %s
            )
            """
            params.extend([f"{logged_in_user_id}", logged_in_user_id])

        elif "qa" in role:
            base_query += """
            WHERE (
                JSON_CONTAINS(u.qa_id, %s)
                OR u.user_id = %s
            )
            """
            params.extend([f"{logged_in_user_id}", logged_in_user_id])

        else:
            base_query += " WHERE u.user_id = %s "
            params.append(logged_in_user_id)

        base_query += " ORDER BY qr.date_of_file_submission DESC, qr.id DESC"

        print("QUERY:", base_query)
        print("PARAMS:", params)

        # ✅ 4. Execute
        cursor.execute(base_query, tuple(params))
        qc_records = cursor.fetchall()

        if not qc_records:
            return api_response(200, "No QC records found", {"count": 0, "records": []})

        # 5. Get rework and correction history for all records
        qc_record_ids = [r["id"] for r in qc_records]

        cursor.execute(f"""
            SELECT 
                *,
                rework_status as review_status
            FROM qc_rework_history
            WHERE qc_record_id IN ({','.join(['%s'] * len(qc_record_ids))})
            ORDER BY qc_rework_id DESC
        """, tuple(qc_record_ids))
        reworks = cursor.fetchall()

        cursor.execute(f"""
            SELECT 
                *,
                correction_status as review_status
            FROM qc_correction_history
            WHERE qc_record_id IN ({','.join(['%s'] * len(qc_record_ids))})
            ORDER BY qc_correction_id DESC
        """, tuple(qc_record_ids))
        corrections = cursor.fetchall()

        # 6. Create mappings for rework and correction history
        rework_map = {}
        for r in reworks:
            rework_map.setdefault(r["qc_record_id"], []).append(r)

        correction_map = {}
        for c in corrections:
            correction_map.setdefault(c["qc_record_id"], []).append(c)

        # 7. Consolidate records by user, date, and project
        consolidated_records = {}
        
        for record in qc_records:
            # Create grouping key: user_id + date + project_id
            date_key = record["date_of_file_submission"].strftime("%Y-%m-%d") if record["date_of_file_submission"] else None
            group_key = f"{record['agent_id']}_{date_key}_{record['project_id']}"
            
            if group_key not in consolidated_records:
                # Initialize consolidated record
                consolidated_records[group_key] = {
                    "agent_id": record["agent_id"],
                    "agent_name": record["agent_name"],
                    "user_team_id": record["user_team_id"],
                    "team_name": record["team_name"],
                    "project_id": record["project_id"],
                    "project_name": record["project_name"],
                    "date_of_file_submission": record["date_of_file_submission"],
                    # Required fields for display
                    "qc_records": 0,  # Total QC generated count
                    "no_of_errors": 0,  # Total error count
                    "final_qc_score": 0,  # Average QC score
                    "error_types": [],  # Unique error categories/types
                    # Additional fields for internal use
                    "total_file_record_count": 0,
                    "total_qc_generated_count": 0,
                    "average_qc_score": 0,
                    "total_error_count": 0,
                    "merged_error_list": [],
                    "qc_statuses": set(),
                    "statuses": set(),
                    "individual_records": [],
                    "assistant_manager_id": record["assistant_manager_id"],
                    "assistant_manager_name": record["assistant_manager_name"],
                    "qa_user_id": record["qa_user_id"],
                    "qa_agent_name": record["qa_agent_name"],
                    "task_id": record["task_id"],
                    "task_name": record["task_name"],
                    "created_at": record["created_at"],
                    "updated_at": record["updated_at"]
                }
            
            consolidated = consolidated_records[group_key]
            
            # Add record counts with explicit conversion
            file_count = int(record["file_record_count"] or 0)
            qc_count = int(record["qc_generated_count"] or 0)
            
            consolidated["total_file_record_count"] += file_count
            consolidated["total_qc_generated_count"] += qc_count
            
            # Update display fields
            consolidated["qc_records"] += qc_count  # QC Records = total QC generated count
            
            # Add to QC score for averaging
            if record["qc_score"] is not None:
                if "qc_score_sum" not in consolidated:
                    consolidated["qc_score_sum"] = 0
                    consolidated["qc_score_count"] = 0
                consolidated["qc_score_sum"] += record["qc_score"]
                consolidated["qc_score_count"] += 1
            
            # Merge error lists and extract error types
            if record["error_list"]:
                try:
                    import json
                    error_list = json.loads(record["error_list"]) if isinstance(record["error_list"], str) else record["error_list"]
                    if error_list:
                        consolidated["merged_error_list"].extend(error_list)
                        consolidated["total_error_count"] += len(error_list)
                        consolidated["no_of_errors"] += len(error_list)  # Update display field
                        
                        # Extract error types/categories
                        for error in error_list:
                            if isinstance(error, dict):
                                # Extract error category or type
                                error_type = error.get("category") or error.get("subcategory") or error.get("error", "Unknown")
                                if error_type not in consolidated["error_types"]:
                                    consolidated["error_types"].append(error_type)
                except (json.JSONDecodeError, TypeError):
                    pass
            
            # Collect unique statuses
            if record["qc_status"]:
                consolidated["qc_statuses"].add(record["qc_status"])
            if record["status"]:
                consolidated["statuses"].add(record["status"])
            
            # Add individual record with its history
            record_with_history = record.copy()
            record_with_history["qc_rework"] = rework_map.get(record["id"], [])
            record_with_history["qc_correction"] = correction_map.get(record["id"], [])
            consolidated["individual_records"].append(record_with_history)
        
        # 8. Finalize consolidated records
        final_data = []
        for consolidated in consolidated_records.values():
            # Calculate average QC score
            if "qc_score_sum" in consolidated and consolidated["qc_score_count"] > 0:
                avg_score = round(consolidated["qc_score_sum"] / consolidated["qc_score_count"], 2)
                consolidated["average_qc_score"] = avg_score
                consolidated["final_qc_score"] = avg_score  # Set display field
            
            # Convert sets to lists
            consolidated["qc_statuses"] = list(consolidated["qc_statuses"])
            consolidated["statuses"] = list(consolidated["statuses"])
            
            # Remove temporary fields
            consolidated.pop("qc_score_sum", None)
            consolidated.pop("qc_score_count", None)
            
            final_data.append(consolidated)

        # Sort by date descending
        final_data.sort(key=lambda x: x["date_of_file_submission"] or "", reverse=True)

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
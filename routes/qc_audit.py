from flask import Blueprint, request, jsonify
from config import get_db_connection
from datetime import datetime
from utils.cloudinary_utils import upload_to_cloudinary, delete_from_cloudinary

qc_audit_bp = Blueprint("qc_audit", __name__)

FOLDER_QC_AUDIT = "hrms/qc_audit_files"

@qc_audit_bp.route("/add", methods=["POST"])
def create_qc_audit():

    form = request.form

    qc_record_id = form.get("qc_record_id")
    qc_score = form.get("qc_score")
    error_notes = form.get("error_notes")

    if not qc_record_id or not qc_score:
        return jsonify({
            "status":400,
            "message":"qc_record_id and qc_score required"
        }),400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        qc_file_url = None
        uploaded = request.files.get("qc_checked_file")

        if uploaded and uploaded.filename:
            extension = uploaded.filename.rsplit('.', 1)[1].lower()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            custom_name = f"qc_checked_file_{qc_record_id}_{timestamp}.{extension}"

            qc_file_url, _ = upload_to_cloudinary(
                uploaded,
                FOLDER_QC_AUDIT,
                display_name=custom_name ,
                resource_type="raw"
            )

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
        INSERT INTO qc_audit
        (qc_record_id,qc_score,qc_checked_file,error_notes,created_date,updated_date)
        VALUES(%s,%s,%s,%s,%s,%s)
        """,(
            qc_record_id,
            qc_score,
            qc_file_url,
            error_notes,
            now,
            now
        ))

        conn.commit()

        return jsonify({
            "status":201,
            "message":"QC audit created"
        }),201

    except Exception as e:
        conn.rollback()
        return jsonify({
            "status":500,
            "message":str(e)
        }),500

    finally:
        cursor.close()
        conn.close() 
        

@qc_audit_bp.route("/test", methods=["GET"])
def test_qc_audit():
    return jsonify({
        "status": 200,
        "message": "QC Audit Test - Code Updated Successfully",
        "timestamp": str(datetime.now())
    })

@qc_audit_bp.route("/report", methods=["POST"])
def qc_audit_report():

    data = request.get_json()
    start_date = data.get("start_date")  # Format: "2024-04-07"
    end_date = data.get("end_date")      # Format: "2024-04-10"
    
    # If no date filters provided, default to current month
    if not start_date or not end_date:
        from datetime import datetime
        current_month = datetime.now().strftime("%Y-%m")
        start_date = f"{current_month}-01"
        # Get last day of current month
        current_year = datetime.now().year
        current_month_num = datetime.now().month
        if current_month_num in [1,3,5,7,8,10,12]:
            last_day = 31
        elif current_month_num in [4,6,9,11]:
            last_day = 30
        elif current_month_num == 2:
            # Check for leap year
            if (current_year % 4 == 0 and current_year % 100 != 0) or (current_year % 400 == 0):
                last_day = 29
            else:
                last_day = 28
        else:
            last_day = 30
        end_date = f"{current_month}-{last_day:02d}"
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        # Base query with date filter
        query = """
        SELECT
        qa.created_date AS audit_datetime,
        qr.date_of_file_submission AS worked_date,
        qr.updated_at AS evaluation_date,
        tu.user_name AS agent_name,
        qc_user.user_name AS qc_agent_name,
        p.project_name AS project,
        t.task_name AS task,
        qr.qc_generated_count AS total_qcs,
        qa.qc_score AS avg_qc_score,
        qr.error_list AS total_errors,
        qa.qc_checked_file,
        qr.qc_status,
        qa.error_notes

        FROM qc_audit qa

        LEFT JOIN qc_records qr
        ON qa.qc_record_id = qr.id

        LEFT JOIN tfs_user tu
        ON qr.agent_id = tu.user_id

        LEFT JOIN tfs_user qc_user
        ON qr.qa_user_id = qc_user.user_id

        LEFT JOIN project p
        ON qr.project_id = p.project_id

        LEFT JOIN task t
        ON qr.task_id = t.task_id
        """

        # Add date filter if start_date and end_date are provided
        date_filter = ""
        if start_date and end_date:
            date_filter = f"""
            WHERE DATE(qr.date_of_file_submission) >= DATE('{start_date}')
            AND DATE(qr.date_of_file_submission) <= DATE('{end_date}')
            """

        query += date_filter + """
        ORDER BY qa.created_date DESC
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        return jsonify({
            "status": 200,
            "message": "QC Audit Report",
            "data": {
                "count": len(rows),
                "records": rows
            }
        }), 200

    except Exception as e:
        return jsonify({
            "status": 500,
            "message": str(e)
        }), 500

    finally:
        cursor.close()
        conn.close()
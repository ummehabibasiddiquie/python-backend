from flask import Blueprint, request

from config import get_db_connection
from mysql.connector import IntegrityError

from report_email_recipients import (
    ensure_table,
    fetch_active_rows,
    find_row_by_email,
    flag_int,
    is_valid_email,
    lists_from_rows,
    normalize_email,
    normalize_type,
)
from utils.response import api_response
from utils.time_ist import now_str

report_email_bp = Blueprint("report_email", __name__)


def get_user_role(cursor, user_id: int) -> str | None:
    cursor.execute(
        """
        SELECT r.role_name
        FROM tfs_user u
        JOIN user_role r ON r.role_id = u.role_id
        WHERE u.user_id=%s AND u.is_active=1 AND u.is_delete=1
        """,
        (user_id,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return (row.get("role_name") or "").strip().lower()


def require_super_admin(cursor, logged_in_user_id):
    if not logged_in_user_id:
        return "logged_in_user_id is required"
    role = get_user_role(cursor, int(logged_in_user_id))
    role_norm = (role or "").replace("_", " ").strip().lower()
    if role_norm == "super admin":
        return None
    return "Permission denied. Only Super Admin can manage report emails."


@report_email_bp.route("/list", methods=["POST"])
def list_report_emails():
    data = request.get_json(silent=True) or {}
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        err = require_super_admin(cursor, data.get("logged_in_user_id"))
        if err:
            return api_response(403 if "Permission" in err else 400, err)
        ensure_table(cursor)
        rows = fetch_active_rows(cursor)
        to_list, cc_list = lists_from_rows(rows)
        return api_response(
            200,
            "Report emails fetched successfully",
            {"rows": rows, "to": to_list, "cc": cc_list},
        )
    except Exception as e:
        conn.rollback()
        return api_response(500, f"Failed to list report emails: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@report_email_bp.route("/add", methods=["POST"])
def add_report_email():
    data = request.get_json(silent=True) or {}
    email = normalize_email(data.get("email"))
    kind = normalize_type(data.get("recipient_type") or data.get("type"))
    if not is_valid_email(email):
        return api_response(400, "A valid email is required")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        err = require_super_admin(cursor, data.get("logged_in_user_id"))
        if err:
            return api_response(403 if "Permission" in err else 400, err)
        ensure_table(cursor)
        existing = find_row_by_email(cursor, email)
        now = now_str()
        send_billable = flag_int(data.get("send_billable"), 1)
        send_tracker = flag_int(data.get("send_tracker"), 1)
        send_tracker_full = flag_int(data.get("send_tracker_full"), 1)
        if existing and int(existing.get("is_active") or 0) == 1:
            return api_response(400, "This email is already in the list")
        if existing:
            cursor.execute(
                """
                UPDATE report_email_recipient
                SET recipient_type=%s, is_active=1,
                    send_billable=%s, send_tracker=%s, send_tracker_full=%s,
                    updated_date=%s
                WHERE recipient_id=%s
                """,
                (
                    kind,
                    send_billable,
                    send_tracker,
                    send_tracker_full,
                    now,
                    existing["recipient_id"],
                ),
            )
            conn.commit()
            return api_response(
                201,
                "Email added",
                {
                    "recipient_id": existing["recipient_id"],
                    "email": email,
                    "recipient_type": kind,
                },
            )
        try:
            cursor.execute(
                """
                INSERT INTO report_email_recipient (
                    email, recipient_type, is_active,
                    send_billable, send_tracker, send_tracker_full,
                    created_date, updated_date
                )
                VALUES (%s, %s, 1, %s, %s, %s, %s, %s)
                """,
                (email, kind, send_billable, send_tracker, send_tracker_full, now, now),
            )
        except IntegrityError:
            conn.rollback()
            return api_response(400, "This email is already in the list")
        conn.commit()
        return api_response(
            201,
            "Email added",
            {"recipient_id": cursor.lastrowid, "email": email, "recipient_type": kind},
        )
    except IntegrityError:
        conn.rollback()
        return api_response(400, "This email is already in the list")
    except Exception as e:
        conn.rollback()
        return api_response(500, f"Failed to add email: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@report_email_bp.route("/update", methods=["POST"])
def update_report_email():
    data = request.get_json(silent=True) or {}
    recipient_id = data.get("recipient_id")
    if not recipient_id:
        return api_response(400, "recipient_id is required")
    kind = normalize_type(data.get("recipient_type") or data.get("type"))
    email = data.get("email")
    email_norm = normalize_email(email) if email is not None else None
    if email is not None and not is_valid_email(email_norm):
        return api_response(400, "A valid email is required")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        err = require_super_admin(cursor, data.get("logged_in_user_id"))
        if err:
            return api_response(403 if "Permission" in err else 400, err)
        ensure_table(cursor)
        cursor.execute(
            "SELECT recipient_id FROM report_email_recipient WHERE recipient_id=%s AND is_active=1",
            (recipient_id,),
        )
        if not cursor.fetchone():
            return api_response(404, "Email not found")

        send_billable = data.get("send_billable")
        send_tracker = data.get("send_tracker")
        send_tracker_full = data.get("send_tracker_full")

        sets = ["recipient_type=%s", "updated_date=%s"]
        params = [kind, now_str()]
        if email_norm:
            other = find_row_by_email(cursor, email_norm)
            if other and int(other.get("recipient_id")) != int(recipient_id):
                return api_response(400, "This email is already in the list")
            sets.append("email=%s")
            params.append(email_norm)
        if "send_billable" in data:
            sets.append("send_billable=%s")
            params.append(flag_int(send_billable, 0 if send_billable in (0, "0", False) else 1))
        if "send_tracker" in data:
            sets.append("send_tracker=%s")
            params.append(flag_int(send_tracker, 0 if send_tracker in (0, "0", False) else 1))
        if "send_tracker_full" in data:
            sets.append("send_tracker_full=%s")
            params.append(flag_int(send_tracker_full, 0 if send_tracker_full in (0, "0", False) else 1))
        params.append(recipient_id)
        cursor.execute(
            f"UPDATE report_email_recipient SET {', '.join(sets)} WHERE recipient_id=%s",
            tuple(params),
        )
        conn.commit()
        cursor.execute(
            """
            SELECT recipient_id, email, recipient_type,
                   send_billable, send_tracker, send_tracker_full
            FROM report_email_recipient
            WHERE recipient_id=%s
            """,
            (recipient_id,),
        )
        saved = cursor.fetchone() or {}
        from report_email_recipients import normalize_row_flags

        return api_response(200, "Email updated", normalize_row_flags(saved))
    except IntegrityError:
        conn.rollback()
        return api_response(400, "This email is already in the list")
    except Exception as e:
        conn.rollback()
        return api_response(500, f"Failed to update email: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@report_email_bp.route("/delete", methods=["POST"])
def delete_report_email():
    data = request.get_json(silent=True) or {}
    recipient_id = data.get("recipient_id")
    if not recipient_id:
        return api_response(400, "recipient_id is required")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        err = require_super_admin(cursor, data.get("logged_in_user_id"))
        if err:
            return api_response(403 if "Permission" in err else 400, err)
        cursor.execute(
            """
            SELECT recipient_id, recipient_type FROM report_email_recipient
            WHERE recipient_id=%s AND is_active=1
            """,
            (recipient_id,),
        )
        row = cursor.fetchone()
        if not row:
            return api_response(404, "Email not found")
        if normalize_type(row.get("recipient_type")) == "to":
            cursor.execute(
                """
                SELECT COUNT(*) AS n FROM report_email_recipient
                WHERE is_active=1 AND recipient_type='to' AND recipient_id != %s
                """,
                (recipient_id,),
            )
            left = int((cursor.fetchone() or {}).get("n") or 0)
            if left < 1:
                return api_response(400, "Keep at least one To email so reports can still send.")
        cursor.execute(
            """
            UPDATE report_email_recipient
            SET is_active=0, updated_date=%s
            WHERE recipient_id=%s
            """,
            (now_str(), recipient_id),
        )
        conn.commit()
        return api_response(200, "Email removed")
    except Exception as e:
        conn.rollback()
        return api_response(500, f"Failed to remove email: {str(e)}")
    finally:
        cursor.close()
        conn.close()

# One Word SOP document per task. Converted to HTML for the Tracker sidebar.
# Live copy = approved only. Uploads land in draft until a checker role approves.

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime
from html import escape
from io import BytesIO

from flask import Blueprint, request

from config import get_db_connection
from utils.cloudinary_utils import upload_to_cloudinary
from utils.docx_to_html import convert_docx_to_html
from utils.email_utils import send_email
from utils.response import api_response
from utils.roster_helpers import get_role_context, now_str
from utils.time_ist import IST, now_ist, today_str

task_sop_bp = Blueprint("task_sop", __name__)

FOLDER_TASK_SOP = "hrms/task_sop"
# Keep in sync with TaskSopEditor.jsx MAX_SOP_FILE_MB
MAX_SOP_FILE_MB = 10
MAX_FILE_BYTES = MAX_SOP_FILE_MB * 1024 * 1024
MAX_SOP_HTML_BYTES = 8 * 1024 * 1024
SOP_FILE_TOO_LARGE_MSG = (
    f"SOP Word file is too large. Maximum allowed size is {MAX_SOP_FILE_MB} MB. "
    "Compress or remove large screenshots and try again."
)
SOP_HTML_TOO_LARGE_MSG = (
    f"This SOP has too much content after conversion (over {MAX_SOP_HTML_BYTES // (1024 * 1024)} MB HTML). "
    "Reduce image size or count in the Word file and try again."
)
SOP_CHECKER_ROLES = {
    "admin",
    "super admin",
    "project manager",
    "assistant manager",
    "qa",
}
SOP_MAIL_ROLES = (
    "admin",
    "super admin",
    "project manager",
    "assistant manager",
)
SOP_MAIL_ROLE_IDS = (1, 2, 3, 4)


def save_sop_image(data: bytes, content_type: str | None) -> str:
    """Upload a screenshot from the Word SOP to Cloudinary and return its URL."""
    ct = (content_type or "").lower()
    ext = "png"
    if "jpeg" in ct or "jpg" in ct:
        ext = "jpg"
    elif "gif" in ct:
        ext = "gif"
    elif "webp" in ct:
        ext = "webp"
    stem = f"img_{uuid.uuid4().hex[:16]}"
    url, _public_id = upload_to_cloudinary(
        BytesIO(data),
        f"{FOLDER_TASK_SOP}/images",
        display_name=stem,
        resource_type="image",
    )
    return url


def _require_user(data: dict):
    logged_in_user_id = data.get("logged_in_user_id")
    if not logged_in_user_id:
        return None, api_response(400, "logged_in_user_id is required")
    try:
        return int(logged_in_user_id), None
    except (TypeError, ValueError):
        return None, api_response(400, "logged_in_user_id is required")


def _can_manage(role_name: str, role_id) -> bool:
    name = (role_name or "").strip().lower()
    try:
        if int(role_id) in (1, 2, 3, 4, 5):
            return True
    except (TypeError, ValueError):
        pass
    return name in SOP_CHECKER_ROLES


def _checker_emails(cursor, exclude_user_id=None) -> list[str]:
    role_placeholders = ",".join(["%s"] * len(SOP_MAIL_ROLES))
    id_placeholders = ",".join(["%s"] * len(SOP_MAIL_ROLE_IDS))
    params = list(SOP_MAIL_ROLES) + list(SOP_MAIL_ROLE_IDS)
    exclude_sql = ""
    if exclude_user_id is not None:
        exclude_sql = " AND u.user_id <> %s"
        params.append(int(exclude_user_id))
    cursor.execute(
        f"""
        SELECT DISTINCT u.user_id, u.user_email
        FROM tfs_user u
        JOIN user_role r ON r.role_id = u.role_id
        WHERE u.is_active=1 AND u.is_delete=1
          AND u.user_email IS NOT NULL AND TRIM(u.user_email) != ''
          AND (
            LOWER(TRIM(r.role_name)) IN ({role_placeholders})
            OR u.role_id IN ({id_placeholders})
          )
          {exclude_sql}
        """,
        tuple(params),
    )
    emails = []
    seen = set()
    for row in cursor.fetchall() or []:
        email = (row.get("user_email") or "").strip()
        key = email.lower()
        if email and key not in seen:
            seen.add(key)
            emails.append(email)
    return emails


def _notify_draft_ready(cursor, task_id: int, uploaded_by: int, kind: str) -> dict:
    cursor.execute(
        """
        SELECT t.task_name, p.project_name, u.user_name
        FROM task t
        JOIN project p ON p.project_id = t.project_id
        LEFT JOIN tfs_user u ON u.user_id = %s
        WHERE t.task_id=%s
        """,
        (int(uploaded_by), int(task_id)),
    )
    info = cursor.fetchone() or {}
    project_name = escape(info.get("project_name") or "Project")
    task_name = escape(info.get("task_name") or f"Task {task_id}")
    who = escape(info.get("user_name") or "A checker")
    action = "updated" if kind == "updated" else "added"
    subject = f"Task SOP {action} — please approve: {project_name} / {task_name}"
    html = f"""
    <p>A task SOP was <strong>{action}</strong> and is waiting for approval.</p>
    <p>
      <strong>Project:</strong> {project_name}<br/>
      <strong>Task:</strong> {task_name}<br/>
      <strong>Added / updated by:</strong> {who}<br/>
      <strong>Date:</strong> {now_str()}
    </p>
    <p>Open HRMS → <strong>Manage → Projects &amp; Targets</strong>, open the task (yellow <strong>Waiting for approval</strong> badge), then Approve SOP. The person who added the draft cannot approve it.</p>
    """
    emails = _checker_emails(cursor, exclude_user_id=uploaded_by)
    if not emails:
        print("[task_sop] no AM/PM/Admin/Super Admin emails to notify", flush=True)
        return {"email_sent": False, "email_count": 0}
    try:
        send_email(emails, subject, html)
        print(f"[task_sop] draft notify emailed {len(emails)} checkers", flush=True)
        return {"email_sent": True, "email_count": len(emails)}
    except Exception as mail_err:
        print(f"[task_sop] draft notify email failed: {mail_err}", flush=True)
        return {"email_sent": False, "email_count": 0}


def _user_email(cursor, user_id) -> str:
    if not user_id:
        return ""
    cursor.execute(
        """
        SELECT user_email FROM tfs_user
        WHERE user_id=%s AND is_active=1 AND is_delete=1
          AND user_email IS NOT NULL AND TRIM(user_email) != ''
        LIMIT 1
        """,
        (int(user_id),),
    )
    row = cursor.fetchone() or {}
    return (row.get("user_email") or "").strip()


def _notify_approved(cursor, task_id: int, approved_by: int, maker_id) -> dict:
    cursor.execute(
        """
        SELECT t.task_name, p.project_name, a.user_name AS approver_name
        FROM task t
        JOIN project p ON p.project_id = t.project_id
        LEFT JOIN tfs_user a ON a.user_id = %s
        WHERE t.task_id=%s
        """,
        (int(approved_by), int(task_id)),
    )
    info = cursor.fetchone() or {}
    project_name = escape(info.get("project_name") or "Project")
    task_name = escape(info.get("task_name") or f"Task {task_id}")
    who = escape(info.get("approver_name") or "A checker")
    subject = f"Task SOP approved: {project_name} / {task_name}"
    html = f"""
    <p>A task SOP has been <strong>approved</strong> and is now live for agents.</p>
    <p>
      <strong>Project:</strong> {project_name}<br/>
      <strong>Task:</strong> {task_name}<br/>
      <strong>Approved by:</strong> {who}<br/>
      <strong>Date:</strong> {now_str()}
    </p>
    <p>Agents will see this SOP in Tracker. No further action is needed unless you want to replace it with a new draft.</p>
    """
    emails = _checker_emails(cursor, exclude_user_id=None)
    seen = {e.lower() for e in emails}
    for extra_id in (approved_by, maker_id):
        extra = _user_email(cursor, extra_id)
        if extra and extra.lower() not in seen:
            emails.append(extra)
            seen.add(extra.lower())
    if not emails:
        print("[task_sop] no emails for approval notify", flush=True)
        return {"email_sent": False, "email_count": 0}
    try:
        send_email(emails, subject, html)
        print(f"[task_sop] approval notify emailed {len(emails)} people", flush=True)
        return {"email_sent": True, "email_count": len(emails)}
    except Exception as mail_err:
        print(f"[task_sop] approval notify email failed: {mail_err}", flush=True)
        return {"email_sent": False, "email_count": 0}


def _ensure_table(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS task_sop (
            task_sop_id INT AUTO_INCREMENT PRIMARY KEY,
            task_id INT NOT NULL,
            title VARCHAR(250) NOT NULL,
            original_file_url VARCHAR(1000) NULL,
            original_file_name VARCHAR(255) NULL,
            html_body MEDIUMTEXT NULL,
            created_by INT NULL,
            updated_by INT NULL,
            is_delete TINYINT NOT NULL DEFAULT 1,
            created_at DATETIME NULL,
            updated_at DATETIME NULL,
            INDEX idx_task_sop_task (task_id)
        )
        """
    )
    cursor.execute("SHOW COLUMNS FROM task_sop")
    have = set()
    for row in cursor.fetchall():
        field = row.get("Field") if isinstance(row, dict) else row[0]
        if field:
            have.add(str(field).lower())
    for name, ddl in (
        ("draft_html_body", "MEDIUMTEXT NULL"),
        ("draft_file_url", "VARCHAR(1000) NULL"),
        ("draft_file_name", "VARCHAR(255) NULL"),
        ("draft_change_note", "VARCHAR(500) NULL"),
        ("draft_updated_by", "INT NULL"),
        ("draft_updated_at", "DATETIME NULL"),
        ("approved_by", "INT NULL"),
        ("approved_at", "DATETIME NULL"),
        ("change_note", "VARCHAR(500) NULL"),
    ):
        if name.lower() in have:
            continue
        try:
            cursor.execute(f"ALTER TABLE task_sop ADD COLUMN {name} {ddl}")
        except Exception as alter_err:
            if "duplicate" not in str(alter_err).lower():
                raise
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS task_sop_history (
            history_id INT AUTO_INCREMENT PRIMARY KEY,
            task_id INT NOT NULL,
            task_sop_id INT NULL,
            version_no INT NOT NULL DEFAULT 1,
            title VARCHAR(250) NULL,
            original_file_url VARCHAR(1000) NULL,
            original_file_name VARCHAR(255) NULL,
            html_body MEDIUMTEXT NULL,
            change_note VARCHAR(500) NULL,
            approved_by INT NULL,
            approved_at DATETIME NULL,
            archived_by INT NULL,
            archived_at DATETIME NULL,
            INDEX idx_task_sop_history_task (task_id, version_no)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS task_sop_ack (
            ack_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            task_id INT NOT NULL,
            ack_key VARCHAR(120) NOT NULL,
            acked_at DATETIME NULL,
            UNIQUE KEY uq_task_sop_ack (user_id, task_id, ack_key)
        )
        """
    )
    today = today_str()
    cursor.execute(
        """
        UPDATE task_sop
        SET approved_at = COALESCE(approved_at, updated_at, created_at),
            approved_by = COALESCE(approved_by, updated_by, created_by)
        WHERE is_delete=1
          AND approved_at IS NULL
          AND html_body IS NOT NULL
          AND TRIM(html_body) <> ''
          AND (draft_html_body IS NULL OR TRIM(draft_html_body) = '')
          AND created_at IS NOT NULL
          AND DATE(created_at) < %s
        """,
        (today,),
    )
    cursor.execute(
        """
        UPDATE task_sop
        SET draft_html_body = COALESCE(NULLIF(TRIM(draft_html_body), ''), html_body),
            draft_file_url = COALESCE(draft_file_url, original_file_url),
            draft_file_name = COALESCE(draft_file_name, original_file_name),
            draft_change_note = COALESCE(NULLIF(draft_change_note, ''), NULLIF(change_note, ''), 'Initial SOP'),
            draft_updated_at = COALESCE(draft_updated_at, updated_at, created_at),
            draft_updated_by = COALESCE(draft_updated_by, updated_by, created_by),
            html_body = NULL,
            original_file_url = NULL,
            original_file_name = NULL
        WHERE is_delete=1
          AND approved_at IS NULL
          AND (
            (html_body IS NOT NULL AND TRIM(html_body) <> '')
            OR original_file_url IS NOT NULL
          )
        """
    )


def _as_ist(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=IST) if val.tzinfo is None else val.astimezone(IST)
    text = str(val).strip()
    for fmt, size in (("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d", 10)):
        try:
            return datetime.strptime(text[:size], fmt).replace(tzinfo=IST)
        except ValueError:
            continue
    return None


def _within_7_days(val) -> bool:
    dt = _as_ist(val)
    if not dt:
        return False
    days = (now_ist().date() - dt.date()).days
    return 0 <= days <= 7


def _fmt_notice_date(val) -> str:
    dt = _as_ist(val)
    if not dt:
        return ""
    return dt.strftime("%d %b %Y")


def _acked(cursor, user_id: int, task_id: int, ack_key: str) -> bool:
    cursor.execute(
        """
        SELECT ack_id FROM task_sop_ack
        WHERE user_id=%s AND task_id=%s AND ack_key=%s
        LIMIT 1
        """,
        (int(user_id), int(task_id), str(ack_key)[:120]),
    )
    return bool(cursor.fetchone())


def _notice_for(cursor, user_id: int, sop):
    if not sop:
        return None
    task_id = sop["task_id"]
    items = []
    ack_keys = []
    if sop.get("has_draft"):
        is_new = not sop.get("has_approved")
        when = sop.get("draft_updated_at") or sop.get("created_at")
        key = f"draft:{when or sop['task_sop_id']}"
        items.append({
            "kind": "new" if is_new else "updated",
            "date": _fmt_notice_date(when),
        })
        ack_keys.append(key)
    live_at = sop.get("approved_at") or sop.get("created_at")
    if sop.get("has_approved") and _within_7_days(live_at) and not sop.get("has_draft"):
        approved_dt = _as_ist(sop.get("approved_at"))
        created_dt = _as_ist(sop.get("created_at"))
        is_update = bool(
            approved_dt
            and created_dt
            and abs((approved_dt - created_dt).total_seconds()) > 60
        )
        key = f"live:{live_at or sop['task_sop_id']}"
        items.append({
            "kind": "updated" if is_update else "new",
            "date": _fmt_notice_date(live_at),
        })
        ack_keys.append(key)
    if not items:
        return None
    return {"show": True, "ack_keys": ack_keys, "items": items}


def _fetch_sop_row(cursor, task_id: int):
    cursor.execute(
        """
        SELECT task_sop_id, task_id, title, original_file_url, original_file_name,
               html_body, created_by, updated_by, created_at, updated_at,
               draft_html_body, draft_file_url, draft_file_name, draft_change_note,
               draft_updated_by, draft_updated_at, approved_by, approved_at, change_note
        FROM task_sop
        WHERE task_id=%s AND is_delete=1
        ORDER BY task_sop_id DESC
        LIMIT 1
        """,
        (int(task_id),),
    )
    return cursor.fetchone()


def _move_unapproved_live_to_draft(cursor, row):
    """SOPs never approved must not look live. Copy live file into draft if needed."""
    if not row or row.get("approved_at"):
        return False
    live_html = (row.get("html_body") or "").strip()
    live_url = row.get("original_file_url")
    if not live_html and not live_url:
        return False
    draft_html = (row.get("draft_html_body") or "").strip()
    draft_url = row.get("draft_file_url")
    if not draft_html and not draft_url:
        cursor.execute(
            """
            UPDATE task_sop
            SET draft_html_body=html_body,
                draft_file_url=original_file_url,
                draft_file_name=original_file_name,
                draft_change_note=COALESCE(NULLIF(draft_change_note, ''), NULLIF(change_note, ''), 'Initial SOP'),
                draft_updated_at=COALESCE(draft_updated_at, updated_at, created_at),
                draft_updated_by=COALESCE(draft_updated_by, updated_by, created_by),
                html_body=NULL,
                original_file_url=NULL,
                original_file_name=NULL
            WHERE task_sop_id=%s
            """,
            (row["task_sop_id"],),
        )
        return True
    cursor.execute(
        """
        UPDATE task_sop
        SET html_body=NULL, original_file_url=NULL, original_file_name=NULL
        WHERE task_sop_id=%s
        """,
        (row["task_sop_id"],),
    )
    return True


def _draft_maker_id(row):
    if not row:
        return None
    for key in ("draft_updated_by", "created_by"):
        try:
            if row.get(key) is not None:
                return int(row[key])
        except (TypeError, ValueError):
            continue
    return None


def _archive_live_sop(cursor, row, archived_by, archived_at) -> None:
    """Keep the previous approved Word/HTML when a new draft is approved. No UI."""
    if not row:
        return
    has_live = bool(
        row.get("approved_at")
        and ((row.get("html_body") or "").strip() or row.get("original_file_url"))
    )
    if not has_live:
        return
    cursor.execute(
        "SELECT COALESCE(MAX(version_no), 0) AS n FROM task_sop_history WHERE task_id=%s",
        (int(row["task_id"]),),
    )
    next_no = int((cursor.fetchone() or {}).get("n") or 0) + 1
    cursor.execute(
        """
        INSERT INTO task_sop_history
        (task_id, task_sop_id, version_no, title, original_file_url, original_file_name,
         html_body, change_note, approved_by, approved_at, archived_by, archived_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            int(row["task_id"]),
            row.get("task_sop_id"),
            next_no,
            (row.get("title") or "")[:250],
            row.get("original_file_url"),
            row.get("original_file_name"),
            row.get("html_body"),
            row.get("change_note"),
            row.get("approved_by"),
            row.get("approved_at"),
            archived_by,
            archived_at,
        ),
    )


def _can_approve_draft(row, viewer_id) -> bool:
    maker = _draft_maker_id(row)
    if maker is None or viewer_id is None:
        return True
    try:
        return int(maker) != int(viewer_id)
    except (TypeError, ValueError):
        return True


def _load_for_task(cursor, task_id: int, viewer_id=None):
    row = _fetch_sop_row(cursor, int(task_id))
    if _move_unapproved_live_to_draft(cursor, row):
        row = _fetch_sop_row(cursor, int(task_id))
    return _serialize_sop(row, viewer_id)


def _serialize_sop(row, viewer_id=None):
    if not row:
        return None
    out = dict(row)
    out["has_approved"] = bool(
        row.get("approved_at")
        and ((row.get("html_body") or "").strip() or row.get("original_file_url"))
    )
    out["has_draft"] = bool((row.get("draft_html_body") or "").strip() or row.get("draft_file_url"))
    out["can_approve"] = bool(out["has_draft"] and _can_approve_draft(row, viewer_id))
    return out


def _safe_stem(filename: str) -> str:
    base = os.path.splitext(os.path.basename(filename or "sop"))[0]
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", base).strip("_")[:60]
    return f"{stem or 'task_sop'}_{uuid.uuid4().hex[:8]}"


@task_sop_bp.route("/get", methods=["POST"])
def get_task_sop():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user(data)
    if err:
        return err
    task_id = data.get("task_id")
    if not task_id:
        return api_response(400, "task_id is required")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ctx = get_role_context(cursor, user_id)
        if not ctx.get("user_role_name"):
            return api_response(404, "User not found")
        _ensure_table(cursor)
        conn.commit()
        sop = _load_for_task(cursor, int(task_id), user_id)
        return api_response(200, "Task SOP loaded", {
            "sop": sop,
            "notice": _notice_for(cursor, user_id, sop),
            "can_manage": _can_manage(ctx.get("user_role_name"), ctx.get("user_role_id")),
        })
    except Exception as exc:
        return api_response(500, f"Failed to load task SOP: {exc}")
    finally:
        cursor.close()
        conn.close()


@task_sop_bp.route("/save", methods=["POST"])
def save_task_sop():
    if request.content_type and "multipart/form-data" in request.content_type:
        data = request.form
        upload = request.files.get("file")
    else:
        data = request.get_json(silent=True) or {}
        upload = None

    user_id, err = _require_user(data)
    if err:
        return err
    task_id = data.get("task_id")
    if not task_id:
        return api_response(400, "task_id is required")
    change_note = (data.get("change_note") or "").strip()[:500]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ctx = get_role_context(cursor, user_id)
        if not ctx.get("user_role_name"):
            return api_response(404, "User not found")
        if not _can_manage(ctx.get("user_role_name"), ctx.get("user_role_id")):
            return api_response(403, "You do not have permission to edit task SOPs")
        _ensure_table(cursor)
        cursor.execute("SELECT task_id FROM task WHERE task_id=%s", (int(task_id),))
        if not cursor.fetchone():
            return api_response(404, "Task not found")

        existing = _load_for_task(cursor, int(task_id))
        is_update = bool(existing)
        draft_file_url = existing.get("draft_file_url") if existing else None
        draft_file_name = existing.get("draft_file_name") if existing else None
        draft_html = existing.get("draft_html_body") if existing else None
        draft_note = change_note or ((existing or {}).get("draft_change_note") or None)
        if not draft_note:
            draft_note = "Initial SOP"

        if upload and upload.filename:
            ext = os.path.splitext(upload.filename)[1].lower()
            if ext != ".docx":
                return api_response(400, "Only a Word document (.docx) is allowed")
            raw = upload.read()
            if not raw:
                return api_response(400, "The file is empty")
            if len(raw) > MAX_FILE_BYTES:
                return api_response(413, SOP_FILE_TOO_LARGE_MSG)
            try:
                draft_html = convert_docx_to_html(raw, save_image=save_sop_image)
            except Exception as conv_err:
                return api_response(400, f"Could not convert this Word document to HTML: {conv_err}")
            html_len = len((draft_html or "").encode("utf-8"))
            if html_len > MAX_SOP_HTML_BYTES:
                return api_response(413, SOP_HTML_TOO_LARGE_MSG)
            draft_file_name = os.path.basename(upload.filename)[:255]
            display_name = f"{_safe_stem(upload.filename)}.docx"
            draft_file_url, _public_id = upload_to_cloudinary(
                BytesIO(raw),
                FOLDER_TASK_SOP,
                display_name=display_name,
                resource_type="raw",
            )
        elif not (draft_html or draft_file_url):
            return api_response(400, "Upload a Word document (.docx) to save as draft")

        now = now_str()
        title = (existing or {}).get("title") or os.path.splitext(draft_file_name or "Task SOP")[0][:250]
        if existing:
            cursor.execute(
                """
                UPDATE task_sop
                SET draft_html_body=%s, draft_file_url=%s, draft_file_name=%s,
                    draft_change_note=%s, draft_updated_by=%s, draft_updated_at=%s,
                    updated_by=%s, updated_at=%s
                WHERE task_sop_id=%s AND is_delete=1
                """,
                (
                    draft_html, draft_file_url, draft_file_name, draft_note,
                    user_id, now, user_id, now, existing["task_sop_id"],
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO task_sop (
                    task_id, title, original_file_url, original_file_name, html_body,
                    draft_html_body, draft_file_url, draft_file_name, draft_change_note,
                    draft_updated_by, draft_updated_at,
                    created_by, updated_by, is_delete, created_at, updated_at
                ) VALUES (%s,%s,NULL,NULL,NULL,%s,%s,%s,%s,%s,%s,%s,%s,1,%s,%s)
                """,
                (
                    int(task_id), title, draft_html, draft_file_url, draft_file_name,
                    draft_note, user_id, now, user_id, user_id, now, now,
                ),
            )
        conn.commit()
        sop = _load_for_task(cursor, int(task_id), user_id)
        mail = _notify_draft_ready(cursor, int(task_id), user_id, "updated" if is_update else "added")
        return api_response(200, "SOP saved as draft. It is not live until someone approves it.", {
            "sop": sop,
            "can_manage": True,
            "email_sent": mail.get("email_sent"),
            "email_count": mail.get("email_count"),
        })
    except Exception as exc:
        conn.rollback()
        return api_response(500, f"Failed to save task SOP: {exc}")
    finally:
        cursor.close()
        conn.close()


@task_sop_bp.route("/approve", methods=["POST"])
def approve_task_sop():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user(data)
    if err:
        return err
    task_id = data.get("task_id")
    if not task_id:
        return api_response(400, "task_id is required")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ctx = get_role_context(cursor, user_id)
        if not ctx.get("user_role_name"):
            return api_response(404, "User not found")
        if not _can_manage(ctx.get("user_role_name"), ctx.get("user_role_id")):
            return api_response(403, "You do not have permission to approve task SOPs")
        _ensure_table(cursor)
        existing = _load_for_task(cursor, int(task_id), user_id)
        if not existing or not existing.get("has_draft"):
            return api_response(400, "There is no draft SOP to approve")
        if not existing.get("can_approve"):
            return api_response(
                403,
                "You cannot approve a SOP you added. Another Assistant Manager, Project Manager, Admin, Super Admin, or QA must approve it.",
            )

        maker_id = existing.get("draft_updated_by") or existing.get("created_by")
        now = now_str()
        _archive_live_sop(cursor, existing, user_id, now)
        title = os.path.splitext(existing.get("draft_file_name") or existing.get("title") or "Task SOP")[0][:250]
        cursor.execute(
            """
            UPDATE task_sop
            SET title=%s,
                html_body=%s,
                original_file_url=%s,
                original_file_name=%s,
                approved_by=%s,
                approved_at=%s,
                change_note=%s,
                draft_html_body=NULL,
                draft_file_url=NULL,
                draft_file_name=NULL,
                draft_change_note=NULL,
                draft_updated_by=NULL,
                draft_updated_at=NULL,
                updated_by=%s,
                updated_at=%s
            WHERE task_sop_id=%s AND is_delete=1
            """,
            (
                title,
                existing.get("draft_html_body"),
                existing.get("draft_file_url"),
                existing.get("draft_file_name"),
                user_id,
                now,
                existing.get("draft_change_note") or "Initial SOP",
                user_id,
                now,
                existing["task_sop_id"],
            ),
        )
        conn.commit()
        sop = _load_for_task(cursor, int(task_id), user_id)
        mail = _notify_approved(cursor, int(task_id), user_id, maker_id)
        return api_response(200, "SOP approved. Agents now see this version.", {
            "sop": sop,
            "can_manage": True,
            "email_sent": mail.get("email_sent"),
            "email_count": mail.get("email_count"),
        })
    except Exception as exc:
        conn.rollback()
        return api_response(500, f"Failed to approve task SOP: {exc}")
    finally:
        cursor.close()
        conn.close()


@task_sop_bp.route("/ack", methods=["POST"])
def ack_task_sop_notice():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user(data)
    if err:
        return err
    task_id = data.get("task_id")
    ack_keys = data.get("ack_keys") or []
    if not task_id:
        return api_response(400, "task_id is required")
    if isinstance(ack_keys, str):
        ack_keys = [ack_keys]
    if not ack_keys:
        return api_response(400, "ack_keys is required")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ctx = get_role_context(cursor, user_id)
        if not ctx.get("user_role_name"):
            return api_response(404, "User not found")
        _ensure_table(cursor)
        now = now_str()
        for key in ack_keys:
            cursor.execute(
                """
                INSERT INTO task_sop_ack (user_id, task_id, ack_key, acked_at)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE acked_at=VALUES(acked_at)
                """,
                (user_id, int(task_id), str(key)[:120], now),
            )
        conn.commit()
        return api_response(200, "SOP notice acknowledged")
    except Exception as exc:
        conn.rollback()
        return api_response(500, f"Failed to save SOP acknowledgement: {exc}")
    finally:
        cursor.close()
        conn.close()


@task_sop_bp.route("/discard_draft", methods=["POST"])
def discard_draft_sop():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user(data)
    if err:
        return err
    task_id = data.get("task_id")
    if not task_id:
        return api_response(400, "task_id is required")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ctx = get_role_context(cursor, user_id)
        if not _can_manage(ctx.get("user_role_name"), ctx.get("user_role_id")):
            return api_response(403, "You do not have permission to edit task SOPs")
        _ensure_table(cursor)
        existing = _load_for_task(cursor, int(task_id))
        if not existing:
            return api_response(404, "Task SOP not found")
        now = now_str()
        if not existing.get("has_approved"):
            cursor.execute(
                "UPDATE task_sop SET is_delete=0, updated_at=%s, updated_by=%s WHERE task_sop_id=%s",
                (now, user_id, existing["task_sop_id"]),
            )
        else:
            cursor.execute(
                """
                UPDATE task_sop
                SET draft_html_body=NULL, draft_file_url=NULL, draft_file_name=NULL,
                    draft_change_note=NULL, draft_updated_by=NULL, draft_updated_at=NULL,
                    updated_by=%s, updated_at=%s
                WHERE task_sop_id=%s AND is_delete=1
                """,
                (user_id, now, existing["task_sop_id"]),
            )
        conn.commit()
        sop = _load_for_task(cursor, int(task_id))
        return api_response(200, "Draft discarded", {"sop": sop, "can_manage": True})
    except Exception as exc:
        conn.rollback()
        return api_response(500, f"Failed to discard draft: {exc}")
    finally:
        cursor.close()
        conn.close()


@task_sop_bp.route("/pending", methods=["POST"])
def pending_task_sops():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user(data)
    if err:
        return err
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ctx = get_role_context(cursor, user_id)
        if not ctx.get("user_role_name"):
            return api_response(404, "User not found")
        if not _can_manage(ctx.get("user_role_name"), ctx.get("user_role_id")):
            return api_response(200, "Pending SOP drafts", {"pending": []})
        _ensure_table(cursor)
        conn.commit()
        project_id = data.get("project_id")
        sql = """
            SELECT s.task_sop_id, s.task_id, s.draft_file_name, s.draft_file_url,
                   s.draft_html_body, s.draft_change_note, s.draft_updated_at, s.approved_at,
                   s.draft_updated_by, s.created_by,
                   t.task_name, t.project_id, p.project_name
            FROM task_sop s
            JOIN task t ON t.task_id = s.task_id
            JOIN project p ON p.project_id = t.project_id
            WHERE s.is_delete=1
              AND (s.draft_file_url IS NOT NULL OR (s.draft_html_body IS NOT NULL AND TRIM(s.draft_html_body) <> ''))
        """
        params = []
        if project_id:
            sql += " AND t.project_id=%s"
            params.append(int(project_id))
        sql += " ORDER BY s.draft_updated_at DESC, s.task_sop_id DESC"
        cursor.execute(sql, tuple(params))
        pending = []
        for row in cursor.fetchall() or []:
            item = dict(row)
            item["can_approve"] = _can_approve_draft(item, user_id)
            pending.append(item)
        return api_response(200, "Pending SOP drafts", {"pending": pending})
    except Exception as exc:
        return api_response(500, f"Failed to load pending SOP drafts: {exc}")
    finally:
        cursor.close()
        conn.close()


@task_sop_bp.route("/delete", methods=["POST"])
def delete_task_sop():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user(data)
    if err:
        return err
    task_id = data.get("task_id")
    if not task_id:
        return api_response(400, "task_id is required")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ctx = get_role_context(cursor, user_id)
        if not _can_manage(ctx.get("user_role_name"), ctx.get("user_role_id")):
            return api_response(403, "You do not have permission to edit task SOPs")
        _ensure_table(cursor)
        now = now_str()
        cursor.execute(
            "UPDATE task_sop SET is_delete=0, updated_at=%s, updated_by=%s WHERE task_id=%s AND is_delete=1",
            (now, user_id, int(task_id)),
        )
        conn.commit()
        return api_response(200, "Task SOP removed", {"sop": None, "can_manage": True})
    except Exception as exc:
        conn.rollback()
        return api_response(500, f"Failed to remove task SOP: {exc}")
    finally:
        cursor.close()
        conn.close()

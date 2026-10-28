# routes/sop.py
# Organization SOP library: topics, each holding a link or an uploaded document.

from __future__ import annotations

import os
import re
import uuid

from flask import Blueprint, request

from config import get_db_connection
from utils.cloudinary_utils import upload_to_cloudinary
from utils.response import api_response
from utils.roster_helpers import get_role_context, now_str

sop_bp = Blueprint("sop", __name__)

FOLDER_SOP = "hrms/sop_files"
MAX_FILE_BYTES = 25 * 1024 * 1024
BLOCKED_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".com", ".msi", ".js", ".html", ".htm",
    ".php", ".sh", ".ps1", ".vbs",
}


def _require_user(data: dict):
    logged_in_user_id = data.get("logged_in_user_id")
    if not logged_in_user_id:
        return None, api_response(400, "logged_in_user_id is required")
    try:
        return int(logged_in_user_id), None
    except (TypeError, ValueError):
        return None, api_response(400, "logged_in_user_id is required")


def _can_manage(role_name: str, role_id) -> bool:
    """Admin, Super Admin and Project Manager may add or edit. Everyone else can view."""
    name = (role_name or "").strip().lower()
    try:
        if int(role_id) in (1, 2, 3):
            return True
    except (TypeError, ValueError):
        pass
    return name in ("admin", "super admin", "project manager")


def _ensure_tables(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sop_topic (
            sop_topic_id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            description TEXT NULL,
            sort_order INT NOT NULL DEFAULT 0,
            created_by INT NULL,
            is_delete TINYINT NOT NULL DEFAULT 1,
            created_at DATETIME NULL,
            updated_at DATETIME NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sop_item (
            sop_item_id INT AUTO_INCREMENT PRIMARY KEY,
            sop_topic_id INT NOT NULL,
            title VARCHAR(250) NOT NULL,
            item_type VARCHAR(10) NOT NULL,
            link_url VARCHAR(1000) NULL,
            file_url VARCHAR(1000) NULL,
            file_name VARCHAR(255) NULL,
            sort_order INT NOT NULL DEFAULT 0,
            created_by INT NULL,
            is_delete TINYINT NOT NULL DEFAULT 1,
            created_at DATETIME NULL,
            updated_at DATETIME NULL,
            INDEX idx_sop_item_topic (sop_topic_id)
        )
        """
    )


def _load_library(cursor) -> list:
    cursor.execute(
        """
        SELECT sop_topic_id, title, description, sort_order, created_by, created_at, updated_at
        FROM sop_topic
        WHERE is_delete=1
        ORDER BY sort_order ASC, sop_topic_id ASC
        """
    )
    topics = cursor.fetchall() or []
    cursor.execute(
        """
        SELECT sop_item_id, sop_topic_id, title, item_type, link_url, file_url,
               file_name, sort_order, created_by, created_at, updated_at
        FROM sop_item
        WHERE is_delete=1
        ORDER BY sort_order ASC, sop_item_id ASC
        """
    )
    items = cursor.fetchall() or []
    by_topic = {}
    for item in items:
        by_topic.setdefault(item["sop_topic_id"], []).append(item)
    for topic in topics:
        topic["items"] = by_topic.get(topic["sop_topic_id"], [])
    return topics


@sop_bp.route("/list", methods=["POST"])
def list_sops():
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
        _ensure_tables(cursor)
        conn.commit()
        topics = _load_library(cursor)
        return api_response(200, "SOP library loaded", {
            "topics": topics,
            "can_manage": _can_manage(ctx.get("user_role_name"), ctx.get("user_role_id")),
        })
    except Exception as exc:
        return api_response(500, f"Failed to load SOPs: {exc}")
    finally:
        cursor.close()
        conn.close()


@sop_bp.route("/topic/save", methods=["POST"])
def save_topic():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user(data)
    if err:
        return err

    title = str(data.get("title") or "").strip()
    if not title:
        return api_response(400, "Topic title is required")
    if len(title) > 200:
        return api_response(400, "Topic title is too long")
    description = str(data.get("description") or "").strip() or None
    topic_id = data.get("sop_topic_id")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ctx = get_role_context(cursor, user_id)
        if not ctx.get("user_role_name"):
            return api_response(404, "User not found")
        if not _can_manage(ctx.get("user_role_name"), ctx.get("user_role_id")):
            return api_response(403, "You do not have permission to edit SOPs")
        _ensure_tables(cursor)
        now = now_str()
        if topic_id:
            cursor.execute(
                """
                UPDATE sop_topic
                SET title=%s, description=%s, updated_at=%s
                WHERE sop_topic_id=%s AND is_delete=1
                """,
                (title, description, now, int(topic_id)),
            )
            if cursor.rowcount == 0:
                return api_response(404, "Topic not found")
        else:
            cursor.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 AS next_order FROM sop_topic")
            next_order = (cursor.fetchone() or {}).get("next_order") or 1
            cursor.execute(
                """
                INSERT INTO sop_topic (title, description, sort_order, created_by, is_delete, created_at, updated_at)
                VALUES (%s, %s, %s, %s, 1, %s, %s)
                """,
                (title, description, next_order, user_id, now, now),
            )
        conn.commit()
        return api_response(200, "Topic saved", {"topics": _load_library(cursor)})
    except Exception as exc:
        conn.rollback()
        return api_response(500, f"Failed to save topic: {exc}")
    finally:
        cursor.close()
        conn.close()


@sop_bp.route("/topic/delete", methods=["POST"])
def delete_topic():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user(data)
    if err:
        return err
    topic_id = data.get("sop_topic_id")
    if not topic_id:
        return api_response(400, "sop_topic_id is required")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ctx = get_role_context(cursor, user_id)
        if not _can_manage(ctx.get("user_role_name"), ctx.get("user_role_id")):
            return api_response(403, "You do not have permission to edit SOPs")
        _ensure_tables(cursor)
        now = now_str()
        cursor.execute(
            "UPDATE sop_topic SET is_delete=0, updated_at=%s WHERE sop_topic_id=%s AND is_delete=1",
            (now, int(topic_id)),
        )
        cursor.execute(
            "UPDATE sop_item SET is_delete=0, updated_at=%s WHERE sop_topic_id=%s AND is_delete=1",
            (now, int(topic_id)),
        )
        conn.commit()
        return api_response(200, "Topic removed", {"topics": _load_library(cursor)})
    except Exception as exc:
        conn.rollback()
        return api_response(500, f"Failed to remove topic: {exc}")
    finally:
        cursor.close()
        conn.close()


def _safe_stem(filename: str) -> str:
    base = os.path.splitext(os.path.basename(filename or "sop"))[0]
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", base).strip("_")[:60]
    return f"{stem or 'sop'}_{uuid.uuid4().hex[:8]}"


@sop_bp.route("/item/save", methods=["POST"])
def save_item():
    if request.content_type and "multipart/form-data" in request.content_type:
        data = request.form
        upload = request.files.get("file")
    else:
        data = request.get_json(silent=True) or {}
        upload = None

    user_id, err = _require_user(data)
    if err:
        return err

    title = str(data.get("title") or "").strip()
    topic_id = data.get("sop_topic_id")
    item_type = str(data.get("item_type") or "").strip().lower()
    if not title:
        return api_response(400, "Title is required")
    if len(title) > 250:
        return api_response(400, "Title is too long")
    if not topic_id:
        return api_response(400, "Choose a topic")
    if item_type not in ("link", "file"):
        return api_response(400, "Choose a link or a file")

    link_url = str(data.get("link_url") or "").strip()
    if item_type == "link":
        if not link_url:
            return api_response(400, "Link is required")
        if not re.match(r"^https?://", link_url, re.I):
            return api_response(400, "Link must start with http:// or https://")
        upload = None

    file_url = None
    file_name = None
    if item_type == "file":
        if not upload or not upload.filename:
            return api_response(400, "Choose a file to upload")
        ext = os.path.splitext(upload.filename)[1].lower()
        if ext in BLOCKED_EXTENSIONS:
            return api_response(400, "This file type is not allowed")
        upload.stream.seek(0, os.SEEK_END)
        size = upload.stream.tell()
        upload.stream.seek(0)
        if size <= 0:
            return api_response(400, "The file is empty")
        if size > MAX_FILE_BYTES:
            return api_response(400, "File is larger than 25 MB")
        file_name = os.path.basename(upload.filename)[:255]
        # Keep the extension on the stored file so Word, PowerPoint, and PDF open it.
        display_name = f"{_safe_stem(upload.filename)}{ext}" if ext else _safe_stem(upload.filename)
        file_url, _public_id = upload_to_cloudinary(
            upload,
            FOLDER_SOP,
            display_name=display_name,
            resource_type="raw",
        )

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ctx = get_role_context(cursor, user_id)
        if not _can_manage(ctx.get("user_role_name"), ctx.get("user_role_id")):
            return api_response(403, "You do not have permission to edit SOPs")
        _ensure_tables(cursor)
        cursor.execute(
            "SELECT sop_topic_id FROM sop_topic WHERE sop_topic_id=%s AND is_delete=1",
            (int(topic_id),),
        )
        if not cursor.fetchone():
            return api_response(404, "Topic not found")
        now = now_str()
        cursor.execute(
            "SELECT COALESCE(MAX(sort_order), 0) + 1 AS next_order FROM sop_item WHERE sop_topic_id=%s",
            (int(topic_id),),
        )
        next_order = (cursor.fetchone() or {}).get("next_order") or 1
        cursor.execute(
            """
            INSERT INTO sop_item (
                sop_topic_id, title, item_type, link_url, file_url, file_name,
                sort_order, created_by, is_delete, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s)
            """,
            (
                int(topic_id),
                title,
                item_type,
                link_url if item_type == "link" else None,
                file_url,
                file_name,
                next_order,
                user_id,
                now,
                now,
            ),
        )
        conn.commit()
        return api_response(200, "SOP saved", {"topics": _load_library(cursor)})
    except Exception as exc:
        conn.rollback()
        return api_response(500, f"Failed to save SOP: {exc}")
    finally:
        cursor.close()
        conn.close()


@sop_bp.route("/item/delete", methods=["POST"])
def delete_item():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user(data)
    if err:
        return err
    item_id = data.get("sop_item_id")
    if not item_id:
        return api_response(400, "sop_item_id is required")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ctx = get_role_context(cursor, user_id)
        if not _can_manage(ctx.get("user_role_name"), ctx.get("user_role_id")):
            return api_response(403, "You do not have permission to edit SOPs")
        _ensure_tables(cursor)
        now = now_str()
        cursor.execute(
            "UPDATE sop_item SET is_delete=0, updated_at=%s WHERE sop_item_id=%s AND is_delete=1",
            (now, int(item_id)),
        )
        if cursor.rowcount == 0:
            return api_response(404, "SOP not found")
        conn.commit()
        return api_response(200, "SOP removed", {"topics": _load_library(cursor)})
    except Exception as exc:
        conn.rollback()
        return api_response(500, f"Failed to remove SOP: {exc}")
    finally:
        cursor.close()
        conn.close()

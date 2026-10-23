from flask import Blueprint, request
from utils.response import api_response
from config import get_db_connection
from utils.cloudinary_utils import upload_to_cloudinary, delete_from_cloudinary, FOLDER_PROJECT
from utils.file_utils import is_allowed_file
from utils.roster_helpers import reject_read_only_actor
import json
import re
from datetime import datetime

project_bp = Blueprint("project", __name__)


def _reject_read_only_from_request(form_or_data) -> object | None:
    actor_id = None
    if form_or_data is not None:
        actor_id = form_or_data.get("logged_in_user_id") or form_or_data.get("user_id")
    if not actor_id:
        return None
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        return reject_read_only_actor(cursor, actor_id)
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

# ---------------- HELPERS ---------------- #

def safe_filename_part(value: str):
    if not value:
        return "NA"
    return value.strip().replace(" ", "_")


def build_project_filename(project_name, project_code, original_filename, index, total):
    ext = original_filename.rsplit(".", 1)[1].lower()
    date_part = datetime.now().strftime("%d-%b-%Y")

    name_part = safe_filename_part(project_name)
    code_part = safe_filename_part(project_code)

    suffix = f"_{index}" if total > 1 else ""

    return f"{name_part}_{code_part}_{date_part}{suffix}.{ext}"


def parse_db_files(val):

    if not val:
        return []

    if isinstance(val, list):
        return val

    if isinstance(val, str):
        try:
            return json.loads(val)
        except:
            return [val]

    return []


def safe_delete_cloudinary_project_files(file_list):

    for f in file_list or []:
        try:
            delete_from_cloudinary(f, resource_type="raw")
        except Exception as e:
            print("Cloudinary delete failed:", e)


def _get_json_list(form, key):

    raw = form.get(key)

    if not raw:
        return []

    try:
        val = json.loads(raw)
        if isinstance(val, list):
            return val
    except:
        pass

    return []


def _get_uploaded_files():
    files = request.files.getlist("files")
    if not files:
        files = request.files.getlist("file")
    return [f for f in files if f and f.filename]


MAX_SOP_LINKS = 20
_sop_links_column_ready = False


def _ensure_sop_links_column(cursor) -> None:
    """Shared-drive SOP links live in their own column so project files stay unchanged."""
    global _sop_links_column_ready
    if _sop_links_column_ready:
        return
    cursor.execute("SHOW COLUMNS FROM project LIKE 'project_sop_links'")
    if not cursor.fetchall():
        cursor.execute("ALTER TABLE project ADD COLUMN project_sop_links TEXT NULL")
    _sop_links_column_ready = True


def parse_sop_links(val) -> list:
    if not val:
        return []
    if isinstance(val, (bytes, bytearray)):
        val = val.decode("utf-8", errors="ignore")
    if isinstance(val, str):
        try:
            val = json.loads(val)
        except Exception:
            return []
    if not isinstance(val, list):
        return []
    out = []
    for item in val:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        title = str(item.get("title") or "").strip() or url
        out.append({"title": title, "url": url})
    return out


def _sop_links_from_form(form):
    """Returns (links, error). links is None when the form did not send sop_links."""
    raw = form.get("sop_links")
    if raw is None:
        return None, None
    try:
        items = json.loads(raw) if raw else []
    except Exception:
        return None, "sop_links must be a JSON list"
    if not isinstance(items, list):
        return None, "sop_links must be a JSON list"
    links = []
    for item in items:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        title = str(item.get("title") or "").strip()
        if not url and not title:
            continue
        if not re.match(r"^https?://", url, re.I):
            return None, f"SOP link must start with http:// or https:// ({title or url})"
        links.append({"title": (title or url)[:250], "url": url[:1000]})
    if len(links) > MAX_SOP_LINKS:
        return None, f"A project can have at most {MAX_SOP_LINKS} SOP links"
    return links, None


# ---------------- CREATE PROJECT ---------------- #

def _reject_without_project_permission(form) -> object | None:
    """Same rule as the website's canManageProjects (AuthContext.jsx)."""
    actor_id = form.get("logged_in_user_id")
    if not actor_id:
        return None
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT u.role_id, LOWER(TRIM(r.role_name)) AS role_name, p.project_creation_permission
            FROM tfs_user u
            LEFT JOIN user_role r ON r.role_id = u.role_id
            LEFT JOIN user_permission p ON p.user_id = u.user_id
            WHERE u.user_id = %s
            ORDER BY p.project_creation_permission DESC
            LIMIT 1
            """,
            (int(actor_id),),
        )
        actor = cursor.fetchone() or {}
    finally:
        cursor.close()
        conn.close()

    try:
        role_id = int(actor.get("role_id") or 0)
    except (TypeError, ValueError):
        role_id = 0
    role_name = (actor.get("role_name") or "").strip()
    is_team_leader = role_id == 7 or "team leader" in role_name
    is_assistant_manager = not is_team_leader and (
        role_id == 4 or "assistant" in role_name or "asst" in role_name
    )
    allowed = not is_team_leader and (
        str(actor.get("project_creation_permission")).strip() == "1"
        or role_id in (1, 2, 3, 4)
        or role_name in ("admin", "super admin")
        or "project manager" in role_name
        or is_assistant_manager
    )
    if not allowed:
        return api_response(403, "You do not have permission to create projects")
    return None


@project_bp.route("/create", methods=["POST"])
def create_project():

    form = request.form
    deny = _reject_read_only_from_request(form) or _reject_without_project_permission(form)
    if deny:
        return deny

    required_fields = ["project_name", "project_code"]

    for f in required_fields:
        if not form.get(f):
            return api_response(400, f"{f} is required")

    project_name = form.get("project_name").strip()
    project_code = form.get("project_code").strip()
    project_description = form.get("project_description")

    if project_description == "null":
        project_description = None

    project_manager_id = form.get("project_manager_id")

    asst_project_manager_id = _get_json_list(form, "asst_project_manager_id")
    project_team_id = _get_json_list(form, "project_team_id")
    project_qa_id = _get_json_list(form, "project_qa_id")

    project_category_id = form.get("project_category_id")

    # NEW FLAGS
    requires_ai_evaluation = str(form.get("requires_ai_evaluation", "false")).lower() in ("true", "1")
    requires_duplicate_check = str(form.get("requires_duplicate_check", "false")).lower() in ("true", "1")

    sop_links, sop_err = _sop_links_from_form(form)
    if sop_err:
        return api_response(400, sop_err)

    uploaded_files = _get_uploaded_files()

    saved_urls = []

    try:

        total = len(uploaded_files)

        for idx, fs in enumerate(uploaded_files, start=1):

            if not is_allowed_file(fs.filename):
                raise ValueError(f"Unsupported file type: {fs.filename}")

            custom_name = build_project_filename(
                project_name,
                project_code,
                fs.filename,
                idx,
                total
            )

            url, _ = upload_to_cloudinary(
                fs,
                FOLDER_PROJECT,
                display_name=custom_name,
                resource_type="raw"
            )

            saved_urls.append(url)

    except Exception as e:

        safe_delete_cloudinary_project_files(saved_urls)

        return api_response(400, f"File upload failed: {str(e)}")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:

        _ensure_sop_links_column(cursor)
        conn.start_transaction()

        cursor.execute(
            """
            INSERT INTO project (
                project_name,
                project_code,
                project_description,
                project_manager_id,
                asst_project_manager_id,
                project_team_id,
                project_qa_id,
                project_pprt,
                project_sop_links,
                project_category_id,
                ai_evaluation,
                duplicate_check,
                created_date,
                updated_date,
                is_active
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1)
            """,
            (
                project_name,
                project_code,
                project_description,
                project_manager_id,
                json.dumps(asst_project_manager_id),
                json.dumps(project_team_id),
                json.dumps(project_qa_id),
                json.dumps(saved_urls),
                json.dumps(sop_links or []),
                project_category_id,
                requires_ai_evaluation,
                requires_duplicate_check,
                now,
                now
            )
        )

        conn.commit()

        return api_response(
            201,
            "Project created successfully",
            {
                "files": saved_urls,
                "requires_ai_evaluation": requires_ai_evaluation,
                "requires_duplicate_check": requires_duplicate_check
            }
        )

    except Exception as e:

        conn.rollback()
        safe_delete_cloudinary_project_files(saved_urls)

        return api_response(500, f"Project creation failed: {str(e)}")

    finally:

        cursor.close()
        conn.close()


# ---------------- UPDATE PROJECT ---------------- #

@project_bp.route("/update", methods=["POST"])
def update_project():

    form = request.form
    deny = _reject_read_only_from_request(form)
    if deny:
        return deny
    project_id = form.get("project_id")

    if not project_id:
        return api_response(400, "project_id is required")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    saved_urls = []

    try:

        cursor.execute(
            "SELECT * FROM project WHERE project_id=%s",
            (project_id,)
        )

        existing = cursor.fetchone()

        if not existing:
            return api_response(404, "Project not found")

        update_values = {}

        # normal fields
        for key in [
            "project_name",
            "project_code",
            "project_description",
            "project_manager_id",
            "project_category_id",
        ]:

            if form.get(key) is not None:

                val = form.get(key)

                if key in ["project_name", "project_code"]:
                    val = val.strip()

                if key == "project_description" and val == "null":
                    val = None

                update_values[key] = val
        
        # json list fields
        for key in [
            "asst_project_manager_id",
            "project_team_id",
            "project_qa_id",
        ]:
            if form.get(key) is not None:
                update_values[key] = json.dumps(_get_json_list(form, key))


        # FLAG MAPPING (API -> DB)

        if form.get("requires_ai_evaluation") is not None:
            update_values["ai_evaluation"] = str(form.get("requires_ai_evaluation")).lower() in ("true", "1")

        if form.get("requires_duplicate_check") is not None:
            update_values["duplicate_check"] = str(form.get("requires_duplicate_check")).lower() in ("true", "1")

        sop_links, sop_err = _sop_links_from_form(form)
        if sop_err:
            return api_response(400, sop_err)
        if sop_links is not None:
            _ensure_sop_links_column(cursor)
            update_values["project_sop_links"] = json.dumps(sop_links)

        # Project files: existing_files = URLs to keep (when sent); new uploads are appended.
        uploaded_files = _get_uploaded_files()
        if uploaded_files or form.get("existing_files") is not None:
            current_files = parse_db_files(existing.get("project_pprt"))

            if form.get("existing_files") is not None:
                keep = _get_json_list(form, "existing_files")
                current_files = [f for f in current_files if f in keep]

            project_name = update_values.get("project_name") or existing.get("project_name")
            project_code = update_values.get("project_code") or existing.get("project_code")
            total = len(uploaded_files)

            try:
                for idx, fs in enumerate(uploaded_files, start=1):

                    if not is_allowed_file(fs.filename):
                        raise ValueError(f"Unsupported file type: {fs.filename}")

                    custom_name = build_project_filename(
                        project_name,
                        project_code,
                        fs.filename,
                        idx,
                        total
                    )

                    url, _ = upload_to_cloudinary(
                        fs,
                        FOLDER_PROJECT,
                        display_name=custom_name,
                        resource_type="raw"
                    )

                    saved_urls.append(url)

            except Exception as e:
                safe_delete_cloudinary_project_files(saved_urls)
                return api_response(400, f"File upload failed: {str(e)}")

            update_values["project_pprt"] = json.dumps(current_files + saved_urls)

        # Active / inactive toggle (does not delete files)
        if form.get("is_active") is not None:
            v = form.get("is_active")
            if str(v).strip().isdigit():
                update_values["is_active"] = 1 if int(v) == 1 else 0
            
        if not update_values:
            return api_response(400, "No fields to update")

        set_clause = ", ".join(f"{k}=%s" for k in update_values.keys())

        params = list(update_values.values()) + [project_id]

        cursor.execute(
            f"""
            UPDATE project
            SET {set_clause},
            updated_date = NOW()
            WHERE project_id=%s
            """,
            tuple(params)
        )

        conn.commit()

        return api_response(200, "Project updated successfully")

    except Exception as e:

        conn.rollback()
        safe_delete_cloudinary_project_files(saved_urls)
        return api_response(500, f"Project update failed: {str(e)}")

    finally:

        cursor.close()
        conn.close()


# ---------------- LIST PROJECTS ---------------- #

@project_bp.route("/list", methods=["POST"])
def list_projects():
    data = request.get_json(silent=True) or {}
    # Management screens can pass include_inactive=1 to show Active/Inactive and reactivate.
    # Dropdowns / reports should omit this (default = active only).
    include_inactive = str(data.get("include_inactive") or "").strip().lower() in ("1", "true", "yes")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        _ensure_sop_links_column(cursor)
        where_sql = "" if include_inactive else "WHERE is_active = 1"
        cursor.execute(f"""
            SELECT
                project_id,
                project_name,
                project_code,
                project_description,
                project_manager_id,
                asst_project_manager_id,
                project_team_id,
                project_qa_id,
                project_category_id,
                project_pprt,
                project_sop_links,
                ai_evaluation,
                duplicate_check,
                is_active,
                created_date,
                updated_date
            FROM project
            {where_sql}
            ORDER BY is_active DESC, project_id DESC
        """)

        projects = cursor.fetchall()

        result = []

        for proj in projects:

            result.append({

                "project_id": proj["project_id"],
                "project_name": proj["project_name"],
                "project_code": proj["project_code"],
                "project_description": proj["project_description"],

                "project_manager_id": proj["project_manager_id"],
                "asst_project_manager_id": json.loads(proj.get("asst_project_manager_id") or "[]"),
                "project_team_id": json.loads(proj.get("project_team_id") or "[]"),
                "project_qa_id": json.loads(proj.get("project_qa_id") or "[]"),

                "project_category_id": proj["project_category_id"],

                "project_files": parse_db_files(proj["project_pprt"]),
                "sop_links": parse_sop_links(proj.get("project_sop_links")),

                "requires_ai_evaluation": bool(proj["ai_evaluation"]),
                "requires_duplicate_check": bool(proj["duplicate_check"]),
                "is_active": int(proj.get("is_active") if proj.get("is_active") is not None else 1),

                "created_date": proj["created_date"],
                "updated_date": proj["updated_date"]

            })

        return api_response(200, "Projects fetched successfully", result)

    except Exception as e:

        return api_response(500, f"Failed to fetch projects: {str(e)}")

    finally:

        cursor.close()
        conn.close()


# ---------------- PROJECT SOP LINKS (view only) ---------------- #

@project_bp.route("/sop_links", methods=["POST"])
def project_sop_links():
    """Shared-drive SOP links for one project. Read only; links are managed on Add/Edit Project."""
    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id")
    if not project_id:
        return api_response(400, "project_id is required")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_sop_links_column(cursor)
        cursor.execute(
            "SELECT project_id, project_name, project_sop_links FROM project WHERE project_id=%s",
            (project_id,),
        )
        row = cursor.fetchone()
        if not row:
            return api_response(404, "Project not found")
        return api_response(200, "SOP links fetched", {
            "project_id": row["project_id"],
            "project_name": row["project_name"],
            "sop_links": parse_sop_links(row.get("project_sop_links")),
        })
    except Exception as e:
        return api_response(500, f"Failed to fetch SOP links: {str(e)}")
    finally:
        cursor.close()
        conn.close()


# ---------------- DELETE PROJECT ---------------- #

@project_bp.route("/delete", methods=["POST"])
def delete_project():

    data = request.get_json() or {}
    deny = _reject_read_only_from_request(data)
    if deny:
        return deny

    project_id = data.get("project_id")

    if not project_id:
        return api_response(400, "project_id is required")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        conn.start_transaction()

        cursor.execute(
            "SELECT project_id, project_pprt, is_active FROM project WHERE project_id=%s",
            (project_id,)
        )

        project = cursor.fetchone()

        if not project:
            return api_response(404, "Project not found")

        files = parse_db_files(project.get("project_pprt"))

        cursor.execute(
            "SELECT COUNT(*) AS n FROM task_work_tracker WHERE project_id=%s",
            (project_id,),
        )
        tracker_count = int((cursor.fetchone() or {}).get("n") or 0)

        cursor.execute(
            "SELECT COUNT(*) AS n FROM project_monthly_tracker WHERE project_id=%s",
            (project_id,),
        )
        monthly_count = int((cursor.fetchone() or {}).get("n") or 0)

        # Empty unused projects (typical duplicate / never-used inactive row)
        # can be removed from the list. Anything with history stays deactivated.
        can_remove_row = tracker_count == 0 and monthly_count == 0

        if can_remove_row:
            safe_delete_cloudinary_project_files(files)
            cursor.execute("DELETE FROM task WHERE project_id=%s", (project_id,))
            cursor.execute("DELETE FROM project WHERE project_id=%s", (project_id,))
            conn.commit()
            return api_response(200, "Project deleted successfully")

        cursor.execute(
            """
            UPDATE task
            SET is_active = 0, updated_date = NOW()
            WHERE project_id = %s AND is_active = 1
            """,
            (project_id,),
        )
        cursor.execute(
            """
            UPDATE project
            SET is_active = 0,
                updated_date = NOW()
            WHERE project_id = %s
            """,
            (project_id,),
        )

        conn.commit()

        return api_response(200, "Project deleted successfully")

    except Exception as e:

        conn.rollback()
        return api_response(500, f"Project delete failed: {str(e)}")

    finally:

        cursor.close()
        conn.close()
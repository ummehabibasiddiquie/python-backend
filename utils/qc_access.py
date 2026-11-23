def _permission_flag(cursor, user_id, column: str) -> bool:
    if not user_id:
        return False
    try:
        cursor.execute(
            f"""
            SELECT COALESCE(p.{column}, 0) AS flag
            FROM tfs_user u
            LEFT JOIN user_permission p ON p.user_id = u.user_id
            WHERE u.user_id = %s
            ORDER BY p.{column} DESC
            LIMIT 1
            """,
            (int(user_id),),
        )
        row = cursor.fetchone() or {}
        return str(row.get("flag") or 0).strip() in ("1", "true", "True")
    except Exception:
        return False


def user_has_qc_permission(cursor, user_id) -> bool:
    return _permission_flag(cursor, user_id, "qc_permission")


def user_has_audit_permission(cursor, user_id) -> bool:
    return _permission_flag(cursor, user_id, "audit_permission")


def user_has_qc_overview_permission(cursor, user_id) -> bool:
    return _permission_flag(cursor, user_id, "qc_overview_permission")


def is_qa_role(role_name) -> bool:
    return (role_name or "").strip().lower() == "qa"


def is_qc_scope(payload) -> bool:
    return str((payload or {}).get("scope") or "").strip().lower() == "qc"


def is_org_wide_qc_scope(cursor, user_id, payload) -> bool:
    """Agent Files / QC screens send scope=qc. Permission holders see all agents/projects."""
    if not is_qc_scope(payload):
        return False
    return user_has_qc_permission(cursor, user_id)

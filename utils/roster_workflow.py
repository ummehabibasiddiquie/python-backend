# utils/roster_workflow.py
"""
Phase 2 roster approval workflow, change application, versioning, and production sync.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, time
from typing import Any

from utils.roster_helpers import (
    FULL_DAY_HOURS,
    HALF_DAY_HOURS,
    day_shift_times,
    get_eligible_employees,
    is_admin_or_super_admin,
    now_str,
    parse_date,
    parse_month_year,
    sync_to_user_monthly_tracker,
    write_audit_log,
)
from utils.json_utils import dumps_json_safe
from utils.roster_metrics import (
    build_month_snapshot,
    apply_active_leaves_to_days,
    iter_dates_inclusive,
    recalculate_metrics_from_days_and_leaves,
)


EDITABLE_STATUSES = frozenset({"Draft", "Approved"})
SUBMITTABLE_STATUSES = frozenset({"Draft", "Approved"})
LOCKABLE_STATUSES = frozenset({"Draft", "Approved"})


def cancel_pending_requests_for_roster(
    cursor,
    roster_month_id: int,
    performed_by: int,
    *,
    note: str = "Cancelled because roster was locked",
) -> int:
    now = now_str()
    cursor.execute(
        """
        SELECT request_id
        FROM roster_change_request
        WHERE roster_month_id=%s AND status='Pending' AND is_active=1
        """,
        (int(roster_month_id),),
    )
    rows = cursor.fetchall() or []
    for row in rows:
        cursor.execute(
            """
            UPDATE roster_change_request
            SET status='Cancelled due to Withdrawal',
                reviewer_comment=%s,
                reviewed_by=%s,
                reviewed_date=%s,
                batch_id=NULL
            WHERE request_id=%s
            """,
            (note, int(performed_by), now, int(row["request_id"])),
        )
    return len(rows)


def count_pending_change_requests_for_month(cursor, month_year: str) -> int:
    cursor.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM roster_change_request rcr
        JOIN roster_month rm ON rm.roster_month_id = rcr.roster_month_id
        WHERE rm.month_year=%s AND rm.is_active=1
          AND rcr.is_active=1 AND rcr.status='Pending'
        """,
        (str(month_year).strip(),),
    )
    row = cursor.fetchone() or {}
    return int(row.get("cnt") or 0)


def lock_roster_month_record(cursor, roster_month_id: int, locked_by: int) -> bool:
    """Lock one roster month unless already Locked or Pending Approval blocked separately."""
    now = now_str()
    cursor.execute(
        """
        UPDATE roster_month
        SET status='Locked', locked_by=%s, locked_date=%s, updated_date=%s
        WHERE roster_month_id=%s AND is_active=1 AND status != 'Locked'
        """,
        (int(locked_by), now, now, int(roster_month_id)),
    )
    return cursor.rowcount > 0


def unlock_roster_month_record(cursor, roster_month_id: int) -> bool:
    """Unlock back to Draft or Approved depending on approval history."""
    cursor.execute(
        """
        SELECT approved_by, last_approved_by
        FROM roster_month
        WHERE roster_month_id=%s AND is_active=1 AND status='Locked'
        """,
        (int(roster_month_id),),
    )
    row = cursor.fetchone()
    if not row:
        return False

    restore_status = (
        "Approved"
        if row.get("approved_by") or row.get("last_approved_by")
        else "Draft"
    )
    now = now_str()
    cursor.execute(
        """
        UPDATE roster_month
        SET status=%s, locked_by=NULL, locked_date=NULL, updated_date=%s
        WHERE roster_month_id=%s AND is_active=1 AND status='Locked'
        """,
        (restore_status, now, int(roster_month_id)),
    )
    return cursor.rowcount > 0


def can_create_change_requests(status: str) -> bool:
    return (status or "").strip() in EDITABLE_STATUSES


def is_month_locked(status: str) -> bool:
    return (status or "").strip().lower() == "locked"


def can_approve_reject(role_name: str) -> bool:
    return is_admin_or_super_admin(role_name)


def get_roster_month(cursor, roster_month_id: int, active_only: bool = True) -> dict | None:
    sql = """
        SELECT rm.*, u.user_name, LOWER(TRIM(r.role_name)) AS employee_role_name,
               locker.user_name AS locked_by_name
        FROM roster_month rm
        JOIN tfs_user u ON u.user_id = rm.user_id
        JOIN user_role r ON r.role_id = u.role_id
        LEFT JOIN tfs_user locker ON locker.user_id = rm.locked_by
        WHERE rm.roster_month_id=%s
    """
    params: list[Any] = [int(roster_month_id)]
    if active_only:
        sql += " AND rm.is_active=1"
    cursor.execute(sql, tuple(params))
    return cursor.fetchone()


def get_roster_days(cursor, roster_month_id: int, active_only: bool = True) -> list[dict]:
    sql = """
        SELECT *
        FROM roster_day
        WHERE roster_month_id=%s
    """
    params: list[Any] = [int(roster_month_id)]
    if active_only:
        sql += " AND is_active=1"
    sql += " ORDER BY roster_date ASC"
    cursor.execute(sql, tuple(params))
    return cursor.fetchall() or []


def get_roster_leaves(cursor, roster_month_id: int, active_only: bool = True) -> list[dict]:
    sql = """
        SELECT *
        FROM roster_leave
        WHERE roster_month_id=%s
    """
    params: list[Any] = [int(roster_month_id)]
    if active_only:
        sql += " AND is_active=1"
    sql += " ORDER BY start_date ASC"
    cursor.execute(sql, tuple(params))
    return cursor.fetchall() or []


def assert_manager_scope(cursor, logged_in_user_id: int, role_name: str, roster_month: dict) -> str | None:
    if is_admin_or_super_admin(role_name):
        return None
    year, month = parse_month_year(roster_month["month_year"])
    allowed = get_eligible_employees(
        cursor,
        logged_in_user_id,
        role_name,
        year,
        month,
        user_id=int(roster_month["user_id"]),
    )
    if not allowed:
        return "You do not have permission to manage this employee roster"
    return None


def create_change_request(
    cursor,
    *,
    roster_month_id: int,
    user_id: int,
    change_type: str,
    change_payload: dict,
    submitted_by: int,
    batch_id: str | None = None,
) -> int:
    now = now_str()
    cursor.execute(
        """
        INSERT INTO roster_change_request (
            roster_month_id, user_id, change_type, change_payload, batch_id,
            status, submitted_by, submitted_date, is_active
        ) VALUES (%s,%s,%s,%s,%s,'Pending',%s,%s,1)
        """,
        (
            int(roster_month_id),
            int(user_id),
            change_type,
            json.dumps(change_payload),
            batch_id,
            int(submitted_by),
            now,
        ),
    )
    request_id = cursor.lastrowid
    write_audit_log(
        cursor,
        roster_month_id=int(roster_month_id),
        user_id=int(user_id),
        action="CHANGE_REQUEST_CREATED",
        entity_type="roster_change_request",
        entity_id=int(request_id),
        old_value=None,
        new_value={"change_type": change_type, "change_payload": change_payload, "batch_id": batch_id},
        performed_by=int(submitted_by),
        approval_status="Pending",
    )
    return int(request_id)


def _leave_request_key(change_type: str, payload: dict) -> tuple:
    start = (payload.get("start_date") or "")[:10]
    end = (payload.get("end_date") or "")[:10]
    leave_type = (payload.get("leave_type") or "").strip().lower()
    if change_type == "LEAVE_UPDATE":
        return (change_type, start, end, leave_type, str(payload.get("leave_id") or ""))
    return (change_type, start, end, leave_type)


def find_matching_pending_leave_requests(
    cursor,
    *,
    roster_month_id: int,
    change_type: str,
    change_payload: dict,
) -> list[dict]:
    start = (change_payload.get("start_date") or "")[:10]
    end = (change_payload.get("end_date") or "")[:10]
    if not start or not end:
        return []

    if change_type == "LEAVE_UPDATE":
        leave_id = change_payload.get("leave_id")
        if not leave_id:
            return []
        cursor.execute(
            """
            SELECT request_id, batch_id, change_payload
            FROM roster_change_request
            WHERE roster_month_id=%s AND change_type='LEAVE_UPDATE'
              AND status='Pending' AND is_active=1
              AND JSON_UNQUOTE(JSON_EXTRACT(change_payload, '$.leave_id')) = %s
            ORDER BY request_id DESC
            """,
            (int(roster_month_id), str(leave_id)),
        )
        return cursor.fetchall() or []

    cursor.execute(
        """
        SELECT request_id, batch_id, change_payload
        FROM roster_change_request
        WHERE roster_month_id=%s AND change_type='LEAVE_ADD'
          AND status='Pending' AND is_active=1
          AND JSON_UNQUOTE(JSON_EXTRACT(change_payload, '$.start_date')) = %s
          AND JSON_UNQUOTE(JSON_EXTRACT(change_payload, '$.end_date')) = %s
        ORDER BY request_id DESC
        """,
        (int(roster_month_id), start, end),
    )
    return cursor.fetchall() or []


def create_or_update_leave_request(
    cursor,
    *,
    roster_month_id: int,
    user_id: int,
    change_type: str,
    change_payload: dict,
    submitted_by: int,
) -> tuple[int, bool]:
    """
    Upsert a pending leave change request.
    Returns (request_id, created_new).
    """
    matches = find_matching_pending_leave_requests(
        cursor,
        roster_month_id=roster_month_id,
        change_type=change_type,
        change_payload=change_payload,
    )

    if matches:
        keep_id = int(matches[0]["request_id"])
        now = now_str()
        cursor.execute(
            """
            UPDATE roster_change_request
            SET change_payload=%s, submitted_by=%s, submitted_date=%s
            WHERE request_id=%s
            """,
            (json.dumps(change_payload), int(submitted_by), now, keep_id),
        )
        for dup in matches[1:]:
            cursor.execute(
                """
                UPDATE roster_change_request
                SET status='Cancelled due to Withdrawal',
                    reviewer_comment='Duplicate leave request removed automatically',
                    reviewed_by=%s,
                    reviewed_date=%s
                WHERE request_id=%s
                """,
                (int(submitted_by), now, int(dup["request_id"])),
            )
        return keep_id, False

    return (
        create_change_request(
            cursor,
            roster_month_id=roster_month_id,
            user_id=user_id,
            change_type=change_type,
            change_payload=change_payload,
            submitted_by=submitted_by,
            batch_id=None,
        ),
        True,
    )


def dedupe_change_request_rows(rows: list[dict]) -> list[dict]:
    """Hide duplicate pending leave rows (same employee, dates, status, batch)."""
    seen: set[tuple] = set()
    deduped: list[dict] = []

    for row in sorted(rows, key=lambda r: int(r.get("request_id") or 0), reverse=True):
        change_type = row.get("change_type") or ""
        if change_type not in ("LEAVE_ADD", "LEAVE_UPDATE"):
            deduped.append(row)
            continue

        payload = row.get("change_payload") or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}

        key = (
            int(row.get("user_id") or 0),
            change_type,
            _leave_request_key(change_type, payload),
            row.get("status") or "",
            row.get("batch_id") or "",
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    deduped.sort(
        key=lambda r: (
            r.get("submitted_date") or "",
            int(r.get("request_id") or 0),
        ),
        reverse=True,
    )
    return deduped


def cancel_duplicate_pending_leave_requests(
    cursor,
    *,
    approved_request: dict,
    reviewed_by: int,
) -> int:
    """When one leave request is approved, cancel other pending duplicates."""
    change_type = approved_request.get("change_type")
    if change_type not in ("LEAVE_ADD", "LEAVE_UPDATE"):
        return 0

    payload = approved_request.get("change_payload") or {}
    if isinstance(payload, str):
        payload = json.loads(payload)

    start = (payload.get("start_date") or "")[:10]
    end = (payload.get("end_date") or "")[:10]
    if not start or not end:
        return 0

    now = now_str()
    keep_id = int(approved_request["request_id"])
    roster_month_id = int(approved_request["roster_month_id"])

    if change_type == "LEAVE_UPDATE":
        leave_id = payload.get("leave_id")
        cursor.execute(
            """
            UPDATE roster_change_request
            SET status='Cancelled due to Withdrawal',
                reviewer_comment='Duplicate leave update — auto-cancelled after approval',
                reviewed_by=%s, reviewed_date=%s
            WHERE roster_month_id=%s AND change_type='LEAVE_UPDATE'
              AND status='Pending' AND is_active=1 AND request_id != %s
              AND JSON_UNQUOTE(JSON_EXTRACT(change_payload, '$.leave_id')) = %s
            """,
            (reviewed_by, now, roster_month_id, keep_id, str(leave_id)),
        )
    else:
        cursor.execute(
            """
            UPDATE roster_change_request
            SET status='Cancelled due to Withdrawal',
                reviewer_comment='Duplicate leave request — auto-cancelled after approval',
                reviewed_by=%s, reviewed_date=%s
            WHERE roster_month_id=%s AND change_type='LEAVE_ADD'
              AND status='Pending' AND is_active=1 AND request_id != %s
              AND JSON_UNQUOTE(JSON_EXTRACT(change_payload, '$.start_date')) = %s
              AND JSON_UNQUOTE(JSON_EXTRACT(change_payload, '$.end_date')) = %s
            """,
            (reviewed_by, now, roster_month_id, keep_id, start, end),
        )

    return cursor.rowcount


def weekoff_swap_preview(cursor, roster_month_id: int, new_week_off_dates: list[str]) -> dict:
    days = get_roster_days(cursor, roster_month_id)
    if not days:
        return {"changes": [], "message": "No roster days found"}

    new_offs = {parse_date(d) for d in new_week_off_dates if parse_date(d)}
    changes = []

    for day in days:
        d = parse_date(day.get("roster_date"))
        if not d:
            continue
        currently_off = day.get("day_type") == "WeekOff"
        should_off = d in new_offs

        if currently_off == should_off:
            continue

        if should_off:
            new_type = "WeekOff"
        elif day.get("holiday_id"):
            new_type = "Holiday"
        else:
            new_type = "Working"

        changes.append(
            {
                "roster_date": d.isoformat(),
                "current_day_type": day.get("day_type"),
                "proposed_day_type": new_type,
            }
        )

    return {
        "roster_month_id": int(roster_month_id),
        "proposed_week_off_dates": sorted(d.isoformat() for d in new_offs),
        "changes": changes,
        "requires_confirmation": True,
    }


def _parse_time_value(value) -> time | None:
    if value is None or value == "":
        return None
    if isinstance(value, time):
        return value
    s = str(value).strip()
    if len(s) >= 5:
        parts = s.split(":")
        return time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
    return None


def apply_day_update(cursor, roster_month: dict, payload: dict) -> None:
    roster_month_id = int(roster_month["roster_month_id"])
    roster_date = parse_date(payload.get("roster_date"))
    if not roster_date:
        raise ValueError("roster_date is required")

    cursor.execute(
        """
        SELECT * FROM roster_day
        WHERE roster_month_id=%s AND roster_date=%s AND is_active=1
        """,
        (roster_month_id, roster_date.isoformat()),
    )
    day = cursor.fetchone()
    if not day:
        raise ValueError("Roster day not found")

    day_type = payload.get("day_type", day.get("day_type"))
    working_type = payload.get("working_type", day.get("working_type"))
    shift = payload.get("shift", day.get("shift", "DAY"))

    current_hours = float(day.get("working_hours") or FULL_DAY_HOURS)
    if working_type == "Half":
        if (day.get("working_type") or "Full") == "Full":
            full_ref = float(payload.get("working_hours") or current_hours)
            working_hours = round(full_ref / 2, 2)
        else:
            working_hours = float(payload.get("working_hours") or current_hours)
    elif working_type == "Full":
        if (day.get("working_type") or "Full") == "Half":
            working_hours = round(current_hours * 2, 2)
        else:
            working_hours = float(payload.get("working_hours") or current_hours)
    else:
        working_hours = float(payload.get("working_hours", current_hours))

    shift_start = _parse_time_value(payload.get("shift_start", day.get("shift_start")))
    shift_end = _parse_time_value(payload.get("shift_end", day.get("shift_end")))

    if day_type == "Working" and shift == "DAY" and not shift_start:
        shift_start, shift_end = day_shift_times(roster_month.get("employee_role_name", "agent"))

    now = now_str()
    cursor.execute(
        """
        UPDATE roster_day
        SET day_type=%s, shift=%s, shift_start=%s, shift_end=%s,
            working_type=%s, working_hours=%s, updated_date=%s
        WHERE roster_day_id=%s
        """,
        (
            day_type,
            shift,
            shift_start.strftime("%H:%M:%S") if shift_start else None,
            shift_end.strftime("%H:%M:%S") if shift_end else None,
            working_type,
            working_hours,
            now,
            int(day["roster_day_id"]),
        ),
    )


def apply_weekoff_swap(cursor, roster_month: dict, payload: dict) -> None:
    for change in payload.get("changes") or []:
        apply_day_update(
            cursor,
            roster_month,
            {
                "roster_date": change.get("roster_date"),
                "day_type": change.get("proposed_day_type"),
            },
        )


def apply_leave_add(cursor, roster_month: dict, payload: dict, created_by: int) -> int:
    roster_month_id = int(roster_month["roster_month_id"])
    now = now_str()
    cursor.execute(
        """
        INSERT INTO roster_leave (
            roster_month_id, leave_type, start_date, end_date, reason,
            is_rostered, affect_target, is_half_day, is_active,
            created_by, created_date, updated_date
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,1,%s,%s,%s)
        """,
        (
            roster_month_id,
            payload.get("leave_type", ""),
            payload.get("start_date"),
            payload.get("end_date"),
            payload.get("reason"),
            int(payload.get("is_rostered", 1)),
            int(payload.get("affect_target", 0)),
            int(payload.get("is_half_day", 0)),
            int(created_by),
            now,
            now,
        ),
    )
    leave_id = int(cursor.lastrowid)
    _apply_leave_to_days(cursor, roster_month_id, leave_id, payload)
    return leave_id


def apply_leave_update(cursor, roster_month: dict, payload: dict) -> None:
    leave_id = int(payload["leave_id"])
    roster_month_id = int(roster_month["roster_month_id"])
    now = now_str()

    cursor.execute(
        """
        UPDATE roster_leave
        SET leave_type=%s, start_date=%s, end_date=%s, reason=%s,
            is_rostered=%s, affect_target=%s, is_half_day=%s, updated_date=%s
        WHERE leave_id=%s AND roster_month_id=%s AND is_active=1
        """,
        (
            payload.get("leave_type", ""),
            payload.get("start_date"),
            payload.get("end_date"),
            payload.get("reason"),
            int(payload.get("is_rostered", 1)),
            int(payload.get("affect_target", 0)),
            int(payload.get("is_half_day", 0)),
            now,
            int(leave_id),
            roster_month_id,
        ),
    )
    _clear_leave_from_days(cursor, roster_month_id, leave_id)
    _apply_leave_to_days(cursor, roster_month_id, leave_id, payload)


def apply_leave_delete(cursor, roster_month: dict, payload: dict) -> None:
    leave_id = int(payload["leave_id"])
    roster_month_id = int(roster_month["roster_month_id"])
    now = now_str()
    cursor.execute(
        """
        UPDATE roster_leave SET is_active=0, updated_date=%s
        WHERE leave_id=%s AND roster_month_id=%s
        """,
        (now, leave_id, roster_month_id),
    )
    _clear_leave_from_days(cursor, roster_month_id, leave_id)


def _clear_leave_from_days(cursor, roster_month_id: int, leave_id: int) -> None:
    cursor.execute(
        """
        SELECT rd.roster_day_id, rd.roster_date, rd.holiday_id
        FROM roster_day rd
        WHERE rd.roster_month_id=%s AND rd.leave_id=%s AND rd.is_active=1
        """,
        (roster_month_id, int(leave_id)),
    )
    rows = cursor.fetchall() or []
    now = now_str()
    for row in rows:
        d = parse_date(row.get("roster_date"))
        if not d:
            continue
        if row.get("holiday_id"):
            new_type = "Holiday"
        elif d.weekday() >= 5:
            new_type = "WeekOff"
        else:
            new_type = "Working"
        cursor.execute(
            """
            UPDATE roster_day
            SET day_type=%s, leave_id=NULL, updated_date=%s
            WHERE roster_day_id=%s
            """,
            (new_type, now, int(row["roster_day_id"])),
        )


def _apply_leave_to_days(cursor, roster_month_id: int, leave_id: int, payload: dict) -> None:
    start = parse_date(payload.get("start_date"))
    end = parse_date(payload.get("end_date"))
    if not start or not end:
        raise ValueError("Invalid leave dates")

    now = now_str()
    for d in iter_dates_inclusive(start, end):
        date_str = d.isoformat()
        cursor.execute(
            """
            UPDATE roster_day
            SET day_type='Leave', leave_id=%s, updated_date=%s
            WHERE roster_month_id=%s
              AND DATE(roster_date)=DATE(%s)
              AND is_active=1
              AND day_type IN ('Working', 'Leave')
            """,
            (int(leave_id), now, int(roster_month_id), date_str),
        )


def apply_extra_hours_update(cursor, roster_month: dict, payload: dict) -> None:
    roster_month_id = int(roster_month["roster_month_id"])
    extra = float(payload.get("extra_assigned_hours", 0))
    cursor.execute(
        """
        UPDATE roster_month
        SET extra_assigned_hours=%s, updated_date=%s
        WHERE roster_month_id=%s
        """,
        (extra, now_str(), roster_month_id),
    )


def apply_change_request(cursor, roster_month: dict, request_row: dict, performed_by: int) -> None:
    change_type = request_row.get("change_type")
    payload = request_row.get("change_payload")
    if isinstance(payload, str):
        payload = json.loads(payload)

    if change_type == "DAY_UPDATE":
        apply_day_update(cursor, roster_month, payload)
    elif change_type == "WEEKOFF_SWAP":
        apply_weekoff_swap(cursor, roster_month, payload)
    elif change_type == "LEAVE_ADD":
        apply_leave_add(cursor, roster_month, payload, performed_by)
    elif change_type == "LEAVE_UPDATE":
        apply_leave_update(cursor, roster_month, payload)
    elif change_type == "LEAVE_DELETE":
        apply_leave_delete(cursor, roster_month, payload)
    elif change_type == "EXTRA_HOURS_UPDATE":
        apply_extra_hours_update(cursor, roster_month, payload)
    else:
        raise ValueError(f"Unsupported change_type: {change_type}")


def refresh_roster_month_metrics(cursor, roster_month_id: int) -> dict:
    leaves = get_roster_leaves(cursor, roster_month_id)
    for leave in leaves:
        if not int(leave.get("is_active", 1)):
            continue
        _apply_leave_to_days(
            cursor,
            int(roster_month_id),
            int(leave["leave_id"]),
            {
                "start_date": leave.get("start_date"),
                "end_date": leave.get("end_date"),
            },
        )
    days = get_roster_days(cursor, roster_month_id)
    days = apply_active_leaves_to_days(days, leaves)
    metrics = recalculate_metrics_from_days_and_leaves(days, leaves)
    cursor.execute(
        """
        UPDATE roster_month
        SET calendar_working_days=%s,
            target_working_days=%s,
            monthly_target_hours=%s,
            updated_date=%s
        WHERE roster_month_id=%s
        """,
        (
            metrics["calendar_working_days"],
            metrics["target_working_days"],
            metrics["monthly_target_hours"],
            now_str(),
            int(roster_month_id),
        ),
    )
    return metrics


def save_version_snapshot(
    cursor,
    roster_month: dict,
    days: list[dict],
    leaves: list[dict],
    approved_by: int,
    reviewer_comment: str,
) -> int:
    snapshot = build_month_snapshot(roster_month, days, leaves)
    now = now_str()
    cursor.execute(
        """
        INSERT INTO roster_version_snapshot (
            roster_month_id, roster_version, snapshot_json,
            approved_by, approved_date, reviewer_comment,
            production_synced_at, created_date
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            int(roster_month["roster_month_id"]),
            int(roster_month["roster_version"]),
            dumps_json_safe(snapshot),
            int(approved_by),
            now,
            reviewer_comment,
            roster_month.get("production_synced_at"),
            now,
        ),
    )
    return int(cursor.lastrowid)


def finalize_approved_cycle(
    cursor,
    roster_month_id: int,
    approved_by: int,
    cycle_reviewer_comment: str,
) -> dict:
    roster_month = get_roster_month(cursor, roster_month_id)
    if not roster_month:
        raise ValueError("Roster month not found")

    refresh_roster_month_metrics(cursor, roster_month_id)
    roster_month = get_roster_month(cursor, roster_month_id)

    new_version = int(roster_month.get("roster_version") or 1) + 1
    now = now_str()

    cursor.execute(
        """
        UPDATE roster_month
        SET roster_version=%s, status='Approved',
            last_approved_by=%s, last_approved_date=%s,
            updated_date=%s
        WHERE roster_month_id=%s
        """,
        (new_version, int(approved_by), now, now, int(roster_month_id)),
    )
    roster_month = get_roster_month(cursor, roster_month_id)
    days = get_roster_days(cursor, roster_month_id)
    leaves = get_roster_leaves(cursor, roster_month_id)

    sync_to_user_monthly_tracker(cursor, roster_month, cycle_reviewer_comment, approved_by)
    roster_month = get_roster_month(cursor, roster_month_id)

    version_id = save_version_snapshot(
        cursor, roster_month, days, leaves, approved_by, cycle_reviewer_comment
    )

    write_audit_log(
        cursor,
        roster_month_id=int(roster_month_id),
        user_id=int(roster_month["user_id"]),
        action="ROSTER_VERSION_APPROVED",
        entity_type="roster_version_snapshot",
        entity_id=version_id,
        old_value={"previous_version": new_version - 1},
        new_value={"roster_version": new_version},
        performed_by=int(approved_by),
        approval_status="Approved",
        notes=cycle_reviewer_comment,
    )

    return {
        "roster_month_id": int(roster_month_id),
        "roster_version": new_version,
        "version_id": version_id,
    }


def get_pending_requests_for_batch(cursor, batch_id: str) -> list[dict]:
    cursor.execute(
        """
        SELECT *
        FROM roster_change_request
        WHERE batch_id=%s AND is_active=1
        ORDER BY request_id ASC
        """,
        (batch_id,),
    )
    rows = cursor.fetchall() or []
    for row in rows:
        if isinstance(row.get("change_payload"), str):
            try:
                row["change_payload"] = json.loads(row["change_payload"])
            except Exception:
                pass
    return rows


def batch_processing_complete(cursor, batch_id: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM roster_change_request
        WHERE batch_id=%s AND is_active=1 AND status='Pending'
        """,
        (batch_id,),
    )
    row = cursor.fetchone() or {}
    return int(row.get("cnt") or 0) == 0


def count_batch_approved(cursor, batch_id: str) -> int:
    cursor.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM roster_change_request
        WHERE batch_id=%s AND is_active=1 AND status='Approved'
        """,
        (batch_id,),
    )
    return int((cursor.fetchone() or {}).get("cnt") or 0)


def new_batch_id() -> str:
    return str(uuid.uuid4())

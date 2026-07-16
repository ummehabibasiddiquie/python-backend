# utils/roster_helpers.py
"""
Shared business logic for the Roster Management module.
All rules are driven by approved business requirements — do not add assumptions here.
"""

from __future__ import annotations

import calendar
import json
from datetime import date, datetime, time, timedelta
from typing import Any

from utils.json_utils import dumps_json_safe

FULL_DAY_HOURS = 9.0
HALF_DAY_HOURS = 4.5


def daily_hours_for_tenure(user_tenure) -> float:
    """
    Full working-day hours for roster target math.
    tenure < 1  → 9 * tenure  (0.5 → 4.5, 0.75 → 6.75)
    tenure >= 1 → 9           (never more than 9, even if tenure > 1)
    Missing/invalid tenure → treat as 1 (full 9 hours).
    """
    try:
        tenure = float(user_tenure)
    except (TypeError, ValueError):
        tenure = 1.0
    if tenure < 0:
        tenure = 0.0
    if tenure > 1:
        tenure = 1.0
    return round(FULL_DAY_HOURS * tenure, 2)


def tenure_cap(user_tenure) -> float:
    """Cap tenure to [0, 1] for hour assignment."""
    try:
        tenure = float(user_tenure)
    except (TypeError, ValueError):
        tenure = 1.0
    if tenure < 0:
        return 0.0
    if tenure > 1:
        return 1.0
    return tenure


def implied_full_day_hours(working_type, working_hours) -> float:
    """Infer full-day hours from a roster_day working_type + working_hours."""
    try:
        wh = float(working_hours if working_hours is not None else FULL_DAY_HOURS)
    except (TypeError, ValueError):
        wh = FULL_DAY_HOURS
    wt = (working_type or "Full").strip()
    # Already stored as half (e.g. 4.5 / 3.375) → double to recover full
    if wt == "Half" and wh <= FULL_DAY_HOURS * 0.6:
        return round(wh * 2, 2)
    return round(wh, 2)


def half_day_hours_from_roster_day(working_type, working_hours) -> float:
    """
    Half of that day's full hours.
    Same number for both:
      - Working type Half
      - Half-day leave (employee still works the other half)
    """
    return round(implied_full_day_hours(working_type, working_hours) / 2, 2)


def assigned_hours_for_roster_day(
    user_tenure,
    *,
    day_type: str | None = None,
    working_type: str | None = None,
    has_roster_day: bool = False,
    is_half_leave: bool = False,
) -> float:
    """
    Morning cron / QC assign-hours rules (roster + tenure):
      Full Working + tenure >= 1 → 9
      Full Working + tenure < 1  → 9 * tenure
      Half Working / half-day leave + tenure >= 1 → 4.5
      Half Working / half-day leave + tenure < 1  → 4.5 * tenure
      Full Leave / WeekOff / Holiday → 0
      No roster day for date → full-day tenure hours (same as Full Working)
    """
    factor = tenure_cap(user_tenure)
    dt = (day_type or "").strip()
    wt = (working_type or "Full").strip()

    if has_roster_day and dt == "Leave":
        # Half-day leave: employee still works the other half
        if is_half_leave or wt == "Half":
            return round(HALF_DAY_HOURS * factor, 2)
        return 0.0

    if has_roster_day and dt and dt != "Working":
        return 0.0

    base = HALF_DAY_HOURS if wt == "Half" else FULL_DAY_HOURS
    return round(base * factor, 2)


AGENT_DAY_SHIFT_START = time(9, 0)
AGENT_DAY_SHIFT_END = time(18, 30)
QA_DAY_SHIFT_START = time(10, 0)
QA_DAY_SHIFT_END = time(19, 30)

MONTH_ABBR = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_date(value: str | date | None) -> date | None:
    if value is None:
        return None
    # datetime is a subclass of date — normalize to date first
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s:
        return None
    if len(s) >= 10:
        s = s[:10]
    return datetime.strptime(s, "%Y-%m-%d").date()


def month_year_label(year: int, month: int) -> str:
    return f"{MONTH_ABBR[month - 1]}{year}"


def parse_month_year(month_year: str) -> tuple[int, int]:
    s = (month_year or "").strip()
    if len(s) < 5:
        raise ValueError("Invalid month_year format. Expected e.g. MAR2026")
    abbr = s[:3].upper()
    year = int(s[3:])
    if abbr not in MONTH_ABBR:
        raise ValueError(f"Invalid month abbreviation: {abbr}")
    return year, MONTH_ABBR.index(abbr) + 1


def month_date_range(year: int, month: int) -> tuple[date, date]:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def next_calendar_month(ref: date | None = None) -> tuple[int, int]:
    ref = ref or date.today()
    if ref.month == 12:
        return ref.year + 1, 1
    return ref.year, ref.month + 1


def is_last_week_of_month(ref: date | None = None) -> bool:
    """Generate button is enabled only during the last week of the current month."""
    ref = ref or date.today()
    last_day = calendar.monthrange(ref.year, ref.month)[1]
    return ref.day >= (last_day - 6)


def roster_month_last_date(month_year: str) -> date:
    year, month = parse_month_year(month_year)
    _, last = month_date_range(year, month)
    return last


def can_lock_roster_month(month_year: str, ref: date | None = None) -> bool:
    """
    Roster lock is allowed on or after the last calendar day of the roster month.
    Example: JUL2026 can be locked from 31 Jul 2026 onward; JUN2026 can still be locked in July.
    """
    ref = ref or date.today()
    return ref >= roster_month_last_date(month_year)


def roster_lock_not_before_message(month_year: str) -> str:
    last = roster_month_last_date(month_year)
    return (
        f"Roster for {month_year} can only be locked on or after "
        f"{last.strftime('%d %b %Y')} (last day of that month)."
    )


def month_calendar_has_lock(cursor, month_year: str) -> dict | None:
    """Return lock info if any active roster in this month is Locked."""
    cursor.execute(
        """
        SELECT rm.locked_by, rm.locked_date, locker.user_name AS locked_by_name
        FROM roster_month rm
        LEFT JOIN tfs_user locker ON locker.user_id = rm.locked_by
        WHERE rm.month_year=%s AND rm.is_active=1 AND rm.status='Locked'
        ORDER BY rm.locked_date DESC
        LIMIT 1
        """,
        (str(month_year).strip(),),
    )
    return cursor.fetchone()


def month_calendar_lock_message(cursor, month_year: str) -> str:
    row = month_calendar_has_lock(cursor, month_year)
    if not row:
        return ""
    locker = (row.get("locked_by_name") or "").strip() or "Super Admin / Admin"
    return (
        f"The {month_year} calendar has been locked by {locker}. "
        "No roster changes can be made until it is unlocked."
    )


def get_role_context(cursor, user_id: int) -> dict:
    cursor.execute(
        """
        SELECT
            u.role_id AS user_role_id,
            LOWER(TRIM(r.role_name)) AS user_role_name
        FROM tfs_user u
        JOIN user_role r ON r.role_id = u.role_id
        WHERE u.user_id=%s AND u.is_active=1 AND u.is_delete=1
        """,
        (int(user_id),),
    )
    row = cursor.fetchone() or {}
    return {
        "user_role_id": row.get("user_role_id"),
        "user_role_name": (row.get("user_role_name") or "").strip().lower(),
    }


def is_super_admin(role_name: str) -> bool:
    return (role_name or "").strip().lower() == "super admin"


def is_admin_or_super_admin(role_name: str) -> bool:
    r = (role_name or "").strip().lower()
    return r in ("admin", "super admin")


def is_self_read_only_roster_role(role_name: str) -> bool:
    """Agent and QA may view only their own roster; no edits."""
    return (role_name or "").strip().lower() in ("agent", "qa")


def can_manage_roster_employees(role_name: str) -> bool:
    """Roles that can generate or manage rosters for employees in their scope."""
    return (role_name or "").strip().lower() in (
        "super admin",
        "admin",
        "project manager",
        "assistant manager",
    )


def can_modify_holiday_master(role_name: str) -> bool:
    return is_super_admin(role_name)


def require_logged_in_user(data: dict) -> tuple[int | None, dict | None]:
    """Shared helper for extracting logged_in_user_id from request data."""
    logged_in_user_id = data.get("logged_in_user_id")
    if not logged_in_user_id:
        return None, {"error": "logged_in_user_id is required", "status": 400}
    return int(logged_in_user_id), None


def get_roster_role_ids(cursor) -> dict[str, int | None]:
    cursor.execute(
        """
        SELECT role_id, LOWER(TRIM(role_name)) AS role_name
        FROM user_role
        WHERE LOWER(TRIM(role_name)) IN ('agent', 'qa')
        """
    )
    rows = cursor.fetchall() or []
    out = {"agent": None, "qa": None}
    for row in rows:
        name = (row.get("role_name") or "").strip().lower()
        if name in out:
            out[name] = int(row["role_id"])
    return out


def _employee_scope_sql(role_name: str, logged_in_user_id: int) -> tuple[str, list]:
    """
    Reuses the same assignment filter pattern as user_monthly_report/list_users.
    """
    role_name = (role_name or "").strip().lower()
    if role_name in ("admin", "super admin"):
        return "", []
    if role_name in ("agent", "qa"):
        return " AND u.user_id = %s", [int(logged_in_user_id)]

    mid = str(logged_in_user_id)
    return (
        """
        AND (
            JSON_CONTAINS(u.project_manager_id, %s)
            OR JSON_CONTAINS(u.asst_manager_id, %s)
            OR JSON_CONTAINS(u.qa_id, %s)
        )
        """,
        [mid, mid, mid],
    )


def get_eligible_employees(
    cursor,
    logged_in_user_id: int,
    role_name: str,
    roster_year: int,
    roster_month: int,
    user_id: int | None = None,
) -> list[dict]:
    """
    Active Agents and QA only.
    Excludes employees who left before the roster month.
    """
    role_ids = get_roster_role_ids(cursor)
    agent_role_id = role_ids.get("agent")
    qa_role_id = role_ids.get("qa")
    eligible_role_ids = [rid for rid in (agent_role_id, qa_role_id) if rid is not None]
    if not eligible_role_ids:
        return []

    month_start, _ = month_date_range(roster_year, roster_month)
    placeholders = ",".join(["%s"] * len(eligible_role_ids))

    scope_sql, scope_params = _employee_scope_sql(role_name, logged_in_user_id)

    team_sql = ""
    team_params: list[Any] = []
    if (role_name or "").strip().lower() == "assistant manager":
        cursor.execute(
            """
            SELECT team_id
            FROM tfs_user
            WHERE user_id=%s AND is_active=1 AND is_delete=1
            LIMIT 1
            """,
            (int(logged_in_user_id),),
        )
        am_row = cursor.fetchone() or {}
        am_team_id = am_row.get("team_id")
        if am_team_id:
            team_sql = " AND u.team_id = %s"
            team_params = [int(am_team_id)]
        else:
            return []

    query = f"""
        SELECT
            u.user_id,
            u.user_name,
            u.role_id,
            LOWER(TRIM(r.role_name)) AS role_name,
            u.joining_date,
            u.user_tenure,
            u.deactivated_at,
            u.is_active,
            u.team_id,
            t.team_name
        FROM tfs_user u
        JOIN user_role r ON r.role_id = u.role_id
        LEFT JOIN team t ON t.team_id = u.team_id
        WHERE u.is_delete = 1
          AND u.is_active = 1
          AND u.role_id IN ({placeholders})
          AND (u.deactivated_at IS NULL OR DATE(u.deactivated_at) >= %s)
          {scope_sql}
          {team_sql}
    """
    params: list[Any] = [*eligible_role_ids, month_start.isoformat()]
    params.extend(scope_params)
    params.extend(team_params)
    if user_id is not None:
        query += " AND u.user_id = %s"
        params.append(int(user_id))

    query += " ORDER BY u.user_name ASC"
    cursor.execute(query, tuple(params))
    return cursor.fetchall() or []


def employee_already_has_roster(cursor, user_id: int, month_year: str) -> bool:
    cursor.execute(
        """
        SELECT roster_month_id
        FROM roster_month
        WHERE user_id=%s AND month_year=%s AND is_active=1
        LIMIT 1
        """,
        (int(user_id), month_year),
    )
    return cursor.fetchone() is not None


def load_active_holidays(cursor, year: int) -> dict[date, dict]:
    cursor.execute(
        """
        SELECT holiday_id, holiday_date, holiday_name, calendar_year
        FROM org_holiday
        WHERE calendar_year=%s AND is_active=1
        """,
        (int(year),),
    )
    rows = cursor.fetchall() or []
    out: dict[date, dict] = {}
    for row in rows:
        d = parse_date(row.get("holiday_date"))
        if d:
            out[d] = row
    return out


def is_default_week_off(d: date) -> bool:
    return d.weekday() >= 5  # Saturday=5, Sunday=6


def count_weekdays_in_range(start: date, end: date) -> int:
    count = 0
    current = start
    while current <= end:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


def day_shift_times(role_name: str) -> tuple[time, time]:
    if (role_name or "").strip().lower() == "qa":
        return QA_DAY_SHIFT_START, QA_DAY_SHIFT_END
    return AGENT_DAY_SHIFT_START, AGENT_DAY_SHIFT_END


def working_hours_for_day(day: dict) -> float:
    """
    Canonical hours for a roster day — used by all business calculations.
    Uses stored working_hours from roster_day (sourced from user_monthly_tracker at generation).
    Half days always resolve to half of that day's full hours (handles stale Full+9h rows).
    """
    if day.get("day_type") != "Working":
        return 0.0
    working_type = (day.get("working_type") or "Full").strip()
    stored = day.get("working_hours")
    if working_type == "Half":
        return half_day_hours_from_roster_day(working_type, stored)
    if working_type == "Full":
        return implied_full_day_hours(working_type, stored)
    return float(stored or FULL_DAY_HOURS)


def derive_daily_full_hours_from_tracker(monthly_target, working_days) -> float:
    """Per-day full hours from user_monthly_tracker (monthly_target / working_days)."""
    try:
        mt = float(monthly_target or 0)
        wd = float(working_days or 0)
        if mt > 0 and wd > 0:
            return round(mt / wd, 2)
    except (TypeError, ValueError):
        pass
    return FULL_DAY_HOURS


def load_user_monthly_tracker_baseline(
    cursor, user_id: int, month_year: str
) -> dict[str, float]:
    """
    Load AM-entered monthly target from user_monthly_tracker.
    daily_full_hours = monthly_target / working_days for roster day defaults and target math.
    extra_assigned_hours is monthly (not per day).
    """
    cursor.execute(
        """
        SELECT monthly_target, working_days, extra_assigned_hours
        FROM user_monthly_tracker
        WHERE user_id=%s AND month_year=%s AND is_active=1
        LIMIT 1
        """,
        (int(user_id), month_year),
    )
    row = cursor.fetchone()
    if not row:
        return {
            "daily_full_hours": FULL_DAY_HOURS,
            "extra_assigned_hours": 0.0,
            "from_tracker": False,
        }
    daily = derive_daily_full_hours_from_tracker(
        row.get("monthly_target"), row.get("working_days")
    )
    return {
        "daily_full_hours": daily,
        "extra_assigned_hours": float(row.get("extra_assigned_hours") or 0),
        "monthly_target": float(row.get("monthly_target") or 0),
        "working_days": float(row.get("working_days") or 0),
        "from_tracker": True,
    }


def sync_tracker_extra_hours_to_roster(
    cursor,
    user_id: int,
    month_year: str,
    extra_assigned_hours: float | None = None,
) -> int:
    """
    Push extra_assigned_hours from user_monthly_tracker to the active roster_month row.
    Called when extra hours are edited on User Monthly Report.
    """
    if extra_assigned_hours is None:
        tracker = load_user_monthly_tracker_baseline(cursor, int(user_id), month_year)
        extra_assigned_hours = float(tracker.get("extra_assigned_hours") or 0)

    cursor.execute(
        """
        SELECT status
        FROM roster_month
        WHERE user_id=%s AND month_year=%s AND is_active=1
        LIMIT 1
        """,
        (int(user_id), str(month_year).strip()),
    )
    row = cursor.fetchone()
    if row and (row.get("status") or "").strip() == "Locked":
        return 0

    cursor.execute(
        """
        UPDATE roster_month
        SET extra_assigned_hours=%s, updated_date=%s
        WHERE user_id=%s AND month_year=%s AND is_active=1 AND status != 'Locked'
        """,
        (float(extra_assigned_hours), now_str(), int(user_id), str(month_year).strip()),
    )
    return int(cursor.rowcount or 0)


def is_calendar_working_day(day: dict) -> bool:
    """Business rule: only day_type=Working counts as a scheduled working day."""
    return day.get("day_type") == "Working"


def is_holiday_on_scheduled_week_off(day: dict) -> bool:
    """Derived from stored fields only — not from display_labels."""
    return day.get("day_type") == "WeekOff" and bool(day.get("holiday_id"))


def build_default_day(
    d: date,
    employee_role_name: str,
    holidays: dict[date, dict],
    scheduled_week_off: bool | None = None,
    daily_full_hours: float | None = None,
) -> dict:
    """
    Week off takes precedence for working-day / target counting.
    When an org holiday falls on a scheduled week off:
      - day_type remains WeekOff (no extra target reduction)
      - holiday_id is stored so the calendar can show both Week Off and Holiday
    """
    on_week_off = is_default_week_off(d) if scheduled_week_off is None else scheduled_week_off
    holiday = holidays.get(d)
    full_hrs = float(daily_full_hours if daily_full_hours is not None else FULL_DAY_HOURS)

    if on_week_off:
        return {
            "roster_date": d,
            "day_type": "WeekOff",
            "shift": "DAY",
            "shift_start": None,
            "shift_end": None,
            "working_type": "Full",
            "working_hours": full_hrs,
            "holiday_id": holiday.get("holiday_id") if holiday else None,
            "holiday_name": holiday.get("holiday_name") if holiday else None,
            "leave_id": None,
        }

    if holiday:
        return {
            "roster_date": d,
            "day_type": "Holiday",
            "shift": "DAY",
            "shift_start": None,
            "shift_end": None,
            "working_type": "Full",
            "working_hours": full_hrs,
            "holiday_id": holiday.get("holiday_id"),
            "holiday_name": holiday.get("holiday_name"),
            "leave_id": None,
        }

    shift_start, shift_end = day_shift_times(employee_role_name)
    return {
        "roster_date": d,
        "day_type": "Working",
        "shift": "DAY",
        "shift_start": shift_start,
        "shift_end": shift_end,
        "working_type": "Full",
        "working_hours": full_hrs,
        "holiday_id": None,
        "holiday_name": None,
        "leave_id": None,
    }


def compute_roster_metrics(days: list[dict]) -> dict:
    """
    Business metrics derived from day_type, working_type, and working_hours.
    Never uses display_labels or other UI-only response fields.
    """
    calendar_working_days = 0.0
    monthly_target_hours = 0.0

    for day in days:
        if is_calendar_working_day(day):
            hours = working_hours_for_day(day)
            working_type = (day.get("working_type") or "Full").strip()
            calendar_working_days += 0.5 if working_type == "Half" else 1.0
            monthly_target_hours += hours

    return {
        "calendar_working_days": calendar_working_days,
        "target_working_days": calendar_working_days,
        "monthly_target_hours": monthly_target_hours,
    }


def resolve_roster_period(
    employee: dict,
    month_start: date,
    month_end: date,
) -> tuple[date | None, date | None, str | None]:
    """
    Prorate from joining_date. Dates before joining are excluded entirely.
    Returns (start, end, skip_reason).
    """
    joining_date = parse_date(employee.get("joining_date"))
    if not joining_date:
        return None, None, "joining_date is not set"

    if joining_date > month_end:
        return None, None, "employee joining date is after the roster month"

    deactivated_at = employee.get("deactivated_at")
    if deactivated_at:
        deact_date = parse_date(deactivated_at)
        if deact_date and deact_date < month_start:
            return None, None, "employee left before the roster month"

    roster_start = max(month_start, joining_date)
    roster_end = month_end
    return roster_start, roster_end, None


def generate_roster_days_for_employee(
    employee: dict,
    roster_start: date,
    roster_end: date,
    holidays: dict[date, dict],
    daily_full_hours: float | None = None,
) -> list[dict]:
    role_name = (employee.get("role_name") or "").strip().lower()
    days: list[dict] = []
    current = roster_start
    while current <= roster_end:
        days.append(
            build_default_day(current, role_name, holidays, daily_full_hours=daily_full_hours)
        )
        current += timedelta(days=1)
    return days


def write_audit_log(
    cursor,
    *,
    roster_month_id: int | None,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None,
    old_value: Any,
    new_value: Any,
    performed_by: int,
    approval_status: str | None = None,
    notes: str | None = None,
) -> None:
    cursor.execute(
        """
        INSERT INTO roster_audit_log (
            roster_month_id, user_id, action, entity_type, entity_id,
            old_value, new_value, performed_by, performed_date,
            approval_status, notes
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            roster_month_id,
            user_id,
            action,
            entity_type,
            entity_id,
            dumps_json_safe(old_value) if old_value is not None else None,
            dumps_json_safe(new_value) if new_value is not None else None,
            int(performed_by),
            now_str(),
            approval_status,
            notes,
        ),
    )


def deactivate_roster_month(cursor, roster_month_id: int) -> None:
    """
    Soft-deactivate a roster month and all related child records.
    Does not hard-delete anything; audit history is preserved.
    """
    now = now_str()
    rid = int(roster_month_id)

    cursor.execute(
        """
        UPDATE roster_month
        SET is_active=0, updated_date=%s
        WHERE roster_month_id=%s
        """,
        (now, rid),
    )
    cursor.execute(
        """
        UPDATE roster_day
        SET is_active=0, updated_date=%s
        WHERE roster_month_id=%s AND is_active=1
        """,
        (now, rid),
    )
    cursor.execute(
        """
        UPDATE roster_leave
        SET is_active=0, updated_date=%s
        WHERE roster_month_id=%s AND is_active=1
        """,
        (now, rid),
    )


def deactivate_active_rosters_for_month(cursor, month_year: str) -> list[int]:
    """Bulk soft-deactivate every active roster for a month. Returns deactivated ids."""
    cursor.execute(
        """
        SELECT roster_month_id
        FROM roster_month
        WHERE month_year=%s AND is_active=1
        """,
        (str(month_year).strip(),),
    )
    ids = [int(r["roster_month_id"]) for r in (cursor.fetchall() or [])]
    if not ids:
        return []

    now = now_str()
    placeholders = ",".join(["%s"] * len(ids))
    cursor.execute(
        f"""
        UPDATE roster_month
        SET is_active=0, updated_date=%s
        WHERE roster_month_id IN ({placeholders})
        """,
        tuple([now, *ids]),
    )
    cursor.execute(
        f"""
        UPDATE roster_day
        SET is_active=0, updated_date=%s
        WHERE roster_month_id IN ({placeholders}) AND is_active=1
        """,
        tuple([now, *ids]),
    )
    cursor.execute(
        f"""
        UPDATE roster_leave
        SET is_active=0, updated_date=%s
        WHERE roster_month_id IN ({placeholders}) AND is_active=1
        """,
        tuple([now, *ids]),
    )
    return ids


def cancel_pending_requests_for_month(cursor, month_year: str, performed_by: int) -> int:
    """Legacy: cancel Pending only. Prefer clear_change_requests_for_month on reset."""
    now = now_str()
    cursor.execute(
        """
        UPDATE roster_change_request rcr
        JOIN roster_month rm ON rm.roster_month_id = rcr.roster_month_id
        SET rcr.status='Cancelled due to Regeneration',
            rcr.reviewed_by=%s,
            rcr.reviewed_date=%s
        WHERE rm.month_year=%s
          AND rcr.status='Pending'
          AND rcr.is_active=1
        """,
        (int(performed_by), now, str(month_year).strip()),
    )
    return int(cursor.rowcount or 0)


def clear_change_requests_for_month(
    cursor,
    month_year: str,
    performed_by: int,
    *,
    user_id: int | None = None,
) -> int:
    """
    Soft-deactivate ALL change requests for a month (Pending / Approved / Rejected / etc.)
    so Approval Queue and My Submissions no longer show them.
    Optional user_id limits clear to one employee (single reset).
    """
    now = now_str()
    sql = """
        UPDATE roster_change_request rcr
        JOIN roster_month rm ON rm.roster_month_id = rcr.roster_month_id
        SET rcr.is_active=0,
            rcr.status=CASE
                WHEN rcr.status='Pending' THEN 'Cancelled due to Regeneration'
                ELSE rcr.status
            END,
            rcr.reviewed_by=COALESCE(rcr.reviewed_by, %s),
            rcr.reviewed_date=COALESCE(rcr.reviewed_date, %s)
        WHERE rm.month_year=%s
          AND rcr.is_active=1
    """
    params: list = [int(performed_by), now, str(month_year).strip()]
    if user_id is not None:
        sql += " AND rm.user_id=%s"
        params.append(int(user_id))
    cursor.execute(sql, tuple(params))
    return int(cursor.rowcount or 0)


def deactivate_active_rosters_for_employee(
    cursor, user_id: int, month_year: str
) -> list[int]:
    """Soft-deactivate active roster(s) for one employee in a month."""
    cursor.execute(
        """
        SELECT roster_month_id
        FROM roster_month
        WHERE user_id=%s AND month_year=%s AND is_active=1
        """,
        (int(user_id), str(month_year).strip()),
    )
    ids = [int(r["roster_month_id"]) for r in (cursor.fetchall() or [])]
    for rid in ids:
        deactivate_roster_month(cursor, rid)
    return ids


def load_tracker_baselines_map(
    cursor, user_ids: list[int], month_year: str
) -> dict[int, dict]:
    """Batch-load UMT baselines for many users (1 query)."""
    if not user_ids:
        return {}
    placeholders = ",".join(["%s"] * len(user_ids))
    cursor.execute(
        f"""
        SELECT user_id, monthly_target, working_days, extra_assigned_hours
        FROM user_monthly_tracker
        WHERE month_year=%s AND is_active=1 AND user_id IN ({placeholders})
        """,
        tuple([str(month_year).strip(), *[int(u) for u in user_ids]]),
    )
    out: dict[int, dict] = {}
    for row in cursor.fetchall() or []:
        uid = int(row["user_id"])
        daily = derive_daily_full_hours_from_tracker(
            row.get("monthly_target"), row.get("working_days")
        )
        out[uid] = {
            "daily_full_hours": daily,
            "extra_assigned_hours": float(row.get("extra_assigned_hours") or 0),
            "monthly_target": float(row.get("monthly_target") or 0),
            "working_days": float(row.get("working_days") or 0),
            "from_tracker": True,
        }
    return out


def insert_roster_for_employee(
    cursor,
    employee: dict,
    month_year: str,
    month_start: date,
    month_end: date,
    holidays: dict[date, dict],
    created_by: int,
    *,
    tracker_baseline: dict | None = None,
    write_audit: bool = True,
) -> dict:
    roster_start, roster_end, skip_reason = resolve_roster_period(employee, month_start, month_end)
    if skip_reason:
        return {"user_id": employee["user_id"], "status": "skipped", "reason": skip_reason}

    tracker = (
        tracker_baseline
        if tracker_baseline is not None
        else load_user_monthly_tracker_baseline(cursor, int(employee["user_id"]), month_year)
    )
    # Target hours: 1 working day = 9 * min(tenure, 1)
    daily_full_hours = daily_hours_for_tenure(employee.get("user_tenure"))
    extra_assigned = tracker["extra_assigned_hours"]

    days = generate_roster_days_for_employee(
        employee, roster_start, roster_end, holidays, daily_full_hours=daily_full_hours
    )
    metrics = compute_roster_metrics(days)
    baseline_target_days = count_weekdays_in_range(roster_start, roster_end)
    now = now_str()

    cursor.execute(
        """
        INSERT INTO roster_month (
            user_id, month_year, status,
            roster_start_date, roster_end_date,
            baseline_target_days, calendar_working_days,
            target_working_days, monthly_target_hours,
            extra_assigned_hours, is_active,
            created_by, created_date, updated_date
        ) VALUES (%s,%s,'Draft',%s,%s,%s,%s,%s,%s,%s,1,%s,%s,%s)
        """,
        (
            int(employee["user_id"]),
            month_year,
            roster_start.isoformat(),
            roster_end.isoformat(),
            baseline_target_days,
            metrics["calendar_working_days"],
            metrics["target_working_days"],
            metrics["monthly_target_hours"],
            extra_assigned,
            int(created_by),
            now,
            now,
        ),
    )
    roster_month_id = cursor.lastrowid

    day_rows = []
    for day in days:
        day_rows.append(
            (
                roster_month_id,
                day["roster_date"].isoformat(),
                day["day_type"],
                day["shift"],
                day["shift_start"].strftime("%H:%M:%S") if day["shift_start"] else None,
                day["shift_end"].strftime("%H:%M:%S") if day["shift_end"] else None,
                day["working_type"],
                day["working_hours"],
                day.get("holiday_id"),
                day.get("leave_id"),
                now,
                now,
            )
        )
    if day_rows:
        cursor.executemany(
            """
            INSERT INTO roster_day (
                roster_month_id, roster_date, day_type, shift,
                shift_start, shift_end, working_type, working_hours,
                holiday_id, leave_id, is_active, created_date, updated_date
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,%s,%s)
            """,
            day_rows,
        )

    if write_audit:
        write_audit_log(
            cursor,
            roster_month_id=roster_month_id,
            user_id=int(employee["user_id"]),
            action="ROSTER_GENERATED",
            entity_type="roster_month",
            entity_id=roster_month_id,
            old_value=None,
            new_value={
                "month_year": month_year,
                "roster_start_date": roster_start.isoformat(),
                "roster_end_date": roster_end.isoformat(),
                "baseline_target_days": baseline_target_days,
                **metrics,
            },
            performed_by=created_by,
            notes="Default roster generated",
        )

    # Push target hours + working days into user_monthly_tracker on generate/reset
    sync_to_user_monthly_tracker(
        cursor,
        {
            "roster_month_id": roster_month_id,
            "user_id": int(employee["user_id"]),
            "month_year": month_year,
            "monthly_target_hours": metrics["monthly_target_hours"],
            "target_working_days": metrics["target_working_days"],
            "extra_assigned_hours": extra_assigned,
        },
        "Synced from roster generate/reset",
        created_by,
        approval_status=None,
        action="ROSTER_GENERATED_SYNCED_TO_UMT",
    )

    return {
        "user_id": employee["user_id"],
        "user_name": employee.get("user_name"),
        "status": "created",
        "roster_month_id": roster_month_id,
        "roster_start_date": roster_start.isoformat(),
        "roster_end_date": roster_end.isoformat(),
        **metrics,
    }

def sync_to_user_monthly_tracker(
    cursor,
    roster_month: dict,
    reviewer_comment: str,
    performed_by: int,
    *,
    approval_status: str | None = "Approved",
    action: str = "ROSTER_SYNCED_TO_PRODUCTION",
) -> dict:
    """
    Upsert user_monthly_tracker from roster metrics.
    Used on generate/reset and again when a change cycle is approved.
    Rejected changes never call this (calendar + UMT stay as last approved/generated).
    """
    user_id = int(roster_month["user_id"])
    month_year = roster_month["month_year"]
    monthly_target = str(roster_month["monthly_target_hours"])
    working_days = str(roster_month["target_working_days"])
    extra = float(roster_month.get("extra_assigned_hours") or 0)
    now = now_str()

    cursor.execute(
        """
        SELECT user_monthly_tracker_id, monthly_target, working_days, extra_assigned_hours
        FROM user_monthly_tracker
        WHERE user_id=%s AND month_year=%s AND is_active=1
        LIMIT 1
        """,
        (user_id, month_year),
    )
    existing = cursor.fetchone()
    old_value = dict(existing) if existing else None

    if existing:
        cursor.execute(
            """
            UPDATE user_monthly_tracker
            SET monthly_target=%s, working_days=%s, extra_assigned_hours=%s
            WHERE user_monthly_tracker_id=%s
            """,
            (monthly_target, working_days, extra, int(existing["user_monthly_tracker_id"])),
        )
        tracker_id = int(existing["user_monthly_tracker_id"])
    else:
        cursor.execute(
            """
            INSERT INTO user_monthly_tracker (
                user_id, month_year, monthly_target, extra_assigned_hours,
                working_days, is_active, created_date
            ) VALUES (%s,%s,%s,%s,%s,1,%s)
            """,
            (user_id, month_year, monthly_target, extra, working_days, now),
        )
        tracker_id = int(cursor.lastrowid)

    roster_month_id = roster_month.get("roster_month_id")
    if roster_month_id:
        cursor.execute(
            """
            UPDATE roster_month
            SET production_synced_at=%s, updated_date=%s
            WHERE roster_month_id=%s
            """,
            (now, now, int(roster_month_id)),
        )

    new_value = {
        "user_monthly_tracker_id": tracker_id,
        "monthly_target": monthly_target,
        "working_days": working_days,
        "extra_assigned_hours": extra,
    }
    if roster_month_id:
        write_audit_log(
            cursor,
            roster_month_id=int(roster_month_id),
            user_id=user_id,
            action=action,
            entity_type="user_monthly_tracker",
            entity_id=tracker_id,
            old_value=old_value,
            new_value=new_value,
            performed_by=int(performed_by),
            approval_status=approval_status,
            notes=reviewer_comment,
        )
    return new_value


def enrich_roster_day_for_response(day: dict, holiday_lookup: dict[int, dict] | None = None) -> dict:
    """
    Attach UI-only display fields for calendar rendering.
    Business logic must use day_type, holiday_id, working_type, working_hours — never display_labels.
    """
    enriched = dict(day)
    if enriched.get("roster_date") and not isinstance(enriched["roster_date"], str):
        enriched["roster_date"] = enriched["roster_date"].isoformat()

    for tkey in ("shift_start", "shift_end"):
        if enriched.get(tkey) is not None:
            enriched[tkey] = str(enriched[tkey])

    holiday_id = enriched.get("holiday_id")
    holiday_name = enriched.get("holiday_name")
    if holiday_id and not holiday_name and holiday_lookup:
        holiday_name = (holiday_lookup.get(int(holiday_id)) or {}).get("holiday_name")
    if holiday_name:
        enriched["holiday_name"] = holiday_name

    # UI-only flags — not used by compute_roster_metrics or other business logic
    is_holiday_on_week_off = is_holiday_on_scheduled_week_off(enriched)
    enriched["is_holiday_on_week_off"] = is_holiday_on_week_off

    labels = []
    if enriched.get("day_type") == "WeekOff":
        labels.append("WeekOff")
    elif enriched.get("day_type") == "Holiday":
        labels.append("Holiday")
    elif enriched.get("day_type") == "Working":
        labels.append("Working")
    elif enriched.get("day_type") == "Leave":
        labels.append("Leave")

    if is_holiday_on_week_off:
        labels.append("Holiday")

    enriched["display_labels"] = labels
    return enriched

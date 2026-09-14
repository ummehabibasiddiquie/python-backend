"""
Deactivated user visibility and write rules.

Convention:
  - is_active = 0 + deactivated_at set = left the org
  - DATE(deactivated_at) = last day their data stays visible and they may still work
  - From the next calendar day: no login, no tracker add/edit for that user
"""

from __future__ import annotations

from datetime import date, datetime

from utils.roster_helpers import parse_date
from utils.time_ist import now_ist


def leave_date(value) -> date | None:
    """Parse deactivated_at (or date-like) to a calendar leave date."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return parse_date(str(value)[:10])


def today_ist() -> date:
    return now_ist().date()


def can_user_login(is_active, deactivated_at, today: date | None = None) -> bool:
    """
    Active users always can.
    Deactivated users can log in only through DATE(deactivated_at) inclusive.
    """
    try:
        active = int(is_active or 0) == 1
    except (TypeError, ValueError):
        active = False
    if active:
        return True
    left = leave_date(deactivated_at)
    if not left:
        return False
    return left >= (today or today_ist())


def can_user_write_tracker(is_active, deactivated_at, work_date=None, today: date | None = None) -> bool:
    """
    Tracker add/edit allowed if active, or if deactivated but work/today
    is still on or before the leave date.
    """
    try:
        active = int(is_active or 0) == 1
    except (TypeError, ValueError):
        active = False
    if active:
        return True
    left = leave_date(deactivated_at)
    if not left:
        return False
    ref = leave_date(work_date) or (today or today_ist())
    return ref <= left


def sql_visible_user_clause(
    alias: str = "u",
    *,
    period_start_param: bool = True,
) -> str:
    """
    SQL fragment: active users OR leavers whose leave date is on/after period start.
    Expects one %s bind for period_start (DATE) when period_start_param is True.
    Use for report/history filters tied to a selected month or date range.
    """
    a = alias
    if period_start_param:
        return f"""(
            {a}.is_active = 1
            OR (
                {a}.is_active = 0
                AND {a}.deactivated_at IS NOT NULL
                AND DATE({a}.deactivated_at) >= %s
            )
        )"""
    return f"""(
        {a}.is_active = 1
        OR (
            {a}.is_active = 0
            AND {a}.deactivated_at IS NOT NULL
            AND DATE({a}.deactivated_at) >= CURDATE()
        )
    )"""


def sql_listing_leaver_clause(alias: str = "u", months: int = 3) -> str:
    """
    Agent-list pages (monthly tracker, agent files, tracker report):
    active users OR deactivated within the last `months` months.
    No bind params — uses CURDATE().
    """
    a = alias
    m = max(1, int(months))
    return f"""(
        {a}.is_active = 1
        OR (
            {a}.is_active = 0
            AND {a}.deactivated_at IS NOT NULL
            AND {a}.deactivated_at >= DATE_SUB(CURDATE(), INTERVAL {m} MONTH)
        )
    )"""


def resolve_dropdown_period_start(data: dict | None) -> date:
    """
    Period start for agent dropdown visibility.
    Prefers date_from / start_date / month_year, else current month start.
    """
    data = data or {}
    for key in ("date_from", "start_date", "from_date"):
        d = leave_date(data.get(key))
        if d:
            return d
    month_year = str(data.get("month_year") or "").strip()
    if month_year:
        # YYYY-MM or SEP2026
        if len(month_year) >= 7 and month_year[4] == "-":
            d = leave_date(f"{month_year[:7]}-01")
            if d:
                return d
        raw = month_year.upper().replace(" ", "")
        months = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
        if len(raw) >= 7 and raw[:3] in months:
            try:
                m = months.index(raw[:3]) + 1
                y = int(raw[3:7])
                return date(y, m, 1)
            except (ValueError, IndexError):
                pass
    today = today_ist()
    return date(today.year, today.month, 1)


def fetch_user_status(cursor, user_id: int) -> dict | None:
    cursor.execute(
        """
        SELECT user_id, is_active, is_delete, deactivated_at, user_name
        FROM tfs_user
        WHERE user_id=%s
        """,
        (int(user_id),),
    )
    return cursor.fetchone()

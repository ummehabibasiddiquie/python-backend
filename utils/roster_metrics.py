# utils/roster_metrics.py
"""
Roster metrics recalculation — business logic only.
Uses day_type, working_type, working_hours, holiday_id, leave records.
Never uses display_labels or other UI-only fields.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from utils.roster_helpers import (
    FULL_DAY_HOURS,
    HALF_DAY_HOURS,
    is_calendar_working_day,
    parse_date,
    working_hours_for_day,
)


def iter_dates_inclusive(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def leave_hours_credit(is_half_day: bool, full_day_hours: float = FULL_DAY_HOURS) -> float:
    if is_half_day:
        return round(full_day_hours / 2, 2)
    return full_day_hours


def infer_full_day_hours_from_days(days: list[dict]) -> float:
    """Derive per-day full hours from roster working days (set from user_monthly_tracker)."""
    for day in days:
        if day.get("day_type") == "Working" and (day.get("working_type") or "Full") == "Full":
            return float(day.get("working_hours") or FULL_DAY_HOURS)
    for day in days:
        if day.get("day_type") == "Working" and (day.get("working_type") or "") == "Half":
            return float(day.get("working_hours") or HALF_DAY_HOURS) * 2
    return FULL_DAY_HOURS


def leave_day_credit(is_half_day: bool) -> float:
    return 0.5 if is_half_day else 1.0


def apply_active_leaves_to_days(days: list[dict], leaves: list[dict] | None) -> list[dict]:
    """Merge approved leave records onto working days for metrics and calendar display."""
    if not leaves:
        return [dict(d) for d in days]

    indexed: dict[date, dict] = {}
    for day in days:
        d = parse_date(day.get("roster_date"))
        if d is not None:
            indexed[d] = dict(day)

    for leave in leaves:
        if not int(leave.get("is_active", 1)):
            continue
        start = parse_date(leave.get("start_date"))
        end = parse_date(leave.get("end_date"))
        if not start or not end:
            continue
        leave_id = leave.get("leave_id")
        for d in iter_dates_inclusive(start, end):
            row = indexed.get(d)
            if row and row.get("day_type") == "Working":
                row["day_type"] = "Leave"
                row["leave_id"] = leave_id

    if not indexed:
        return [dict(d) for d in days]
    return [indexed[d] for d in sorted(indexed.keys())]


def recalculate_metrics_from_days_and_leaves(
    days: list[dict],
    leaves: list[dict] | None = None,
) -> dict[str, float]:
    """
    Compute calendar_working_days, target_working_days, monthly_target_hours.

  Leave rules (approved):
    - Leave dates are reflected on days as day_type=Leave (not Working).
    - calendar_working_days counts only Working days.
    - Leaves with affect_target=No add credit back to target metrics only.
    - Leaves with affect_target=Yes are already excluded via day_type=Leave.
    - Night shift does not affect target hours (only working_type drives hours).
    """
    leaves = leaves or []
    full_day_hours = infer_full_day_hours_from_days(days)

    calendar_working_days = 0.0
    base_target_hours = 0.0

    for day in days:
        if is_calendar_working_day(day):
            calendar_working_days += 1.0
            base_target_hours += working_hours_for_day(day)

    target_hour_credit = 0.0
    target_day_credit = 0.0

    for leave in leaves:
        if not int(leave.get("is_active", 1)):
            continue
        if int(leave.get("affect_target", 0)):
            continue

        start = parse_date(leave.get("start_date"))
        end = parse_date(leave.get("end_date"))
        if not start or not end:
            continue

        is_half = bool(int(leave.get("is_half_day", 0)))
        hrs = leave_hours_credit(is_half, full_day_hours)
        day_equiv = leave_day_credit(is_half)

        for d in iter_dates_inclusive(start, end):
            matching = [x for x in days if parse_date(x.get("roster_date")) == d]
            if matching and matching[0].get("day_type") == "Leave":
                target_hour_credit += hrs
                target_day_credit += day_equiv

    monthly_target_hours = base_target_hours + target_hour_credit
    target_working_days = calendar_working_days + target_day_credit

    return {
        "calendar_working_days": calendar_working_days,
        "target_working_days": target_working_days,
        "monthly_target_hours": monthly_target_hours,
    }


def serialize_day_row(row: dict) -> dict:
    """Normalize DB row for metrics / snapshots."""
    out = dict(row)
    rd = out.get("roster_date")
    if rd and not isinstance(rd, str):
        out["roster_date"] = rd.isoformat()
    for key in ("shift_start", "shift_end"):
        if out.get(key) is not None:
            out[key] = str(out[key])
    for key, val in list(out.items()):
        if isinstance(val, Decimal):
            out[key] = float(val)
    return out


def serialize_leave_row(row: dict) -> dict:
    """Normalize leave row for JSON snapshots."""
    out = dict(row)
    for key in ("start_date", "end_date", "created_date", "updated_date"):
        val = out.get(key)
        if val is not None and not isinstance(val, str):
            out[key] = val.isoformat() if hasattr(val, "isoformat") else str(val)
    for key, val in list(out.items()):
        if isinstance(val, Decimal):
            out[key] = float(val)
    return out


def build_month_snapshot(
    roster_month: dict,
    days: list[dict],
    leaves: list[dict],
) -> dict[str, Any]:
    return {
        "roster_month_id": roster_month.get("roster_month_id"),
        "user_id": roster_month.get("user_id"),
        "month_year": roster_month.get("month_year"),
        "roster_version": roster_month.get("roster_version"),
        "status": roster_month.get("status"),
        "roster_start_date": str(roster_month.get("roster_start_date")),
        "roster_end_date": str(roster_month.get("roster_end_date")),
        "baseline_target_days": float(roster_month.get("baseline_target_days") or 0),
        "calendar_working_days": float(roster_month.get("calendar_working_days") or 0),
        "target_working_days": float(roster_month.get("target_working_days") or 0),
        "monthly_target_hours": float(roster_month.get("monthly_target_hours") or 0),
        "extra_assigned_hours": float(roster_month.get("extra_assigned_hours") or 0),
        "days": [serialize_day_row(d) for d in days],
        "leaves": [serialize_leave_row(l) for l in leaves],
    }

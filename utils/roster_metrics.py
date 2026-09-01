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
    implied_full_day_hours,
    is_calendar_working_day,
    parse_date,
    half_day_hours_from_roster_day,
    working_hours_for_day,
    apply_universal_working_days_cap,
    count_universal_working_days_from_days,
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
            return implied_full_day_hours(day.get("working_type"), day.get("working_hours"))
    for day in days:
        if day.get("day_type") == "Working" and (day.get("working_type") or "") == "Half":
            return implied_full_day_hours(day.get("working_type"), day.get("working_hours"))
    return FULL_DAY_HOURS


def leave_day_credit(is_half_day: bool) -> float:
    return 0.5 if is_half_day else 1.0


def _index_leaves_by_date(leaves: list[dict] | None) -> dict[date, dict]:
    by_date: dict[date, dict] = {}
    for leave in leaves or []:
        if not int(leave.get("is_active", 1)):
            continue
        start = parse_date(leave.get("start_date"))
        end = parse_date(leave.get("end_date"))
        if not start or not end:
            continue
        for d in iter_dates_inclusive(start, end):
            by_date[d] = leave
    return by_date


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
        is_half = bool(int(leave.get("is_half_day", 0)))
        affect_target = bool(int(leave.get("affect_target", 0)))
        for d in iter_dates_inclusive(start, end):
            row = indexed.get(d)
            if row and row.get("day_type") in ("Working", "Leave"):
                row["day_type"] = "Leave"
                row["leave_id"] = leave_id
                row["leave_is_half_day"] = is_half
                row["leave_affect_target"] = affect_target
                row["leave_type"] = leave.get("leave_type") or row.get("leave_type")
                if is_half:
                    orig_wt = row.get("working_type") or "Full"
                    wh = row.get("working_hours")
                    row["working_type"] = "Half"
                    row["working_hours"] = half_day_hours_from_roster_day(orig_wt, wh)
                    row["is_half_day"] = True
                    # Display as half working + leave type (same feel as Half Working day)
                    row["display_as_half_working"] = True

    if not indexed:
        return [dict(d) for d in days]
    return [indexed[d] for d in sorted(indexed.keys())]


def _is_universal_working_date(d: date | None, day: dict | None) -> bool:
    """Mon–Fri that is not an org holiday. Week-off swaps do not change this."""
    if d is None or d.weekday() >= 5:
        return False
    if not day:
        return True
    if (day.get("day_type") or "").strip() == "Holiday":
        return False
    return True


def recalculate_metrics_from_days_and_leaves(
    days: list[dict],
    leaves: list[dict] | None = None,
) -> dict[str, float]:
    """
    Calendar working days follow the weekly grid (week-offs, extra working days).

    Monthly target starts at universal Mon–Fri minus holidays, then:
    - extra week-offs do NOT reduce target (agents settle offs across later weeks)
    - extra weekend working days do NOT raise target (ceiling)
    - leave with affect_target=Yes reduces target (full −1, half −0.5)
    - leave with affect_target=No does not reduce target
    - Working-type Half on a universal day reduces target by 0.5
    """
    leaves = leaves or []
    full_day_hours = infer_full_day_hours_from_days(days)
    leave_by_date = _index_leaves_by_date(leaves)

    calendar_working_days = 0.0

    for day in days:
        d = parse_date(day.get("roster_date"))
        leave = leave_by_date.get(d) if d else None
        is_half_leave = bool(leave and int(leave.get("is_half_day", 0)))

        if is_calendar_working_day(day):
            working_type = (day.get("working_type") or "Full").strip()
            if working_type == "Half":
                calendar_working_days += 0.5
            else:
                calendar_working_days += 1.0
        elif day.get("day_type") == "Leave" and is_half_leave:
            calendar_working_days += 0.5

    universal = count_universal_working_days_from_days(days)
    penalty_days = 0.0
    penalty_hours = 0.0

    for day in days:
        d = parse_date(day.get("roster_date"))
        if not _is_universal_working_date(d, day):
            continue
        leave = leave_by_date.get(d) if d else None
        day_type = (day.get("day_type") or "").strip()
        working_type = (day.get("working_type") or "Full").strip()

        if leave and int(leave.get("is_active", 1)) and int(leave.get("affect_target", 0)):
            if day_type == "Leave":
                is_half = bool(int(leave.get("is_half_day", 0)))
                penalty_days += leave_day_credit(is_half)
                penalty_hours += leave_hours_credit(is_half, full_day_hours)
            continue

        if day_type == "Working" and working_type == "Half":
            penalty_days += 0.5
            penalty_hours += round(full_day_hours / 2, 2)

    if universal > 0:
        target_working_days = round(max(0.0, float(universal) - penalty_days), 2)
        monthly_target_hours = round(
            max(0.0, float(universal) * full_day_hours - penalty_hours), 2
        )
    else:
        target_working_days = calendar_working_days
        monthly_target_hours = round(calendar_working_days * full_day_hours, 2)

    metrics = {
        "calendar_working_days": calendar_working_days,
        "target_working_days": target_working_days,
        "monthly_target_hours": monthly_target_hours,
    }
    return apply_universal_working_days_cap(
        metrics,
        days,
        universal_days=universal if universal > 0 else None,
        daily_full_hours=full_day_hours,
    )


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

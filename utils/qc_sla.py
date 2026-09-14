"""
QC SLA: deadline = submission + 24 working hours.
Working-hour clock pauses on Saturday, Sunday, and org_holiday dates.

Files submitted before QC_FORM_SLA_EFFECTIVE_FROM used the old temp_qc
full-day average score flow (no per-file QC form) and are excluded from
urgent / late-file SLA.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Iterable

from utils.roster_helpers import load_active_holidays, parse_date
from utils.time_ist import IST, now_ist

QC_SLA_WORKING_HOURS = 24.0
# Per-file QC form + 24h urgent SLA apply from this month onward.
# Earlier months used temp_qc daily average scores only.
QC_FORM_SLA_EFFECTIVE_FROM = date(2026, 9, 1)
QC_FORM_SLA_EFFECTIVE_FROM_SQL = QC_FORM_SLA_EFFECTIVE_FROM.isoformat()


def submission_date(value) -> date | None:
    dt = parse_dt(value)
    if dt:
        return ensure_aware(dt).date()
    return parse_date(str(value or "")[:10])


def sla_applies_to_submission(submitted_at) -> bool:
    """True when this file is in the QC-form era (not old temp_qc-only months)."""
    d = submission_date(submitted_at)
    if not d:
        return False
    return d >= QC_FORM_SLA_EFFECTIVE_FROM


def holiday_date_set(cursor, start: date | None, end: date | None) -> set[date]:
    """Load org holiday dates covering [start, end] (inclusive), with year buffer."""
    if not start and not end:
        today = now_ist().date()
        start = end = today
    if not start:
        start = end
    if not end:
        end = start
    if end < start:
        start, end = end, start
    out: set[date] = set()
    for year in range(start.year, end.year + 1):
        out.update(load_active_holidays(cursor, year).keys())
    return out


def is_working_day(d: date, holidays: Iterable[date] | None = None) -> bool:
    holiday_set = set(holidays or [])
    return d.weekday() < 5 and d not in holiday_set


def parse_dt(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text or text.lower() in ("none", "null", "nat") or text.startswith("0000-00-00"):
            return None
        text = text.replace("T", " ")[:19]
        try:
            dt = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                dt = datetime.strptime(text[:10], "%Y-%m-%d")
            except ValueError:
                return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=IST)
    return dt.astimezone(IST)


def _next_working_day_start(from_date: date, holidays: set[date]) -> datetime:
    d = from_date
    for _ in range(400):
        if is_working_day(d, holidays):
            return datetime.combine(d, time(0, 0, 0), tzinfo=IST)
        d += timedelta(days=1)
    return datetime.combine(from_date, time(0, 0, 0), tzinfo=IST)


def add_working_hours(
    start_dt: datetime | None,
    hours: float = QC_SLA_WORKING_HOURS,
    holidays: Iterable[date] | None = None,
) -> datetime | None:
    """Advance start_dt by `hours` of working time (weekends/holidays paused)."""
    if start_dt is None:
        return None
    try:
        hours_f = float(hours)
    except (TypeError, ValueError):
        hours_f = QC_SLA_WORKING_HOURS
    if hours_f <= 0:
        return ensure_aware(start_dt)

    holiday_set = set(holidays or [])
    current = ensure_aware(start_dt)
    remaining = timedelta(hours=hours_f)

    if not is_working_day(current.date(), holiday_set):
        current = _next_working_day_start(current.date() + timedelta(days=1), holiday_set)

    for _ in range(10000):
        if remaining <= timedelta(0):
            return current
        if not is_working_day(current.date(), holiday_set):
            current = _next_working_day_start(current.date() + timedelta(days=1), holiday_set)
            continue
        next_midnight = datetime.combine(
            current.date() + timedelta(days=1), time(0, 0, 0), tzinfo=IST
        )
        available = next_midnight - current
        if remaining <= available:
            return current + remaining
        remaining -= available
        current = _next_working_day_start(current.date() + timedelta(days=1), holiday_set)
    return current


def working_hours_between(
    start_dt: datetime | None,
    end_dt: datetime | None,
    holidays: Iterable[date] | None = None,
) -> float | None:
    """
    Signed working hours from start → end (weekends/holidays paused).
    Positive = end is after start in working time; negative = end is before start.
    """
    if start_dt is None or end_dt is None:
        return None
    start = ensure_aware(start_dt)
    end = ensure_aware(end_dt)
    if end == start:
        return 0.0
    sign = 1.0
    if end < start:
        start, end = end, start
        sign = -1.0

    holiday_set = set(holidays or [])
    current = start
    total = timedelta(0)

    if not is_working_day(current.date(), holiday_set):
        current = _next_working_day_start(current.date() + timedelta(days=1), holiday_set)
        if current >= end:
            return 0.0 * sign

    for _ in range(10000):
        if current >= end:
            break
        if not is_working_day(current.date(), holiday_set):
            current = _next_working_day_start(current.date() + timedelta(days=1), holiday_set)
            continue
        next_midnight = datetime.combine(
            current.date() + timedelta(days=1), time(0, 0, 0), tzinfo=IST
        )
        slice_end = end if end < next_midnight else next_midnight
        if slice_end > current:
            total += slice_end - current
        current = slice_end if slice_end < next_midnight else _next_working_day_start(
            current.date() + timedelta(days=1), holiday_set
        )
    return sign * round(total.total_seconds() / 3600.0, 2)


def ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=IST)
    return dt.astimezone(IST)


def qc_deadline(
    submitted_at,
    holidays: Iterable[date] | None = None,
    hours: float = QC_SLA_WORKING_HOURS,
) -> datetime | None:
    return add_working_hours(parse_dt(submitted_at), hours, holidays)


def is_qc_late(
    submitted_at,
    qc_done_at,
    holidays: Iterable[date] | None = None,
    hours: float = QC_SLA_WORKING_HOURS,
) -> bool:
    if not sla_applies_to_submission(submitted_at):
        return False
    submitted = parse_dt(submitted_at)
    done = parse_dt(qc_done_at)
    if not submitted or not done:
        return False
    deadline = add_working_hours(submitted, hours, holidays)
    if not deadline:
        return False
    return ensure_aware(done) > deadline


def sla_fields(
    submitted_at,
    holidays: Iterable[date] | None = None,
    now: datetime | None = None,
    hours: float = QC_SLA_WORKING_HOURS,
) -> dict:
    """Fields for pending-file urgency UI."""
    if not sla_applies_to_submission(submitted_at):
        submitted = parse_dt(submitted_at)
        return {
            "file_submitted_at": submitted.strftime("%Y-%m-%d %H:%M:%S") if submitted else "",
            "qc_deadline": "",
            "is_overdue": False,
            "hours_remaining": None,
            "sla_applies": False,
        }
    submitted = parse_dt(submitted_at)
    deadline = add_working_hours(submitted, hours, holidays) if submitted else None
    current = ensure_aware(now or now_ist())
    if not deadline:
        return {
            "file_submitted_at": submitted.strftime("%Y-%m-%d %H:%M:%S") if submitted else "",
            "qc_deadline": "",
            "is_overdue": False,
            "hours_remaining": None,
            "sla_applies": True,
        }
    remaining = working_hours_between(current, deadline, holidays)
    return {
        "file_submitted_at": submitted.strftime("%Y-%m-%d %H:%M:%S") if submitted else "",
        "qc_deadline": deadline.strftime("%Y-%m-%d %H:%M:%S"),
        "is_overdue": bool(remaining is not None and remaining < 0),
        "hours_remaining": remaining,
        "sla_applies": True,
    }


def load_holidays_around(cursor, *datetimes_or_dates) -> set[date]:
    """Load holidays spanning all provided datetimes/dates plus a forward buffer."""
    dates: list[date] = []
    for value in datetimes_or_dates:
        if value is None:
            continue
        if isinstance(value, datetime):
            dates.append(ensure_aware(value).date())
        elif isinstance(value, date):
            dates.append(value)
        else:
            dt = parse_dt(value)
            if dt:
                dates.append(dt.date())
            else:
                d = parse_date(str(value)[:10])
                if d:
                    dates.append(d)
    today = now_ist().date()
    if not dates:
        dates = [today]
    start = min(dates) - timedelta(days=7)
    end = max(max(dates), today) + timedelta(days=60)
    return holiday_date_set(cursor, start, end)

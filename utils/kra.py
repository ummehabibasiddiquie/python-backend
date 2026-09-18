"""
Monthly agent KRA.

The sheet is calculated from billable hours, QC scores, roster, and tracker counts.
Daily notes can be added when needed. Everything else is read-only.
Active from SEP2026. For the current month, days are shown only through today (IST).
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal

from utils.qc_auto_score import AUTO_QC_DAYS_SQL
from utils.roster_helpers import parse_month_year, roster_day_status_label
from utils.time_ist import now_ist, now_str

# KRA starts from this calendar month (MonYYYY). Earlier months are not available.
KRA_GO_LIVE_MONTH = "SEP2026"

PRODUCTIVITY_HOURS = 9
QUALITY_MIN = 98
TRACKER_MIN = 7

WEIGHT_PRODUCTIVITY = 33
WEIGHT_QUALITY = 33
WEIGHT_SCHEDULE = 10
WEIGHT_REPORTING = 14
WEIGHT_TIMELINESS = 10

# Up to 3 non-compliance days keeps the full 14%.
# The workbook says "3 to 6"; 3 is already covered by "up to 3", so the next band starts at 4.
REPORTING_FULL_MAX = 3
REPORTING_PARTIAL_MAX = 6
REPORTING_FULL_SCORE = 14
REPORTING_PARTIAL_SCORE = 7

WORKING_ATTENDANCE = ("PRESENT", "HALF DAY", "ABSENT", "WFH", "UNROSTERED")
PRESENT_ATTENDANCE = ("PRESENT", "HALF DAY", "WFH")
TRACKER_ATTENDANCE = ("PRESENT", "HALF DAY", "WFH", "UNROSTERED")
BLANK_ATTENDANCE = ("", "—", "WEEK OFF", "HOLIDAY", "LEAVE")

ROSTER_TO_KRA = {
    "Week Off": "WEEK OFF",
    "Holiday": "HOLIDAY",
    "Leave": "LEAVE",
    "Half Day Leave": "LEAVE",
    "Half Day": "HALF DAY",
    "Working": "PRESENT",
}

FORMULAS = {
    "productivity_day": 'YES if billable hours are 9 or more, otherwise NO. Blank on Week Off, Holiday, and Leave when there are no hours.',
    "quality_day": "YES if the day's QC score is 98 or above. NO if a score exists and is below 98. Blank when there is no score.",
    "productivity_score": "(No. of YES days / Total working days) × 33",
    "quality_score": "(No. of days with QC score ≥ 98 / Total working days) × 33",
    "schedule_score": "(Present + Half Day + WFH / Total working days) × 10",
    "working_days": "Days marked Present, Half Day, Absent, WFH, or Unrostered. Leave, Week Off, and Holiday are not working days.",
    "present_days": "Present, Half Day, and WFH. This is rostered attendance.",
    "reporting": "Count Present, Half Day, WFH, and Unrostered days with fewer than 7 trackers. Add warning instances (verbal = 1, email = 2, letter = 3). 0–3 instances = 14%, 4–6 = 7%, more than 6 = 0%.",
    "timeliness": "Left blank. This point is not stored in HRMS.",
}


def ensure_kra_note_table(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS kra_day_note (
            kra_day_note_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            work_date DATE NOT NULL,
            note VARCHAR(500) NULL,
            updated_by INT NULL,
            updated_date DATETIME NULL,
            UNIQUE KEY uq_kra_day_note (user_id, work_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )


def _num(value) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _date_key(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def roster_attendance(day_type, working_type, is_half_day) -> str:
    label = roster_day_status_label(day_type, working_type, is_half_day)
    return ROSTER_TO_KRA.get(label, "")


def productivity_flag(attendance: str, billable_hours) -> str | None:
    hours = _num(billable_hours)
    has_hours = hours is not None and hours > 0
    if attendance not in WORKING_ATTENDANCE and not has_hours:
        return None
    compare = hours if hours is not None else 0
    return "YES" if compare >= PRODUCTIVITY_HOURS else "NO"


def quality_flag(qc_score) -> str | None:
    score = _num(qc_score)
    if score is None:
        return None
    return "YES" if score >= QUALITY_MIN else "NO"


def is_working_day(attendance: str) -> bool:
    return attendance in WORKING_ATTENDANCE


def is_present_day(attendance: str) -> bool:
    return attendance in PRESENT_ATTENDANCE


def is_low_tracker_day(attendance: str, tracker_count) -> bool:
    if attendance not in TRACKER_ATTENDANCE:
        return False
    count = int(_num(tracker_count) or 0)
    return count < TRACKER_MIN


def reporting_score(low_tracker_days: int, verbal: int = 0, email: int = 0, letter: int = 0) -> dict:
    extra = int(verbal or 0) + int(email or 0) * 2 + int(letter or 0) * 3
    instances = int(low_tracker_days or 0) + extra
    if instances <= REPORTING_FULL_MAX:
        earned = REPORTING_FULL_SCORE
        band = f"0–{REPORTING_FULL_MAX} instances = {REPORTING_FULL_SCORE}%"
    elif instances <= REPORTING_PARTIAL_MAX:
        earned = REPORTING_PARTIAL_SCORE
        band = f"4–{REPORTING_PARTIAL_MAX} instances = {REPORTING_PARTIAL_SCORE}%"
    else:
        earned = 0
        band = f"more than {REPORTING_PARTIAL_MAX} instances = 0%"
    return {
        "low_tracker_days": int(low_tracker_days or 0),
        "warning_instances": extra,
        "instances": instances,
        "earned": earned,
        "band": band,
    }


def _ratio_score(numerator: int, denominator: int, weight: float) -> float | None:
    if not denominator:
        return None
    return round((numerator / denominator) * weight, 2)


def _index_by_date(rows, date_field: str) -> dict[date, dict]:
    out = {}
    for row in rows or []:
        key = _date_key(row.get(date_field))
        if key:
            out[key] = row
    return out


def kra_period_end(year: int, month: int, today: date | None = None) -> date:
    """Last day included in the KRA sheet for that month (today for the current month)."""
    month_end = date(year, month, calendar.monthrange(year, month)[1])
    today = today or now_ist().date()
    if (year, month) == (today.year, today.month):
        return min(month_end, today)
    return month_end


def is_kra_month_allowed(month_year: str) -> bool:
    try:
        year, month = parse_month_year(month_year)
        go_year, go_month = parse_month_year(KRA_GO_LIVE_MONTH)
    except ValueError:
        return False
    return (year, month) >= (go_year, go_month)


def build_kra_report(cursor, user_id: int, year: int, month: int, month_year: str) -> dict:
    ensure_kra_note_table(cursor)
    start = date(year, month, 1)
    today = now_ist().date()
    end = kra_period_end(year, month, today)

    cursor.execute(
        """
        SELECT u.user_id, u.user_name, t.team_name
        FROM tfs_user u
        LEFT JOIN team t ON t.team_id = u.team_id
        WHERE u.user_id = %s
        LIMIT 1
        """,
        (int(user_id),),
    )
    user = cursor.fetchone() or {}

    cursor.execute(
        """
        SELECT
            DATE(CAST(twt.date_time AS DATETIME)) AS work_date,
            ROUND(SUM(COALESCE(twt.production, 0) / NULLIF(twt.tenure_target, 0)), 2) AS billable_hours,
            COUNT(*) AS tracker_count
        FROM task_work_tracker twt
        WHERE twt.user_id = %s
          AND twt.is_active != 0
          AND DATE(CAST(twt.date_time AS DATETIME)) BETWEEN %s AND %s
        GROUP BY DATE(CAST(twt.date_time AS DATETIME))
        """,
        (int(user_id), start, end),
    )
    billable = _index_by_date(cursor.fetchall(), "work_date")

    cursor.execute(
        """
        SELECT
            DATE(rd.roster_date) AS work_date,
            rd.day_type,
            rd.working_type,
            COALESCE(rl.is_half_day, 0) AS is_half_day
        FROM roster_month rm
        JOIN roster_day rd
          ON rd.roster_month_id = rm.roster_month_id
         AND rd.is_active = 1
        LEFT JOIN roster_leave rl
          ON rl.leave_id = rd.leave_id
         AND rl.is_active = 1
        WHERE rm.user_id = %s
          AND rm.is_active = 1
          AND UPPER(rm.month_year) = UPPER(%s)
        """,
        (int(user_id), month_year),
    )
    roster = _index_by_date(cursor.fetchall(), "work_date")

    cursor.execute(
        """
        SELECT
            DATE(date_of_file_submission) AS work_date,
            ROUND(AVG(qc_score), 2) AS qc_score
        FROM qc_records
        WHERE agent_id = %s
          AND qc_score IS NOT NULL
          AND DATE(date_of_file_submission) BETWEEN %s AND %s
        GROUP BY DATE(date_of_file_submission)
        """,
        (int(user_id), start, end),
    )
    qc_records = _index_by_date(cursor.fetchall(), "work_date")

    cursor.execute(
        """
        SELECT `date` AS work_date, qc_score
        FROM temp_qc
        WHERE user_id = %s
          AND `date` BETWEEN %s AND %s
        """,
        (int(user_id), start.isoformat(), end.isoformat()),
    )
    temp_qc = _index_by_date(cursor.fetchall(), "work_date")

    cursor.execute(
        f"""
        SELECT work_date, auto_qc_score
        FROM ({AUTO_QC_DAYS_SQL}) auto_qc
        WHERE auto_qc.user_id = %s
          AND auto_qc.work_date BETWEEN %s AND %s
        """,
        (int(user_id), start, end),
    )
    auto_qc = _index_by_date(cursor.fetchall(), "work_date")

    cursor.execute(
        """
        SELECT work_date, note
        FROM kra_day_note
        WHERE user_id = %s AND work_date BETWEEN %s AND %s
        """,
        (int(user_id), start, end),
    )
    notes = _index_by_date(cursor.fetchall(), "work_date")

    cursor.execute(
        """
        SELECT working_days
        FROM user_monthly_tracker
        WHERE user_id = %s
          AND is_active = 1
          AND UPPER(month_year) = UPPER(%s)
        LIMIT 1
        """,
        (int(user_id), month_year),
    )
    goal_row = cursor.fetchone() or {}

    days = []
    current = start
    while current <= end:
        bill = billable.get(current) or {}
        rost = roster.get(current) or {}
        roster_status = ""
        if rost:
            roster_status = roster_attendance(
                rost.get("day_type"),
                rost.get("working_type"),
                rost.get("is_half_day"),
            )
        attendance = roster_status
        hours = _num(bill.get("billable_hours"))
        if hours is not None:
            hours = round(hours, 2)
        tracker_count = int(bill.get("tracker_count") or 0) if bill else 0
        qc = _num((temp_qc.get(current) or {}).get("qc_score"))
        if qc is None:
            qc = _num((qc_records.get(current) or {}).get("qc_score"))
        if qc is None:
            qc = _num((auto_qc.get(current) or {}).get("auto_qc_score"))
        if qc is not None:
            qc = round(qc, 2)
        note = ((notes.get(current) or {}).get("note") or "").strip()
        days.append(
            {
                "work_date": current.isoformat(),
                "day": current.strftime("%A"),
                "roster_status": roster_status,
                "attendance": attendance,
                "billable_hours": hours if bill else None,
                "productivity": productivity_flag(attendance, hours if bill else None),
                "qc_score": qc,
                "quality": quality_flag(qc),
                "tracker_count": tracker_count if bill or attendance in TRACKER_ATTENDANCE else None,
                "note": note,
                "low_tracker": is_low_tracker_day(
                    attendance,
                    tracker_count if bill or attendance in TRACKER_ATTENDANCE else 0,
                ),
            }
        )
        current += timedelta(days=1)

    # Working days with no tracker rows still count as 0 trackers.
    for row in days:
        if row["attendance"] in TRACKER_ATTENDANCE and row["tracker_count"] is None:
            row["tracker_count"] = 0
            row["low_tracker"] = True

    status_counts = {key: 0 for key in (
        "PRESENT", "HALF DAY", "ABSENT", "LEAVE", "WEEK OFF", "WFH", "UNROSTERED", "HOLIDAY"
    )}
    productivity_yes = 0
    productivity_no = 0
    quality_yes = 0
    quality_no = 0
    working_days = 0
    present_days = 0
    low_tracker_days = 0
    billable_total = 0.0
    quality_scores = []

    for row in days:
        status = row["attendance"]
        if status in status_counts:
            status_counts[status] += 1
        if row["productivity"] == "YES":
            productivity_yes += 1
        elif row["productivity"] == "NO":
            productivity_no += 1
        if row["quality"] == "YES":
            quality_yes += 1
        elif row["quality"] == "NO":
            quality_no += 1
        if is_working_day(status):
            working_days += 1
        if is_present_day(status):
            present_days += 1
        if row["low_tracker"]:
            low_tracker_days += 1
        if row["billable_hours"] is not None:
            billable_total += row["billable_hours"]
        if row["qc_score"] is not None:
            quality_scores.append(row["qc_score"])

    verbal = 0
    email = 0
    letter = 0
    timeliness = None
    reporting = reporting_score(low_tracker_days, verbal, email, letter)

    productivity_earned = _ratio_score(productivity_yes, working_days, WEIGHT_PRODUCTIVITY)
    quality_earned = _ratio_score(quality_yes, working_days, WEIGHT_QUALITY)
    schedule_earned = _ratio_score(present_days, working_days, WEIGHT_SCHEDULE)
    reporting_earned = float(reporting["earned"])
    timeliness_earned = None if timeliness is None else round(float(timeliness), 2)

    earned_parts = [
        productivity_earned or 0,
        quality_earned or 0,
        schedule_earned or 0,
        reporting_earned,
    ]
    applicable_weight = WEIGHT_PRODUCTIVITY + WEIGHT_QUALITY + WEIGHT_SCHEDULE + WEIGHT_REPORTING
    if timeliness_earned is not None:
        earned_parts.append(timeliness_earned)
        applicable_weight += WEIGHT_TIMELINESS
    earned_total = round(sum(earned_parts), 2)
    kra_percent = round((earned_total / applicable_weight) * 100, 2) if applicable_weight else None

    return {
        "user_id": int(user_id),
        "user_name": user.get("user_name") or "",
        "team_name": user.get("team_name") or "",
        "month_year": month_year,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "as_of_date": today.isoformat(),
        "is_current_month": (year, month) == (today.year, today.month),
        "go_live_month": KRA_GO_LIVE_MONTH,
        "roster_found": bool(roster),
        "goal_working_days": _num(goal_row.get("working_days")),
        "rules": {
            "productivity_hours": PRODUCTIVITY_HOURS,
            "quality_min": QUALITY_MIN,
            "tracker_min": TRACKER_MIN,
            "weights": {
                "productivity": WEIGHT_PRODUCTIVITY,
                "quality": WEIGHT_QUALITY,
                "schedule": WEIGHT_SCHEDULE,
                "reporting": WEIGHT_REPORTING,
                "timeliness": WEIGHT_TIMELINESS,
            },
            "reporting_full_max": REPORTING_FULL_MAX,
            "reporting_partial_max": REPORTING_PARTIAL_MAX,
        },
        "formulas": FORMULAS,
        "days": days,
        "counts": {
            "productivity_yes": productivity_yes,
            "productivity_no": productivity_no,
            "quality_yes": quality_yes,
            "quality_no": quality_no,
            "working_days": working_days,
            "present_days": present_days,
            "low_tracker_days": low_tracker_days,
            "attendance": status_counts,
            "billable_hours": round(billable_total, 2),
            "avg_quality": round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else None,
        },
        "reporting": reporting,
        "inputs": {
            "verbal_warnings": verbal,
            "email_warnings": email,
            "letter_warnings": letter,
            "timeliness_percent": timeliness_earned,
        },
        "scores": [
            {
                "key": "productivity",
                "sr": 1,
                "objective": "Meeting Daily Productivity",
                "weight": WEIGHT_PRODUCTIVITY,
                "earned": productivity_earned,
                "formula": FORMULAS["productivity_score"],
            },
            {
                "key": "quality",
                "sr": 2,
                "objective": "Delivering Right Quality Everyday",
                "weight": WEIGHT_QUALITY,
                "earned": quality_earned,
                "formula": FORMULAS["quality_score"],
            },
            {
                "key": "schedule",
                "sr": 3,
                "objective": "Schedule Adherence — Rostered Attendance",
                "weight": WEIGHT_SCHEDULE,
                "earned": schedule_earned,
                "formula": FORMULAS["schedule_score"],
            },
            {
                "key": "reporting",
                "sr": 4,
                "objective": "Adherence to Reporting in TimeChamp, Project Tracker, and Keka",
                "weight": WEIGHT_REPORTING,
                "earned": reporting_earned,
                "formula": FORMULAS["reporting"],
            },
            {
                "key": "timeliness",
                "sr": 5,
                "objective": "Timeliness — Adherence to break and login schedule",
                "weight": WEIGHT_TIMELINESS,
                "earned": timeliness_earned,
                "formula": FORMULAS["timeliness"],
            },
        ],
        "totals": {
            "earned": earned_total,
            "applicable_weight": applicable_weight,
            "kra_percent": kra_percent,
            "timeliness_included": timeliness_earned is not None,
        },
    }


def save_kra_notes(cursor, actor_id: int, user_id: int, notes: list[dict], *, period_start: date, period_end: date) -> None:
    """Save optional daily notes only. Does not change calculated KRA fields."""
    ensure_kra_note_table(cursor)
    stamp = now_str()
    for item in notes or []:
        work_date = _date_key(item.get("work_date"))
        if not work_date or work_date < period_start or work_date > period_end:
            continue
        note = (item.get("note") or "").strip()[:500]
        if not note:
            cursor.execute(
                "DELETE FROM kra_day_note WHERE user_id=%s AND work_date=%s",
                (int(user_id), work_date),
            )
            continue
        cursor.execute(
            """
            INSERT INTO kra_day_note
                (user_id, work_date, note, updated_by, updated_date)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                note=VALUES(note),
                updated_by=VALUES(updated_by),
                updated_date=VALUES(updated_date)
            """,
            (int(user_id), work_date, note, int(actor_id), stamp),
        )


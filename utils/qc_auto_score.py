"""
Auto QC score when a person-day has tracker rows but nothing to QC:
  all production = 0 and no tracker file → 100% the next morning (~8 AM cron).
"""

from __future__ import annotations

from datetime import date, datetime

from utils.time_ist import now_ist, now_str

AUTO_QC_SCORE = 100.0
# First work date that the next-morning 100% job may score.
# Days before this stay blank until QC types the score (Add/Edit on Billable).
AUTO_QC_EFFECTIVE_FROM = date(2026, 9, 3)
AUTO_QC_EFFECTIVE_FROM_SQL = AUTO_QC_EFFECTIVE_FROM.isoformat()
# Catch-up window if the 8 AM job missed a day (only on/after effective from).
AUTO_QC_LOOKBACK_DAYS = 14

# Training (7) and Sample (8): QC score is typed on Billable, but only if
# the agent worked solely on these projects that day.
MANUAL_QC_PROJECT_IDS = (7, 8)
_MANUAL_QC_IN = ",".join(str(int(i)) for i in MANUAL_QC_PROJECT_IDS)

# Temporary: Add/Edit QC for any project-day that has trackers but no file.
# Set False later to keep Add/Edit only for Training/Sample-only days.
ALLOW_MANUAL_QC_FOR_ANY_NO_FILE_DAY = True

# Person-days with at least one active tracker, zero production, and no files.
# Skip days that are only manual-QC projects (QA must type the score).
# Same-day 0-production is not auto-scored until the next calendar day.
AUTO_QC_DAYS_SQL = f"""
    SELECT
        twt.user_id,
        DATE(CAST(twt.date_time AS DATETIME)) AS work_date,
        100 AS auto_qc_score
    FROM task_work_tracker twt
    WHERE twt.is_active = 1
      AND DATE(CAST(twt.date_time AS DATETIME)) < CURDATE()
      AND DATE(CAST(twt.date_time AS DATETIME)) >= '{AUTO_QC_EFFECTIVE_FROM_SQL}'
    GROUP BY twt.user_id, DATE(CAST(twt.date_time AS DATETIME))
    HAVING COALESCE(SUM(CAST(twt.production AS DECIMAL(18,6))), 0) = 0
       AND SUM(
            CASE
                WHEN twt.tracker_file IS NOT NULL
                 AND TRIM(twt.tracker_file) NOT IN ('', '-', 'N/A')
                THEN 1 ELSE 0
            END
       ) = 0
       AND SUM(CASE WHEN twt.project_id IN ({_MANUAL_QC_IN}) THEN 0 ELSE 1 END) > 0
"""

_NO_FILE_MANUAL_QC_HAVING = """
            OR SUM(
                CASE
                    WHEN twt.tracker_file IS NOT NULL
                     AND TRIM(twt.tracker_file) NOT IN ('', '-', 'N/A')
                    THEN 1 ELSE 0
                END
            ) = 0
""" if ALLOW_MANUAL_QC_FOR_ANY_NO_FILE_DAY else ""

# Add/Edit QC on Billable when the day is only Training/Sample (7/8).
# Temporary: also any project if that whole day has no tracker file.
MANUAL_QC_DAYS_SQL = f"""
    SELECT
        twt.user_id,
        DATE(CAST(twt.date_time AS DATETIME)) AS work_date,
        1 AS can_manual_qc
    FROM task_work_tracker twt
    WHERE twt.is_active = 1
    GROUP BY twt.user_id, DATE(CAST(twt.date_time AS DATETIME))
    HAVING COUNT(*) > 0
       AND (
            SUM(CASE WHEN twt.project_id IN ({_MANUAL_QC_IN}) THEN 0 ELSE 1 END) = 0
            {_NO_FILE_MANUAL_QC_HAVING}
       )
"""

# Days that qualify and do not already have a real QC score (temp_qc or qc_records).
AUTO_QC_DAYS_WITHOUT_EXISTING_SCORE_SQL = f"""
    SELECT
        a.user_id,
        DATE_FORMAT(a.work_date, '%Y-%m-%d') AS qc_date,
        a.auto_qc_score AS daily_qc_avg
    FROM (
        {AUTO_QC_DAYS_SQL}
    ) a
    LEFT JOIN temp_qc tq
      ON tq.user_id = a.user_id
     AND tq.date = DATE_FORMAT(a.work_date, '%Y-%m-%d')
     AND tq.qc_score IS NOT NULL
    LEFT JOIN (
        SELECT
            qr.agent_id,
            DATE(qr.date_of_file_submission) AS qc_date
        FROM qc_records qr
        WHERE qr.qc_score IS NOT NULL
        GROUP BY qr.agent_id, DATE(qr.date_of_file_submission)
    ) qr
      ON qr.agent_id = a.user_id
     AND qr.qc_date = a.work_date
    WHERE tq.user_id IS NULL
      AND qr.agent_id IS NULL
"""


def is_manual_qc_only_day(*, tracker_count, other_project_count) -> bool:
    return int(tracker_count or 0) > 0 and int(other_project_count or 0) == 0


def _day_tracker_stats(cursor, user_id, date_str):
    cursor.execute(
        f"""
        SELECT
            COUNT(*) AS tracker_count,
            COALESCE(SUM(CAST(production AS DECIMAL(18,6))), 0) AS total_production,
            SUM(
                CASE
                    WHEN tracker_file IS NOT NULL
                     AND TRIM(tracker_file) NOT IN ('', '-', 'N/A')
                    THEN 1 ELSE 0
                END
            ) AS file_count,
            SUM(CASE WHEN project_id IN ({_MANUAL_QC_IN}) THEN 0 ELSE 1 END) AS other_count
        FROM task_work_tracker
        WHERE user_id = %s
          AND is_active = 1
          AND DATE(CAST(date_time AS DATETIME)) = %s
        """,
        (int(user_id), date_str),
    )
    row = cursor.fetchone() or {}
    if not isinstance(row, dict):
        return {
            "tracker_count": row[0],
            "total_production": row[1],
            "file_count": row[2],
            "other_count": row[3],
        }
    return row


def day_allows_manual_qc_from_stats(
    *,
    tracker_count,
    other_project_count,
    file_count,
    total_production,
    work_date,
) -> bool:
    n = int(tracker_count or 0)
    if n <= 0:
        return False
    if is_manual_qc_only_day(tracker_count=n, other_project_count=other_project_count):
        return True
    if not ALLOW_MANUAL_QC_FOR_ANY_NO_FILE_DAY:
        return False
    return int(file_count or 0) == 0


def day_allows_manual_qc(cursor, user_id, work_date) -> bool:
    """
    Same rules as MANUAL_QC_DAYS_SQL: 7/8-only days, or (temporary) any
    no-file day.
    """
    date_str = _work_date_str(work_date)
    if not user_id or not date_str:
        return False
    stats = _day_tracker_stats(cursor, user_id, date_str)
    return day_allows_manual_qc_from_stats(
        tracker_count=stats.get("tracker_count"),
        other_project_count=stats.get("other_count"),
        file_count=stats.get("file_count"),
        total_production=stats.get("total_production"),
        work_date=date_str,
    )


def day_is_manual_qc_only(cursor, user_id, work_date) -> bool:
    date_str = _work_date_str(work_date)
    if not user_id or not date_str:
        return False
    placeholders = ",".join(["%s"] * len(MANUAL_QC_PROJECT_IDS))
    cursor.execute(
        f"""
        SELECT
            COUNT(*) AS tracker_count,
            SUM(CASE WHEN project_id IN ({placeholders}) THEN 0 ELSE 1 END) AS other_count
        FROM task_work_tracker
        WHERE user_id = %s
          AND is_active = 1
          AND DATE(CAST(date_time AS DATETIME)) = %s
        """,
        (*MANUAL_QC_PROJECT_IDS, int(user_id), date_str),
    )
    row = cursor.fetchone()
    if not row:
        return False
    if isinstance(row, dict):
        n, other = row.get("tracker_count"), row.get("other_count")
    else:
        n, other = row[0], row[1]
    return is_manual_qc_only_day(tracker_count=n, other_project_count=other)


def should_auto_qc_100(*, tracker_count, total_production, file_count) -> bool:
    if int(tracker_count or 0) <= 0:
        return False
    try:
        prod = float(total_production or 0)
    except (TypeError, ValueError):
        prod = 0.0
    return prod == 0 and int(file_count or 0) == 0


def _work_date_str(work_date) -> str | None:
    if work_date is None:
        return None
    if isinstance(work_date, datetime):
        return work_date.date().isoformat()
    if isinstance(work_date, date):
        return work_date.isoformat()
    s = str(work_date).strip()[:10]
    return s or None


def apply_pending_auto_qc_scores(cursor, as_of_date: date | None = None) -> int:
    """
    Persist 100% QC for eligible past days on/after AUTO_QC_EFFECTIVE_FROM
    (0 production, no file, not manual-QC-only, no existing score).
    Used by the ~8 AM job. Older no-file days stay for Add/Edit QC.
    """
    as_of = as_of_date or now_ist().date()
    as_of_str = as_of.isoformat()
    cursor.execute(
        f"""
        {AUTO_QC_DAYS_WITHOUT_EXISTING_SCORE_SQL}
          AND a.work_date < %s
          AND a.work_date >= DATE_SUB(%s, INTERVAL %s DAY)
        """,
        (as_of_str, as_of_str, AUTO_QC_LOOKBACK_DAYS),
    )
    rows = cursor.fetchall() or []
    updated = now_str()
    count = 0
    for row in rows:
        if isinstance(row, dict):
            uid, qc_date = row.get("user_id"), row.get("qc_date")
        else:
            uid, qc_date = row[0], row[1]
        if not uid or not qc_date:
            continue
        cursor.execute(
            """
            INSERT INTO temp_qc (user_id, qc_score, date, updated_date)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                qc_score = COALESCE(qc_score, VALUES(qc_score)),
                updated_date = VALUES(updated_date)
            """,
            (int(uid), AUTO_QC_SCORE, str(qc_date)[:10], updated),
        )
        count += 1
    return count


def sync_auto_qc_score_for_day(cursor, user_id: int, work_date) -> None:
    """
    Write or clear temp_qc.qc_score = 100 for this agent/date.
    100% is only written after the work date (next-morning cron / later edits).
    Does not overwrite an existing non-null score unless it is the auto 100
    and the day no longer qualifies.
    """
    date_str = _work_date_str(work_date)
    if not user_id or not date_str:
        return
    work_is_past = date_str < now_ist().date().isoformat()
    work_in_auto_window = date_str >= AUTO_QC_EFFECTIVE_FROM_SQL

    cursor.execute(
        """
        SELECT
            COUNT(*) AS tracker_count,
            COALESCE(SUM(CAST(production AS DECIMAL(18,6))), 0) AS total_production,
            SUM(
                CASE
                    WHEN tracker_file IS NOT NULL
                     AND TRIM(tracker_file) NOT IN ('', '-', 'N/A')
                    THEN 1 ELSE 0
                END
            ) AS file_count
        FROM task_work_tracker
        WHERE user_id = %s
          AND is_active = 1
          AND DATE(CAST(date_time AS DATETIME)) = %s
        """,
        (int(user_id), date_str),
    )
    row = cursor.fetchone() or {}
    eligible = should_auto_qc_100(
        tracker_count=row.get("tracker_count"),
        total_production=row.get("total_production"),
        file_count=row.get("file_count"),
    ) and not day_is_manual_qc_only(cursor, user_id, date_str)

    cursor.execute(
        """
        SELECT COUNT(*) AS n
        FROM qc_records
        WHERE agent_id = %s
          AND DATE(date_of_file_submission) = %s
          AND qc_score IS NOT NULL
        """,
        (int(user_id), date_str),
    )
    has_qc_form = int((cursor.fetchone() or {}).get("n") or 0) > 0

    cursor.execute(
        """
        SELECT qc_score
        FROM temp_qc
        WHERE user_id = %s AND date = %s
        LIMIT 1
        """,
        (int(user_id), date_str),
    )
    existing = cursor.fetchone()
    existing_score = None if not existing else existing.get("qc_score")
    try:
        existing_num = None if existing_score is None else float(existing_score)
    except (TypeError, ValueError):
        existing_num = None

    updated = now_str()

    if eligible and not has_qc_form and work_is_past and work_in_auto_window:
        if existing_num is not None:
            return
        cursor.execute(
            """
            INSERT INTO temp_qc (user_id, qc_score, date, updated_date)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                qc_score = COALESCE(qc_score, VALUES(qc_score)),
                updated_date = VALUES(updated_date)
            """,
            (int(user_id), AUTO_QC_SCORE, date_str, updated),
        )
        return

    # Day no longer qualifies: drop only the auto 100 so a later QC form can apply.
    if existing_num == AUTO_QC_SCORE and not has_qc_form:
        cursor.execute(
            """
            UPDATE temp_qc
            SET qc_score = NULL, updated_date = %s
            WHERE user_id = %s AND date = %s AND qc_score = %s
            """,
            (updated, int(user_id), date_str, AUTO_QC_SCORE),
        )

"""
Auto QC score when a person-day has tracker rows but nothing to QC:
  all production = 0 and no tracker file → 100%.
"""

from __future__ import annotations

from datetime import date, datetime

from utils.time_ist import now_str

AUTO_QC_SCORE = 100.0

# Training (7) and Sample (8): QC score is typed on Billable, but only if
# the agent worked solely on these projects that day.
MANUAL_QC_PROJECT_IDS = (7, 8)
_MANUAL_QC_IN = ",".join(str(int(i)) for i in MANUAL_QC_PROJECT_IDS)

# Person-days with at least one active tracker, zero production, and no files.
# Skip days that are only manual-QC projects (QA must type the score).
AUTO_QC_DAYS_SQL = f"""
    SELECT
        twt.user_id,
        DATE(CAST(twt.date_time AS DATETIME)) AS work_date,
        100 AS auto_qc_score
    FROM task_work_tracker twt
    WHERE twt.is_active = 1
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

# Days where every active tracker is project 7 and/or 8.
MANUAL_QC_DAYS_SQL = f"""
    SELECT
        twt.user_id,
        DATE(CAST(twt.date_time AS DATETIME)) AS work_date,
        1 AS can_manual_qc
    FROM task_work_tracker twt
    WHERE twt.is_active = 1
    GROUP BY twt.user_id, DATE(CAST(twt.date_time AS DATETIME))
    HAVING COUNT(*) > 0
       AND SUM(CASE WHEN twt.project_id IN ({_MANUAL_QC_IN}) THEN 0 ELSE 1 END) = 0
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


def sync_auto_qc_score_for_day(cursor, user_id: int, work_date) -> None:
    """
    Write or clear temp_qc.qc_score = 100 for this agent/date.
    Does not overwrite an existing non-null score unless it is the auto 100
    and the day no longer qualifies.
    """
    date_str = _work_date_str(work_date)
    if not user_id or not date_str:
        return

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

    if eligible and not has_qc_form:
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

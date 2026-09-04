"""
To/CC for billable + tracker reports.

Prefer rows in report_email_recipient (edited in HRMS).
If the table is empty or DB is down, fall back to the lists below.
"""

from __future__ import annotations

import re

REPORT_BILLABLE = "billable"
REPORT_TRACKER = "tracker"
REPORT_TRACKER_FULL = "tracker_full"
REPORT_FLAG_COLUMNS = {
    REPORT_BILLABLE: "send_billable",
    REPORT_TRACKER: "send_tracker",
    REPORT_TRACKER_FULL: "send_tracker_full",
}

DEFAULT_RECIPIENTS = [
    "ummehabiba.siddiquie@transformsolution.net",
    "dharmesh.jotania@transformsolution.net",
    "yahya.irani@transformsolution.net",
    "amit.mandviwala@transformsolution.net",
    "sriman.narayan@transformsolution.net",
    "shirin.gafoor@transformsolution.net",
    "avinash.dwivedi@transformsolution.net",
    "manas.pradhan@transformsolution.net",
]

DEFAULT_CC_RECIPIENTS = [
    "ashfaq@transformsolution.com",
    "seema@transformsolution.com",
]
# Used only if the DB list cannot be read. Seema is billable-only in production.
DEFAULT_CC_TRACKER = [
    "ashfaq@transformsolution.com",
]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS report_email_recipient (
    recipient_id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    recipient_type VARCHAR(8) NOT NULL DEFAULT 'to',
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    send_billable TINYINT(1) NOT NULL DEFAULT 1,
    send_tracker TINYINT(1) NOT NULL DEFAULT 1,
    send_tracker_full TINYINT(1) NOT NULL DEFAULT 1,
    created_date DATETIME NULL,
    updated_date DATETIME NULL
)
"""


def normalize_email(value) -> str:
    return (value or "").strip().lower()


def is_valid_email(value) -> bool:
    email = normalize_email(value)
    return bool(email) and EMAIL_RE.match(email) is not None


def normalize_type(value) -> str:
    kind = (value or "to").strip().lower()
    return "cc" if kind == "cc" else "to"


def normalize_report(value) -> str:
    key = (value or REPORT_BILLABLE).strip().lower()
    return key if key in REPORT_FLAG_COLUMNS else REPORT_BILLABLE


def flag_int(value, default=1) -> int:
    if value is None:
        return default
    if isinstance(value, (bytes, bytearray)):
        if not value:
            return 0
        return 1 if value[-1] else 0
    if isinstance(value, bool):
        return 1 if value else 0
    s = str(value).strip().lower()
    if s in ("0", "false", "no", "off"):
        return 0
    if s in ("1", "true", "yes", "on"):
        return 1
    try:
        return 1 if int(float(value)) else 0
    except (TypeError, ValueError):
        return default


def default_report_flags() -> dict[str, int]:
    return {"send_billable": 1, "send_tracker": 1, "send_tracker_full": 1}


def ensure_table(cursor) -> None:
    cursor.execute(CREATE_TABLE_SQL)
    for col in REPORT_FLAG_COLUMNS.values():
        cursor.execute("SHOW COLUMNS FROM report_email_recipient LIKE %s", (col,))
        if not cursor.fetchone():
            cursor.execute(
                f"ALTER TABLE report_email_recipient "
                f"ADD COLUMN {col} TINYINT(1) NOT NULL DEFAULT 1"
            )
    collapse_duplicate_emails(cursor)
    try:
        cursor.execute(
            """
            ALTER TABLE report_email_recipient
            ADD UNIQUE INDEX uq_report_email_recipient_email (email)
            """
        )
    except Exception:
        pass


def collapse_duplicate_emails(cursor) -> None:
    """One row per email. Keep the active row if any, else the oldest."""
    cursor.execute(
        """
        SELECT
            LOWER(email) AS em,
            MIN(CASE WHEN is_active = 1 THEN recipient_id END) AS active_id,
            MIN(recipient_id) AS oldest_id,
            COUNT(*) AS n
        FROM report_email_recipient
        GROUP BY LOWER(email)
        HAVING COUNT(*) > 1
        """
    )
    groups = list(cursor.fetchall() or [])
    for row in groups:
        keeper = row.get("active_id") or row.get("oldest_id")
        if not keeper:
            continue
        cursor.execute(
            """
            DELETE FROM report_email_recipient
            WHERE LOWER(email) = %s AND recipient_id != %s
            """,
            (row.get("em"), keeper),
        )


def find_row_by_email(cursor, email: str):
    cursor.execute(
        """
        SELECT recipient_id, email, recipient_type, is_active
        FROM report_email_recipient
        WHERE LOWER(email) = %s
        ORDER BY is_active DESC, recipient_id ASC
        LIMIT 1
        """,
        (normalize_email(email),),
    )
    return cursor.fetchone()


def seed_defaults_if_empty(cursor, now_str: str) -> None:
    cursor.execute(
        "SELECT COUNT(*) AS n FROM report_email_recipient WHERE is_active = 1"
    )
    row = cursor.fetchone() or {}
    n = int((row.get("n") if isinstance(row, dict) else row[0]) or 0)
    if n > 0:
        return
    for email in DEFAULT_RECIPIENTS:
        flags = default_report_flags()
        cursor.execute(
            """
            INSERT INTO report_email_recipient (
                email, recipient_type, is_active,
                send_billable, send_tracker, send_tracker_full,
                created_date, updated_date
            )
            SELECT %s, 'to', 1, %s, %s, %s, %s, %s
            FROM DUAL
            WHERE NOT EXISTS (
                SELECT 1 FROM report_email_recipient
                WHERE LOWER(email) = %s AND is_active = 1
            )
            """,
            (
                normalize_email(email),
                flags["send_billable"],
                flags["send_tracker"],
                flags["send_tracker_full"],
                now_str,
                now_str,
                normalize_email(email),
            ),
        )
    for email in DEFAULT_CC_RECIPIENTS:
        flags = default_report_flags()
        cursor.execute(
            """
            INSERT INTO report_email_recipient (
                email, recipient_type, is_active,
                send_billable, send_tracker, send_tracker_full,
                created_date, updated_date
            )
            SELECT %s, 'cc', 1, %s, %s, %s, %s, %s
            FROM DUAL
            WHERE NOT EXISTS (
                SELECT 1 FROM report_email_recipient
                WHERE LOWER(email) = %s AND is_active = 1
            )
            """,
            (
                normalize_email(email),
                flags["send_billable"],
                flags["send_tracker"],
                flags["send_tracker_full"],
                now_str,
                now_str,
                normalize_email(email),
            ),
        )


def fetch_active_rows(cursor) -> list[dict]:
    cursor.execute(
        """
        SELECT
            recipient_id, email, recipient_type,
            send_billable, send_tracker, send_tracker_full
        FROM report_email_recipient
        WHERE is_active = 1
        ORDER BY recipient_type ASC, recipient_id ASC
        """
    )
    rows = list(cursor.fetchall() or [])
    return [normalize_row_flags(r) if isinstance(r, dict) else r for r in rows]


def normalize_row_flags(row: dict) -> dict:
    if not isinstance(row, dict):
        return row
    row["send_billable"] = flag_int(row.get("send_billable"), 1)
    row["send_tracker"] = flag_int(row.get("send_tracker"), 1)
    row["send_tracker_full"] = flag_int(row.get("send_tracker_full"), 1)
    return row


def row_gets_report(row, report: str) -> bool:
    col = REPORT_FLAG_COLUMNS.get(normalize_report(report))
    if not col:
        return True
    if isinstance(row, dict):
        return flag_int(row.get(col), 1) == 1
    return True


def lists_from_rows(rows, report: str | None = None) -> tuple[list[str], list[str]]:
    to_list: list[str] = []
    cc_list: list[str] = []
    seen_to = set()
    seen_cc = set()
    report_key = normalize_report(report) if report else None
    for row in rows or []:
        if report_key and not row_gets_report(row, report_key):
            continue
        email = normalize_email(row.get("email") if isinstance(row, dict) else row[1])
        kind = normalize_type(
            row.get("recipient_type") if isinstance(row, dict) else row[2]
        )
        if not email:
            continue
        if kind == "cc":
            if email not in seen_cc:
                cc_list.append(email)
                seen_cc.add(email)
        else:
            if email not in seen_to:
                to_list.append(email)
                seen_to.add(email)
    return to_list, cc_list


def fallback_lists(report: str) -> tuple[list[str], list[str]]:
    report_key = normalize_report(report)
    cc = list(DEFAULT_CC_RECIPIENTS) if report_key == REPORT_BILLABLE else list(DEFAULT_CC_TRACKER)
    return list(DEFAULT_RECIPIENTS), cc


def get_report_email_lists(report: str = REPORT_BILLABLE) -> tuple[list[str], list[str]]:
    """Used by cron senders. Never raises for DB issues — falls back to defaults."""
    report_key = normalize_report(report)
    try:
        from config import get_db_connection
        from utils.time_ist import now_str

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            ensure_table(cursor)
            seed_defaults_if_empty(cursor, now_str())
            conn.commit()
            to_list, cc_list = lists_from_rows(fetch_active_rows(cursor), report_key)
            if to_list:
                print(
                    f"[report_email_recipients] {report_key} from DB "
                    f"to={len(to_list)} cc={cc_list}"
                )
                return to_list, cc_list
            print(f"[report_email_recipients] {report_key} DB To list empty; using file defaults")
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"[report_email_recipients] Using file defaults ({e})")
    return fallback_lists(report_key)

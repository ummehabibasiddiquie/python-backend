"""
To/CC for billable + tracker reports.

Recipients come only from report_email_recipient (edited in HRMS).
If there are no To emails or the DB cannot be read, log and return empty lists.
Do not fall back to hardcoded addresses.
"""

from __future__ import annotations

import os
import re

import mysql.connector
from dotenv import load_dotenv
from pathlib import Path

REPORT_BILLABLE = "billable"
REPORT_TRACKER = "tracker"
REPORT_TRACKER_FULL = "tracker_full"
REPORT_FLAG_COLUMNS = {
    REPORT_BILLABLE: "send_billable",
    REPORT_TRACKER: "send_tracker",
    REPORT_TRACKER_FULL: "send_tracker_full",
}

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


def _db_connection():
    """MySQL only — do not import config.py (that requires cloudinary for Flask)."""
    load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_DATABASE", "tfs_hrms"),
    )


def get_report_email_lists(report: str = REPORT_BILLABLE) -> tuple[list[str], list[str]]:
    """Cron senders: database only. Empty lists if missing or DB error."""
    report_key = normalize_report(report)
    try:
        conn = _db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            ensure_table(cursor)
            to_list, cc_list = lists_from_rows(fetch_active_rows(cursor), report_key)
            if not to_list:
                print(
                    f"[report_email_recipients] {report_key} no To emails in database; skip send"
                )
                return [], []
            print(
                f"[report_email_recipients] {report_key} from DB "
                f"to={len(to_list)} cc={cc_list}"
            )
            return to_list, cc_list
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(
            f"[report_email_recipients] {report_key} database lookup failed; skip send ({e})"
        )
        return [], []

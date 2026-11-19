"""
Monthly tenure update from Company Joining Date.

Who:
  Active Agent role only, with tenure 1 or above.
  Tenure below 1 is never changed here (manual).
  QA and other roles are not updated.

When a step applies:
  First step 1 → 1.15 after 13 months from company joining date,
  then 1.25 / 1.35 / 1.45 every 12 months after that.
  The new tenure starts on the 1st of the month AFTER that anniversary.

Never decreases tenure if the person is already above the calculated step.

After a live update, every active Project Manager is emailed, plus only the
Assistant Manager(s) assigned on that agent. Time completed from company DOJ,
old tenure → new tenure, and the IST time of the change. The agent is not emailed.

Usage:
  python update_agent_tenure.py --dry-run
  python update_agent_tenure.py --dry-run --date 2026-12-01
  python update_agent_tenure.py

Cron (1st of every month, 09:00 IST):
  0 9 1 * * cd /root/tfshrms/hrms-backend && venv/bin/python update_agent_tenure.py >> logs/update_agent_tenure.log 2>&1
"""

from __future__ import annotations

import argparse
import calendar
import json
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(dotenv_path=BASE_DIR / ".env")

from utils.email_utils import send_email  # noqa: E402
from utils.time_ist import now_str as ist_now_str  # noqa: E402

LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "update_agent_tenure.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

# 1.00 → 1.15 after 13 months, then +12 months each step.
TENURE_STEPS = (1.15, 1.25, 1.35, 1.45)
FIRST_STEP_MONTHS = 13
LATER_STEP_MONTHS = 12
MIN_AUTO_TENURE = 1.0
ELIGIBLE_ROLES = ("agent",)


def add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def first_of_next_month(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def parse_joining(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()[:10]
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def format_tenure(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.2f}"


def parse_tenure(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_id_list(val) -> list[int]:
    if val is None:
        return []
    if isinstance(val, list):
        return [int(x) for x in val if str(x).strip().lstrip("-").isdigit()]
    if isinstance(val, int):
        return [val]
    text = str(val).strip()
    if not text:
        return []
    if text.isdigit():
        return [int(text)]
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if isinstance(parsed, list):
        return [int(x) for x in parsed if str(x).strip().lstrip("-").isdigit()]
    if isinstance(parsed, int):
        return [parsed]
    return []


def service_duration_label(joining: date, as_of: date) -> str:
    months = (as_of.year - joining.year) * 12 + (as_of.month - joining.month)
    if as_of.day < joining.day:
        months -= 1
    months = max(0, months)
    years, rem = divmod(months, 12)
    parts = []
    if years:
        parts.append(f"{years} year" if years == 1 else f"{years} years")
    if rem:
        parts.append(f"{rem} month" if rem == 1 else f"{rem} months")
    if not parts:
        return "less than 1 month"
    return " ".join(parts)


def all_project_manager_emails(cursor) -> list[dict]:
    cursor.execute(
        """
        SELECT u.user_id, u.user_name, u.user_email
        FROM tfs_user u
        JOIN user_role r ON r.role_id = u.role_id
        WHERE u.is_active = 1 AND u.is_delete = 1
          AND LOWER(TRIM(r.role_name)) = 'project manager'
          AND u.user_email IS NOT NULL AND TRIM(u.user_email) <> ''
        """
    )
    return cursor.fetchall() or []


def assigned_assistant_manager_emails(cursor, am_ids: list[int]) -> list[dict]:
    ids = list(dict.fromkeys(int(i) for i in am_ids if i))
    if not ids:
        return []
    placeholders = ",".join(["%s"] * len(ids))
    cursor.execute(
        f"""
        SELECT user_id, user_name, user_email
        FROM tfs_user
        WHERE user_id IN ({placeholders})
          AND is_active = 1 AND is_delete = 1
          AND user_email IS NOT NULL AND TRIM(user_email) <> ''
        """,
        tuple(ids),
    )
    return cursor.fetchall() or []


def tenure_update_email_html(payload: dict) -> str:
    return f"""
    <p>Hello,</p>
    <p>
      Tenure has been updated for <strong>{payload['agent_name']}</strong>
      ({payload['agent_email'] or 'no email'}).
    </p>
    <table cellpadding="6" cellspacing="0" border="1" style="border-collapse:collapse;">
      <tr><td>Company joining date</td><td>{payload['doj']}</td></tr>
      <tr><td>Time completed</td><td>{payload['completed']}</td></tr>
      <tr><td>Tenure</td><td>{payload['old_tenure']} → {payload['new_tenure']}</td></tr>
      <tr><td>Daily assigned hours</td><td>{payload['hours']}</td></tr>
      <tr><td>Updated at (IST)</td><td>{payload['updated_at']}</td></tr>
    </table>
    <p>This is an automatic mail from HRMS. Please do not reply.</p>
    """


def send_tenure_update_mail(payload: dict, recipients: list[dict]) -> bool:
    to_list = []
    seen = set()
    for row in recipients:
        email = (row.get("user_email") or "").strip()
        key = email.lower()
        if not email or key in seen:
            continue
        if key == (payload.get("agent_email") or "").strip().lower():
            continue
        seen.add(key)
        to_list.append(email)
    if not to_list:
        logging.warning(
            "[MAIL SKIP] %s: no Project Manager or assigned Assistant Manager email",
            payload["agent_name"],
        )
        return False
    subject = (
        f"Tenure updated: {payload['agent_name']} "
        f"({payload['old_tenure']} → {payload['new_tenure']})"
    )
    send_email(to_list, subject, tenure_update_email_html(payload))
    logging.info(
        "[MAIL] %s: sent to %s",
        payload["agent_name"],
        ", ".join(to_list),
    )
    return True


def expected_tenure(joining: date, as_of: date) -> float:
    """Highest step whose effective date (1st after anniversary) is on or before as_of."""
    result = MIN_AUTO_TENURE
    for i, step in enumerate(TENURE_STEPS):
        months = FIRST_STEP_MONTHS + i * LATER_STEP_MONTHS
        effective = first_of_next_month(add_months(joining, months))
        if as_of >= effective:
            result = step
        else:
            break
    return result


def tenure_cap(user_tenure) -> float:
    try:
        t = float(user_tenure)
    except (TypeError, ValueError):
        t = 1.0
    return max(0.0, min(1.0, t))


def calculate_assigned_hours(new_tenure: str) -> float:
    return round(9.0 * tenure_cap(new_tenure), 2)


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_DATABASE", "tfs_hrms"),
    )


def run_tenure_update(dry_run: bool = False, as_of: date | None = None, target_date_str: str | None = None):
    as_of = as_of or date.today()
    mode_str = "[DRY-RUN]" if dry_run else "[LIVE UPDATE]"
    logging.info("==================================================")
    logging.info("Starting Company-DOJ tenure update %s as of %s", mode_str, as_of.isoformat())
    logging.info("==================================================")

    today_str = target_date_str or datetime.now().strftime("%Y-%m-%d")
    now_str = ist_now_str()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    stats = {
        "would_update": 0,
        "already_ok": 0,
        "below_one": 0,
        "no_joining_date": 0,
        "kept_higher": 0,
        "errors": 0,
        "mailed": 0,
        "mail_failed": 0,
    }
    pending_mails: list[tuple[dict, list[dict]]] = []

    try:
        cursor.execute(
            """
            SELECT u.user_id, u.user_name, u.user_email, u.user_tenure,
                   u.company_joining_date, u.project_manager_id, u.asst_manager_id,
                   r.role_name
            FROM tfs_user u
            JOIN user_role r ON r.role_id = u.role_id
            LEFT JOIN team t ON t.team_id = u.team_id
            WHERE u.is_active = 1 AND u.is_delete = 1
              AND LOWER(TRIM(r.role_name)) = %s
              AND (
                    t.team_name IS NULL
                    OR LOWER(TRIM(u.user_name)) <> LOWER(TRIM(t.team_name))
              )
            ORDER BY u.user_name
            """,
            ELIGIBLE_ROLES,
        )
        rows = cursor.fetchall() or []
        all_pms = all_project_manager_emails(cursor)

        for user in rows:
            name = user.get("user_name") or ""
            uid = user["user_id"]
            current = parse_tenure(user.get("user_tenure"))
            if current is None:
                logging.warning("[SKIP] %s (ID %s): invalid tenure %r", name, uid, user.get("user_tenure"))
                stats["errors"] += 1
                continue
            if current < MIN_AUTO_TENURE - 1e-9:
                logging.info("[SKIP <1] %s (ID %s): tenure %s stays manual", name, uid, user.get("user_tenure"))
                stats["below_one"] += 1
                continue

            joining = parse_joining(user.get("company_joining_date"))
            if joining is None:
                logging.warning(
                    "[NO COMPANY DOJ] %s (ID %s): tenure %s — fill company_joining_date",
                    name, uid, user.get("user_tenure"),
                )
                stats["no_joining_date"] += 1
                continue

            want = expected_tenure(joining, as_of)
            want_str = format_tenure(want)
            current_str = format_tenure(current)
            first_bump = first_of_next_month(add_months(joining, FIRST_STEP_MONTHS))

            if abs(want - current) < 1e-4:
                logging.info(
                    "[OK] %s (ID %s): %s (DOJ %s, first auto bump %s)",
                    name, uid, current_str, joining.isoformat(), first_bump.isoformat(),
                )
                stats["already_ok"] += 1
                continue

            if current > want + 1e-4:
                logging.info(
                    "[KEEP HIGHER] %s (ID %s): DB %s > calculated %s (DOJ %s) — not decreasing",
                    name, uid, current_str, want_str, joining.isoformat(),
                )
                stats["kept_higher"] += 1
                continue

            logging.info(
                "[UPDATE] %s (ID %s): %s -> %s (DOJ %s, first auto bump %s)",
                name, uid, current_str, want_str, joining.isoformat(), first_bump.isoformat(),
            )
            stats["would_update"] += 1
            hours = calculate_assigned_hours(want_str)
            payload = {
                "agent_name": name,
                "agent_email": (user.get("user_email") or "").strip(),
                "doj": joining.isoformat(),
                "completed": service_duration_label(joining, as_of),
                "old_tenure": current_str,
                "new_tenure": want_str,
                "hours": hours,
                "updated_at": now_str,
            }
            assigned_ams = assigned_assistant_manager_emails(
                cursor, parse_id_list(user.get("asst_manager_id"))
            )
            recipients = all_pms + assigned_ams
            if dry_run:
                emails = ", ".join(
                    (r.get("user_email") or "").strip()
                    for r in recipients
                    if (r.get("user_email") or "").strip()
                ) or "(no PM/AM email)"
                logging.info("[MAIL DRY-RUN] %s → %s", name, emails)
                continue

            cursor.execute(
                "UPDATE tfs_user SET user_tenure = %s WHERE user_id = %s",
                (want_str, uid),
            )
            cursor.execute(
                """
                INSERT INTO temp_qc (user_id, assigned_hours, date, updated_date)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    assigned_hours = VALUES(assigned_hours),
                    updated_date = VALUES(updated_date)
                """,
                (uid, hours, today_str, now_str),
            )
            pending_mails.append((payload, recipients))

        if dry_run:
            logging.info("\n--- DRY-RUN (no database changes, no mail sent) ---")
        else:
            conn.commit()
            logging.info("\n--- LIVE UPDATE committed ---")
            for payload, recipients in pending_mails:
                try:
                    if send_tenure_update_mail(payload, recipients):
                        stats["mailed"] += 1
                except Exception:
                    stats["mail_failed"] += 1
                    logging.exception("[MAIL FAIL] %s", payload["agent_name"])

        logging.info("Would update / updated : %s", stats["would_update"])
        logging.info("Already on correct step: %s", stats["already_ok"])
        logging.info("Kept higher than calc  : %s", stats["kept_higher"])
        logging.info("Skipped tenure < 1     : %s", stats["below_one"])
        logging.info("Missing company DOJ    : %s", stats["no_joining_date"])
        logging.info("Manager mails sent     : %s", stats["mailed"])
        logging.info("Manager mails failed   : %s", stats["mail_failed"])
        logging.info("Errors                 : %s", stats["errors"])
        logging.info("==================================================")
        return stats

    except Exception:
        conn.rollback()
        logging.exception("CRITICAL ERROR during tenure update")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monthly tenure update from company joining date")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing to the database")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="As-of date YYYY-MM-DD (default today). Also used for temp_qc hours on live run.",
    )
    args = parser.parse_args()
    as_of = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    run_tenure_update(dry_run=args.dry_run, as_of=as_of, target_date_str=args.date)

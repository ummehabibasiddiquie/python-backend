"""
update_agent_tenure.py

Standalone script to update employee tenure in tfs_user.
Designed to run via cron on 1st November at 09:00 AM (or manually).

Scheduled updates:
  1. Shivkumar Prajapati (User ID 195) : 0.50 -> 0.75
  2. Udit Kamani         (User ID 135) : 1.25 -> 1.35
  3. Virendra Singh      (User ID 188) : 0.75 -> 1
  4. Swapnil Patel       (User ID 155) : 1.00 -> 1.15

Features:
  - Validates current DB tenure against old_tenure before updating.
  - Updates tfs_user.user_tenure.
  - Updates temp_qc.assigned_hours for 1st Nov so that daily hours
    reflect the new tenure even if the 08:00 AM assign-hours cron ran earlier.
  - Supports --dry-run to test in advance without modifying the database.
  - Comprehensive logging to console and logs/update_agent_tenure.log.

Usage:
  # Test without making changes (safe to run anytime):
  python update_agent_tenure.py --dry-run

  # Apply updates:
  python update_agent_tenure.py

Cron Setup (runs Nov 1 at 09:00 AM IST):
  # If server timezone is IST:
  0 9 1 11 * cd /path/to/backend-api && /path/to/venv/bin/python update_agent_tenure.py >> logs/update_agent_tenure.log 2>&1

  # If server timezone is UTC (09:00 IST = 03:30 UTC):
  30 3 1 11 * cd /path/to/backend-api && /path/to/venv/bin/python update_agent_tenure.py >> logs/update_agent_tenure.log 2>&1
"""

import argparse
from datetime import datetime
import logging
import os
from pathlib import Path
import sys
import mysql.connector
from dotenv import load_dotenv

# -------------------------------
# CONFIG & LOGGING
# -------------------------------
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "update_agent_tenure.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"   ),
        logging.StreamHandler(sys.stdout),
    ],
)

# -------------------------------
# AGENT TENURE UPDATE LIST
# -------------------------------
TENURE_UPDATES = [
    {
        "user_id": 195,
        "user_name": "Shivkumar Prajapati",
        "email": "shivkumar.prajapati@transformsolution.net",
        "old_tenure": "0.50",
        "new_tenure": "0.75",
    },
    {
        "user_id": 135,
        "user_name": "Udit Kamani",
        "email": "udit.kamani@transformsolution.net",
        "old_tenure": "1.25",
        "new_tenure": "1.35",
    },
    {
        "user_id": 188,
        "user_name": "Virendra Singh",
        "email": "virendra.singh@transformsolution.net",
        "old_tenure": "0.75",
        "new_tenure": "1",
    },
    {
        "user_id": 155,
        "user_name": "Swapnil Patel",
        "email": "swapnil.patel@transformsolution.net",
        "old_tenure": "1.00",
        "new_tenure": "1.15",
    },
]


# -------------------------------
# DB CONNECTION
# -------------------------------
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_DATABASE", "tfs_hrms"),
    )


def tenure_cap(user_tenure) -> float:
    """Cap tenure to [0, 1] for daily hour assignment (max 9 hours)."""
    try:
        t = float(user_tenure)
    except (TypeError, ValueError):
        t = 1.0
    return max(0.0, min(1.0, t))


def calculate_assigned_hours(new_tenure: str, day_type: str = "Working", working_type: str = "Full") -> float:
    """
    Standard formula from utils.roster_helpers:
      Full working day = 9 * tenure (capped at 9)
      Half working day = 4.5 * tenure
    """
    factor = tenure_cap(new_tenure)
    wt = (working_type or "Full").strip()
    dt = (day_type or "Working").strip()
    if dt in ("WeekOff", "Holiday", "Leave", "Left", "PreJoin"):
        return 0.0
    if wt == "Half":
        return round(4.5 * factor, 2)
    return round(9.0 * factor, 2)


def is_tenure_equal(val1, val2) -> bool:
    """Compare two tenure values numerically to handle '1.00' == '1' or '0.50' == '0.5'."""
    try:
        return abs(float(val1) - float(val2)) < 1e-4
    except (TypeError, ValueError):
        return str(val1).strip() == str(val2).strip()


def run_tenure_update(dry_run: bool = False, target_date_str: str | None = None):
    mode_str = "[DRY-RUN]" if dry_run else "[LIVE UPDATE]"
    logging.info("==================================================")
    logging.info(f"Starting Agent Tenure Update {mode_str}")
    logging.info(f"Total agents in queue: {len(TENURE_UPDATES)}")
    logging.info("==================================================")

    if not TENURE_UPDATES:
        logging.warning("No agents defined in TENURE_UPDATES.")
        return

    today_str = target_date_str or datetime.now().strftime("%Y-%m-%d")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    stats = {
        "success": 0,
        "mismatched_old_tenure": 0,
        "not_found": 0,
        "already_updated": 0,
        "errors": 0,
    }

    try:
        for item in TENURE_UPDATES:
            user_id = item.get("user_id")
            user_name_hint = item.get("user_name", "")
            expected_email = str(item.get("email", "")).strip().lower()
            expected_old = str(item.get("old_tenure", "")).strip()
            new_tenure = str(item.get("new_tenure", "")).strip()

            if not user_id or not new_tenure:
                logging.error(f"Skipping invalid entry: {item}")
                stats["errors"] += 1
                continue

            cursor.execute(
                """
                SELECT user_id, user_name, user_email, user_tenure, is_active, is_delete 
                FROM tfs_user 
                WHERE user_id = %s
                """,
                (user_id,),
            )
            user = cursor.fetchone()

            if not user:
                logging.warning(f"[NOT FOUND] User ID '{user_id}' ({user_name_hint})")
                stats["not_found"] += 1
                continue

            actual_name = user["user_name"]
            actual_email = (user["user_email"] or "").strip().lower()
            current_db_tenure = str(user["user_tenure"] or "").strip()

            # Safety check: Verify email matches
            if expected_email and actual_email != expected_email:
                logging.warning(
                    f"[EMAIL MISMATCH] ID {user_id}: expected email '{expected_email}' but found '{actual_email}'. Skipping."
                )
                stats["errors"] += 1
                continue

            # Check if already updated
            if is_tenure_equal(current_db_tenure, new_tenure):
                logging.info(
                    f"[ALREADY UPDATED] {actual_name} ({actual_email}, ID: {user_id}) - current tenure is already '{current_db_tenure}'"
                )
                stats["already_updated"] += 1
                continue

            # Verify old tenure matches before updating
            if expected_old and not is_tenure_equal(current_db_tenure, expected_old):
                logging.warning(
                    f"[MISMATCH] {actual_name} ({actual_email}, ID: {user_id}): Expected old tenure '{expected_old}', but found '{current_db_tenure}' in DB. Skipping."
                )
                stats["mismatched_old_tenure"] += 1
                continue

            logging.info(
                f"[MATCH] {actual_name} ({actual_email}, ID: {user_id}): '{current_db_tenure}' -> '{new_tenure}'"
            )

            if not dry_run:
                # 1. Update tfs_user table
                cursor.execute(
                    "UPDATE tfs_user SET user_tenure = %s WHERE user_id = %s",
                    (new_tenure, user_id),
                )

                # 2. Recalculate today's assigned hours in temp_qc
                new_assigned_hours = calculate_assigned_hours(new_tenure)
                cursor.execute(
                    """
                    INSERT INTO temp_qc (user_id, assigned_hours, date, updated_date)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        assigned_hours = VALUES(assigned_hours),
                        updated_date = VALUES(updated_date)
                    """,
                    (user_id, new_assigned_hours, today_str, now_str),
                )

            stats["success"] += 1

        if dry_run:
            logging.info("\n--- DRY-RUN SUMMARY (No database changes were committed) ---")
        else:
            conn.commit()
            logging.info("\n--- LIVE UPDATE SUMMARY (Changes successfully committed to DB) ---")

        logging.info(f"Successfully processed/updated : {stats['success']}")
        logging.info(f"Already had new tenure        : {stats['already_updated']}")
        logging.info(f"Skipped (old tenure mismatch) : {stats['mismatched_old_tenure']}")
        logging.info(f"Not found in database         : {stats['not_found']}")
        logging.info(f"Invalid / Error entries       : {stats['errors']}")
        logging.info("==================================================")

    except Exception as e:
        conn.rollback()
        logging.exception(f"CRITICAL ERROR during tenure update: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone Agent Tenure Updater")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the update and print actions without modifying the database.",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Target date for temp_qc assigned hours sync (YYYY-MM-DD, defaults to today).",
    )
    args = parser.parse_args()

    run_tenure_update(dry_run=args.dry_run, target_date_str=args.date)

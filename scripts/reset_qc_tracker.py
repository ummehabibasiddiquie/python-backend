"""Reset/Delete QC records for a specific tracker and reopen it for QC.

Reference: docs/reset-qc-for-tracker.md
Usage:
    python scripts/reset_qc_tracker.py --tracker-id 45092
    python scripts/reset_qc_tracker.py --tracker-id 45092 --host <HOST> --user <USER> --database <DB>
"""

from __future__ import annotations

import argparse
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to sys.path to access config/env if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.hostinger_db import connect


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Delete QC records for a tracker and reset qc_status to 0")
    p.add_argument("--tracker-id", type=int, required=True, help="Tracker ID to reset QC for")
    p.add_argument("--host", default=os.getenv("DB_HOST", "localhost"))
    p.add_argument("--port", type=int, default=int(os.getenv("DB_PORT", "3306")))
    p.add_argument("--user", default=os.getenv("DB_USERNAME", "root"))
    p.add_argument("--database", default=os.getenv("DB_DATABASE", "tfs_hrms"))
    p.add_argument("--password", default=None, help="MySQL password (optional)")
    p.add_argument("--dry-run", action="store_true", help="Inspect without committing changes")
    return p.parse_args()


def main():
    args = parse_args()
    tracker_id = args.tracker_id
    print(f"Connecting to database to reset QC for Tracker ID: {tracker_id}...")

    conn = connect(args)
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Inspect Tracker
        cursor.execute(
            "SELECT tracker_id, user_id, project_id, task_id, qc_status, tracker_file, date_time "
            "FROM task_work_tracker WHERE tracker_id = %s",
            (tracker_id,),
        )
        tracker = cursor.fetchone()

        if not tracker:
            print(f"[!] Warning: Tracker ID {tracker_id} not found in task_work_tracker.")
        else:
            print(f"[+] Found tracker {tracker_id}: user_id={tracker['user_id']}, project_id={tracker['project_id']}, "
                  f"task_id={tracker['task_id']}, qc_status={tracker['qc_status']}")

        # 2. Inspect QC Records
        cursor.execute(
            "SELECT id, tracker_id, qa_user_id, agent_id, qc_score, status, qc_status, created_at "
            "FROM qc_records WHERE tracker_id = %s",
            (tracker_id,),
        )
        qc_records = cursor.fetchall()
        print(f"[+] Found {len(qc_records)} QC record(s) for tracker {tracker_id}:")
        qc_ids = []
        for qr in qc_records:
            qc_ids.append(qr["id"])
            print(f"    - QC ID: {qr['id']}, QA User: {qr['qa_user_id']}, Status: {qr['status']}, Score: {qr['qc_score']}")

        if not qc_records and not tracker:
            print("[!] Nothing to delete or reset. Exiting.")
            return

        # 3. Check related child rows
        if qc_ids:
            format_strings = ",".join(["%s"] * len(qc_ids))
            
            cursor.execute(f"SELECT COUNT(*) AS count FROM qc_audit WHERE qc_record_id IN ({format_strings})", tuple(qc_ids))
            audit_count = cursor.fetchone()["count"]

            cursor.execute(f"SELECT COUNT(*) AS count FROM qc_rework_history WHERE qc_record_id IN ({format_strings})", tuple(qc_ids))
            rework_count = cursor.fetchone()["count"]

            cursor.execute(f"SELECT COUNT(*) AS count FROM qc_correction_history WHERE qc_record_id IN ({format_strings})", tuple(qc_ids))
            correction_count = cursor.fetchone()["count"]

            print(f"[+] Child rows found: qc_audit={audit_count}, qc_rework_history={rework_count}, qc_correction_history={correction_count}")

        if args.dry_run:
            print("\n[DRY RUN] No changes were made.")
            return

        # 4. Perform Deletion in Transaction
        conn.start_transaction()

        # Delete qc_audit
        cursor.execute(
            "DELETE qa FROM qc_audit qa "
            "INNER JOIN qc_records qr ON qa.qc_record_id = qr.id "
            "WHERE qr.tracker_id = %s",
            (tracker_id,),
        )
        del_audit = cursor.rowcount

        # Delete qc_rework_history
        cursor.execute(
            "DELETE rh FROM qc_rework_history rh "
            "INNER JOIN qc_records qr ON rh.qc_record_id = qr.id "
            "WHERE qr.tracker_id = %s",
            (tracker_id,),
        )
        del_rework = cursor.rowcount

        # Delete qc_correction_history
        cursor.execute(
            "DELETE ch FROM qc_correction_history ch "
            "INNER JOIN qc_records qr ON ch.qc_record_id = qr.id "
            "WHERE qr.tracker_id = %s",
            (tracker_id,),
        )
        del_corr = cursor.rowcount

        # Delete qc_records
        cursor.execute("DELETE FROM qc_records WHERE tracker_id = %s", (tracker_id,))
        del_qc = cursor.rowcount

        # Reopen tracker
        cursor.execute("UPDATE task_work_tracker SET qc_status = 0 WHERE tracker_id = %s", (tracker_id,))
        updated_tracker = cursor.rowcount

        conn.commit()

        print("\n=== SUCCESS ===")
        print(f"Deleted from qc_audit: {del_audit} row(s)")
        print(f"Deleted from qc_rework_history: {del_rework} row(s)")
        print(f"Deleted from qc_correction_history: {del_corr} row(s)")
        print(f"Deleted from qc_records: {del_qc} row(s)")
        print(f"Reset task_work_tracker (qc_status = 0): {updated_tracker} row(s)")
        print(f"Tracker {tracker_id} is now reset and pending QC re-evaluation.")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Transaction rolled back due to error: {e}", file=sys.stderr)
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()

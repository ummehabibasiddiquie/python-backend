"""Copy qc_score and error_list from an older database backup into records that lost them.

Import the backup as its own database first (for example tfs_hrms_backup on localhost).
Only records whose qc_score is still NULL in the target are touched, and only when the
backup has a score for that same qc_records id and tracker.

Usage (from backend-api, target = the DB_* settings in .env):
    # dry run
    python scripts/restore_qc_scores_from_backup.py --backup-database BACKUP_DB_NAME

    # write
    python scripts/restore_qc_scores_from_backup.py --backup-database BACKUP_DB_NAME --apply

If the backup database has its own MySQL user, add --backup-user and --backup-password.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime
from types import SimpleNamespace

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.hostinger_db import connect  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Restore wiped QC scores from a backup database")
    p.add_argument("--host", default=os.getenv("DB_HOST", "localhost"))
    p.add_argument("--port", type=int, default=int(os.getenv("DB_PORT", "3306")))
    p.add_argument("--user", default=os.getenv("DB_USERNAME", "root"))
    p.add_argument("--database", default=os.getenv("DB_DATABASE", "tfs_hrms"))
    p.add_argument("--password", default=None)
    p.add_argument("--backup-host", default=os.getenv("DB_HOST", "localhost"))
    p.add_argument("--backup-port", type=int, default=int(os.getenv("DB_PORT", "3306")))
    p.add_argument("--backup-user", default=os.getenv("DB_USERNAME", "root"))
    p.add_argument("--backup-database", required=True, help="Database the backup was imported into")
    p.add_argument("--backup-password", default=None)
    p.add_argument("--ids", default="", help="Comma-separated qc_records ids. Default: every record with qc_score NULL")
    p.add_argument("--apply", action="store_true", help="Write the restored values")
    args = p.parse_args()
    env_host = os.getenv("DB_HOST", "localhost")
    if args.password is None and args.host == env_host:
        args.password = os.getenv("DB_PASSWORD")
    if args.backup_password is None and args.backup_host == env_host and args.backup_user == os.getenv("DB_USERNAME", "root"):
        args.backup_password = os.getenv("DB_PASSWORD")
    return args


def main():
    args = parse_args()
    target = connect(args)
    backup = connect(
        SimpleNamespace(
            host=args.backup_host,
            port=args.backup_port,
            user=args.backup_user,
            database=args.backup_database,
            password=args.backup_password,
        )
    )
    tcur = target.cursor(dictionary=True)
    bcur = backup.cursor(dictionary=True)

    where = "qr.qc_score IS NULL"
    params: tuple = ()
    if args.ids.strip():
        ids = [int(x) for x in args.ids.split(",") if x.strip()]
        where = f"qr.id IN ({','.join(['%s'] * len(ids))}) AND qr.qc_score IS NULL"
        params = tuple(ids)

    tcur.execute(
        f"SELECT qr.id, qr.tracker_id, u.user_name AS agent_name FROM qc_records qr "
        f"LEFT JOIN tfs_user u ON u.user_id = qr.agent_id WHERE {where} ORDER BY qr.id",
        params,
    )
    wiped = tcur.fetchall()
    print(f"Records with an empty score: {len(wiped)}  ({'APPLY' if args.apply else 'DRY RUN'})\n")

    report = []
    updates = []
    for rec in wiped:
        bcur.execute(
            "SELECT id, tracker_id, qc_score, error_list, status, updated_at FROM qc_records WHERE id = %s",
            (rec["id"],),
        )
        old = bcur.fetchone()
        row = {
            "qc_record_id": rec["id"],
            "tracker_id": rec["tracker_id"],
            "agent": rec["agent_name"],
            "backup_score": "",
            "backup_errors": "",
            "backup_status": "",
            "backup_updated_at": "",
            "result": "",
        }
        if not old:
            row["result"] = "not in backup"
        elif old["tracker_id"] != rec["tracker_id"]:
            row["result"] = f"tracker differs in backup ({old['tracker_id']}) - skipped"
        elif old["qc_score"] is None:
            row["result"] = "score also empty in backup"
        else:
            error_list = old["error_list"]
            if isinstance(error_list, (bytes, bytearray)):
                error_list = error_list.decode("utf-8")
            row.update(
                {
                    "backup_score": old["qc_score"],
                    "backup_errors": error_list or "",
                    "backup_status": old["status"],
                    "backup_updated_at": old["updated_at"],
                    "result": "restore",
                }
            )
            updates.append((old["qc_score"], error_list, rec["id"]))
        report.append(row)
        print(f"QC {rec['id']} tracker {rec['tracker_id']} {rec['agent_name']}: {row['result']}"
              + (f" -> {row['backup_score']}%" if row["result"] == "restore" else ""))

    report_path = os.path.join(
        os.path.dirname(__file__), f"restore_qc_scores_{datetime.now():%Y%m%d_%H%M%S}.csv"
    )
    if report:
        with open(report_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(report[0].keys()))
            writer.writeheader()
            writer.writerows(report)
        print(f"\nReport: {report_path}")
    print(f"Can restore: {len(updates)}   Cannot: {len(report) - len(updates)}")

    if not args.apply:
        print("\n[DRY RUN] Nothing was saved. Run again with --apply to write these values.")
    elif updates:
        try:
            if target.in_transaction:
                target.rollback()
            target.start_transaction()
            for score, error_list, qc_id in updates:
                tcur.execute(
                    "UPDATE qc_records SET qc_score = %s, error_list = %s, updated_at = updated_at "
                    "WHERE id = %s AND qc_score IS NULL",
                    (score, error_list, qc_id),
                )
            target.commit()
            print(f"Saved {len(updates)} record(s).")
        except Exception:
            target.rollback()
            raise

    tcur.close()
    bcur.close()
    target.close()
    backup.close()


if __name__ == "__main__":
    main()

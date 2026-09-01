"""Read-only inspect: roster objects vs live HRMS data (no writes)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.dirname(__file__))

from hostinger_db import connect, parse_db_args  # noqa: E402


TABLES = [
    "tfs_user",
    "team",
    "org_holiday",
    "roster_month",
    "roster_day",
    "roster_leave",
    "roster_change_request",
    "roster_audit_log",
    "roster_version_snapshot",
    "roster_week_lock",
]


def _count(cursor, sql, params=()):
    cursor.execute(sql, params)
    row = cursor.fetchone() or {}
    if isinstance(row, dict):
        return int(next(iter(row.values())))
    return int(row[0]) if row else 0


def main() -> None:
    args = parse_db_args("Inspect roster schema (read-only).")
    conn = connect(args)
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT DATABASE() AS db")
        print("database:", (cursor.fetchone() or {}).get("db"))
        print("host:", args.host)

        print("\n--- table presence / approx rows ---")
        for table in TABLES:
            exists = _count(
                cursor,
                """
                SELECT COUNT(*) AS c FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                """,
                (table,),
            )
            if not exists:
                print(f"  {table}: MISSING")
                continue
            try:
                n = _count(cursor, f"SELECT COUNT(*) AS c FROM `{table}`")
            except Exception as e:
                n = f"error {e}"
            print(f"  {table}: OK rows={n}")

        print("\n--- tfs_user columns ---")
        for col in ("joining_date", "deactivated_at"):
            n = _count(
                cursor,
                """
                SELECT COUNT(*) AS c FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME='tfs_user' AND COLUMN_NAME=%s
                """,
                (col,),
            )
            print(f"  tfs_user.{col}: {'OK' if n else 'MISSING'}")

        if _count(
            cursor,
            """
            SELECT COUNT(*) AS c FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME='roster_week_lock'
            """,
        ):
            print("\n--- roster_week_lock columns ---")
            cursor.execute(
                """
                SELECT COLUMN_NAME FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME='roster_week_lock'
                ORDER BY ORDINAL_POSITION
                """
            )
            print(" ", [r["COLUMN_NAME"] for r in cursor.fetchall()])
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()

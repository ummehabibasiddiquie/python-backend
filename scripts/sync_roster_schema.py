"""Apply missing roster columns/tables used by the current APIs."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import get_db_connection  # noqa: E402


ROSTER_MONTH_COLUMNS = [
    ("roster_version", "INT NOT NULL DEFAULT 1"),
    ("submitted_by", "INT NULL"),
    ("submitted_date", "DATETIME NULL"),
    ("locked_by", "INT NULL"),
    ("locked_date", "DATETIME NULL"),
    ("production_synced_at", "DATETIME NULL"),
    ("last_approved_by", "INT NULL"),
    ("last_approved_date", "DATETIME NULL"),
]

CHANGE_REQUEST_COLUMNS = [
    ("batch_id", "VARCHAR(64) NULL"),
    ("reviewer_comment", "TEXT NULL"),
    ("applied_at", "DATETIME NULL"),
    ("roster_version_applied", "INT NULL"),
]

WEEK_LOCK_COLUMNS = [
    ("month_year", "VARCHAR(16) NULL"),
    ("week_number", "INT NOT NULL"),
    ("week_start", "DATE NOT NULL"),
    ("week_end", "DATE NOT NULL"),
    ("locked_by", "INT NULL"),
    ("locked_date", "DATETIME NULL"),
]


def column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) AS c
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (table, column),
    )
    row = cursor.fetchone() or {}
    return bool(row.get("c") if isinstance(row, dict) else (row[0] if row else 0))


def table_exists(cursor, table: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) AS c
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
        """,
        (table,),
    )
    row = cursor.fetchone() or {}
    return bool(row.get("c") if isinstance(row, dict) else (row[0] if row else 0))


def add_missing_columns(cursor, table: str, columns: list[tuple[str, str]]) -> list[str]:
    added = []
    for name, ddl in columns:
        if column_exists(cursor, table, name):
            print(f"skip {table}.{name} (exists)")
            continue
        cursor.execute(f"ALTER TABLE `{table}` ADD COLUMN `{name}` {ddl}")
        added.append(f"{table}.{name}")
        print(f"added {table}.{name}")
    return added


def migrate_week_lock_table(cursor) -> None:
    """Align roster_week_lock with current git code (month_year, not roster_month_id)."""
    if not table_exists(cursor, "roster_week_lock"):
        cursor.execute(
            """
            CREATE TABLE roster_week_lock (
              week_lock_id INT NOT NULL AUTO_INCREMENT,
              month_year VARCHAR(16) NOT NULL,
              week_number INT NOT NULL,
              week_start DATE NOT NULL,
              week_end DATE NOT NULL,
              locked_by INT NOT NULL,
              locked_date DATETIME NOT NULL,
              PRIMARY KEY (week_lock_id),
              UNIQUE KEY uq_roster_week_lock (month_year, week_number),
              KEY idx_roster_week_lock_month (month_year)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        print("created roster_week_lock")
        return

    add_missing_columns(cursor, "roster_week_lock", WEEK_LOCK_COLUMNS)

    if column_exists(cursor, "roster_week_lock", "roster_month_id"):
        cursor.execute(
            """
            UPDATE roster_week_lock wl
            JOIN roster_month rm ON rm.roster_month_id = wl.roster_month_id
            SET wl.month_year = rm.month_year
            WHERE wl.month_year IS NULL OR wl.month_year = ''
            """
        )
        print("backfilled roster_week_lock.month_year from roster_month")
        cursor.execute("ALTER TABLE roster_week_lock MODIFY roster_month_id INT NULL")
        print("made roster_week_lock.roster_month_id nullable")

    if column_exists(cursor, "roster_week_lock", "created_date"):
        cursor.execute(
            """
            ALTER TABLE roster_week_lock
              MODIFY created_date DATETIME NULL DEFAULT CURRENT_TIMESTAMP
            """
        )
    if column_exists(cursor, "roster_week_lock", "updated_date"):
        cursor.execute(
            """
            ALTER TABLE roster_week_lock
              MODIFY updated_date DATETIME NULL DEFAULT CURRENT_TIMESTAMP
            """
        )

    cursor.execute(
        """
        SELECT COUNT(*) AS c
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'roster_week_lock'
          AND INDEX_NAME = 'idx_roster_week_lock_month'
        """
    )
    row = cursor.fetchone() or {}
    has_idx = bool(row.get("c") if isinstance(row, dict) else (row[0] if row else 0))
    if not has_idx and column_exists(cursor, "roster_week_lock", "month_year"):
        cursor.execute(
            "ALTER TABLE roster_week_lock ADD KEY idx_roster_week_lock_month (month_year)"
        )
        print("added idx_roster_week_lock_month")


def main() -> None:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        db_name = os.getenv("DB_DATABASE", "")
        print(f"syncing roster schema on {db_name or 'connected database'}")

        if not table_exists(cursor, "roster_month"):
            print("roster_month not found. Import the old backup into tfs_hrms first, then run this script again.")
            return

        added = []
        added.extend(add_missing_columns(cursor, "roster_month", ROSTER_MONTH_COLUMNS))

        if table_exists(cursor, "roster_change_request"):
            added.extend(
                add_missing_columns(cursor, "roster_change_request", CHANGE_REQUEST_COLUMNS)
            )
        else:
            print("skip roster_change_request (table missing)")

        migrate_week_lock_table(cursor)

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS roster_version_snapshot (
              version_id INT NOT NULL AUTO_INCREMENT,
              roster_month_id INT NOT NULL,
              roster_version INT NOT NULL,
              snapshot_json JSON NOT NULL,
              approved_by INT NOT NULL,
              approved_date DATETIME NOT NULL,
              reviewer_comment TEXT,
              production_synced_at DATETIME NULL,
              created_date DATETIME NOT NULL,
              PRIMARY KEY (version_id),
              UNIQUE KEY uk_roster_month_version (roster_month_id, roster_version)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        print("ensured roster_version_snapshot")

        conn.commit()
        print("done. added:", ", ".join(added) if added else "nothing new")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()

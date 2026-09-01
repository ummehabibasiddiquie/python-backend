"""Idempotent additive roster schema for live HRMS. Never DROP/TRUNCATE data tables."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.dirname(__file__))

from hostinger_db import connect, parse_db_args  # noqa: E402


TFS_USER_COLUMNS = [
    ("joining_date", "DATE NULL"),
    ("deactivated_at", "DATETIME NULL"),
]

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

CREATE_TABLES_SQL = [
    (
        "org_holiday",
        """
        CREATE TABLE IF NOT EXISTS org_holiday (
          holiday_id INT NOT NULL AUTO_INCREMENT,
          holiday_date DATE NOT NULL,
          holiday_name VARCHAR(255) NOT NULL,
          calendar_year INT NOT NULL,
          is_active TINYINT NOT NULL DEFAULT 1,
          created_by INT DEFAULT NULL,
          created_date DATETIME NOT NULL,
          updated_date DATETIME NOT NULL,
          PRIMARY KEY (holiday_id),
          UNIQUE KEY uk_org_holiday_date_year (holiday_date, calendar_year),
          KEY idx_org_holiday_year_active (calendar_year, is_active)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    ),
    (
        "roster_month",
        """
        CREATE TABLE IF NOT EXISTS roster_month (
          roster_month_id INT NOT NULL AUTO_INCREMENT,
          user_id INT NOT NULL,
          month_year VARCHAR(20) NOT NULL,
          status ENUM('Draft','Pending Approval','Approved','Locked') NOT NULL DEFAULT 'Draft',
          roster_version INT NOT NULL DEFAULT 1,
          roster_start_date DATE NOT NULL,
          roster_end_date DATE NOT NULL,
          baseline_target_days DECIMAL(10,2) NOT NULL DEFAULT 0,
          calendar_working_days DECIMAL(10,2) NOT NULL DEFAULT 0,
          target_working_days DECIMAL(10,2) NOT NULL DEFAULT 0,
          monthly_target_hours DECIMAL(10,2) NOT NULL DEFAULT 0,
          extra_assigned_hours DECIMAL(10,2) NOT NULL DEFAULT 0,
          is_active TINYINT NOT NULL DEFAULT 1,
          created_by INT DEFAULT NULL,
          created_date DATETIME NOT NULL,
          approved_by INT DEFAULT NULL,
          approved_date DATETIME DEFAULT NULL,
          submitted_by INT NULL,
          submitted_date DATETIME NULL,
          locked_by INT NULL,
          locked_date DATETIME NULL,
          production_synced_at DATETIME NULL,
          last_approved_by INT NULL,
          last_approved_date DATETIME NULL,
          updated_date DATETIME NOT NULL,
          PRIMARY KEY (roster_month_id),
          KEY idx_roster_month_user (user_id, month_year, is_active),
          KEY idx_roster_month_status (month_year, status, is_active)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    ),
    (
        "roster_day",
        """
        CREATE TABLE IF NOT EXISTS roster_day (
          roster_day_id INT NOT NULL AUTO_INCREMENT,
          roster_month_id INT NOT NULL,
          roster_date DATE NOT NULL,
          day_type ENUM('Working','WeekOff','Holiday','Leave','PreJoin') NOT NULL DEFAULT 'Working',
          shift ENUM('DAY','NIGHT') NOT NULL DEFAULT 'DAY',
          shift_start TIME DEFAULT NULL,
          shift_end TIME DEFAULT NULL,
          working_type ENUM('Full','Half') NOT NULL DEFAULT 'Full',
          working_hours DECIMAL(4,2) NOT NULL DEFAULT 9.00,
          holiday_id INT DEFAULT NULL,
          leave_id INT DEFAULT NULL,
          is_active TINYINT NOT NULL DEFAULT 1,
          created_date DATETIME NOT NULL,
          updated_date DATETIME NOT NULL,
          PRIMARY KEY (roster_day_id),
          UNIQUE KEY uk_roster_day_month_date (roster_month_id, roster_date),
          KEY idx_roster_day_date (roster_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    ),
    (
        "roster_leave",
        """
        CREATE TABLE IF NOT EXISTS roster_leave (
          leave_id INT NOT NULL AUTO_INCREMENT,
          roster_month_id INT NOT NULL,
          leave_type VARCHAR(100) NOT NULL,
          start_date DATE NOT NULL,
          end_date DATE NOT NULL,
          reason TEXT,
          is_rostered TINYINT NOT NULL DEFAULT 1,
          affect_target TINYINT NOT NULL DEFAULT 0,
          is_half_day TINYINT NOT NULL DEFAULT 0,
          is_active TINYINT NOT NULL DEFAULT 1,
          created_by INT DEFAULT NULL,
          created_date DATETIME NOT NULL,
          updated_date DATETIME NOT NULL,
          PRIMARY KEY (leave_id),
          KEY idx_roster_leave_month (roster_month_id, is_active)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    ),
    (
        "roster_change_request",
        """
        CREATE TABLE IF NOT EXISTS roster_change_request (
          request_id INT NOT NULL AUTO_INCREMENT,
          roster_month_id INT NOT NULL,
          user_id INT NOT NULL,
          change_type VARCHAR(50) NOT NULL,
          change_payload JSON NOT NULL,
          batch_id VARCHAR(64) NULL,
          status ENUM(
            'Pending','Approved','Rejected',
            'Cancelled due to Regeneration',
            'Cancelled due to Withdrawal'
          ) NOT NULL DEFAULT 'Pending',
          submitted_by INT NOT NULL,
          submitted_date DATETIME NOT NULL,
          reviewed_by INT DEFAULT NULL,
          reviewed_date DATETIME DEFAULT NULL,
          rejection_reason TEXT,
          reviewer_comment TEXT NULL,
          applied_at DATETIME NULL,
          roster_version_applied INT NULL,
          is_active TINYINT NOT NULL DEFAULT 1,
          PRIMARY KEY (request_id),
          KEY idx_roster_change_month_status (roster_month_id, status),
          KEY idx_roster_change_batch (batch_id, status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    ),
    (
        "roster_audit_log",
        """
        CREATE TABLE IF NOT EXISTS roster_audit_log (
          audit_id INT NOT NULL AUTO_INCREMENT,
          roster_month_id INT DEFAULT NULL,
          user_id INT DEFAULT NULL,
          action VARCHAR(100) NOT NULL,
          entity_type VARCHAR(50) NOT NULL,
          entity_id INT DEFAULT NULL,
          old_value JSON DEFAULT NULL,
          new_value JSON DEFAULT NULL,
          performed_by INT NOT NULL,
          performed_date DATETIME NOT NULL,
          approval_status VARCHAR(50) DEFAULT NULL,
          notes TEXT,
          PRIMARY KEY (audit_id),
          KEY idx_roster_audit_month (roster_month_id),
          KEY idx_roster_audit_user (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    ),
    (
        "roster_version_snapshot",
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
        """,
    ),
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


def index_exists(cursor, table: str, index_name: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) AS c
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND INDEX_NAME = %s
        """,
        (table, index_name),
    )
    row = cursor.fetchone() or {}
    return bool(row.get("c") if isinstance(row, dict) else (row[0] if row else 0))


def add_missing_columns(cursor, table: str, columns: list[tuple[str, str]]) -> list[str]:
    added = []
    if not table_exists(cursor, table):
        print(f"skip columns for missing table {table}")
        return added
    for name, ddl in columns:
        if column_exists(cursor, table, name):
            print(f"skip {table}.{name} (exists)")
            continue
        cursor.execute(f"ALTER TABLE `{table}` ADD COLUMN `{name}` {ddl}")
        added.append(f"{table}.{name}")
        print(f"added {table}.{name}")
    return added


def ensure_change_request_status_enum(cursor) -> None:
    if not table_exists(cursor, "roster_change_request"):
        return
    cursor.execute(
        """
        ALTER TABLE roster_change_request
          MODIFY COLUMN status ENUM(
            'Pending','Approved','Rejected',
            'Cancelled due to Regeneration',
            'Cancelled due to Withdrawal'
          ) NOT NULL DEFAULT 'Pending'
        """
    )
    print("ensured roster_change_request.status enum")


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
        if table_exists(cursor, "roster_month"):
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

    if not index_exists(cursor, "roster_week_lock", "idx_roster_week_lock_month"):
        if column_exists(cursor, "roster_week_lock", "month_year"):
            cursor.execute(
                "ALTER TABLE roster_week_lock ADD KEY idx_roster_week_lock_month (month_year)"
            )
            print("added idx_roster_week_lock_month")


def table_row_count(cursor, table: str) -> int | None:
    if not table_exists(cursor, table):
        return None
    cursor.execute(f"SELECT COUNT(*) AS c FROM `{table}`")
    row = cursor.fetchone() or {}
    return int(row.get("c") if isinstance(row, dict) else row[0])


def main() -> None:
    args = parse_db_args("Apply additive roster schema (Hostinger-safe, no DROP).")
    conn = connect(args)
    cursor = conn.cursor(dictionary=True)
    try:
        print(f"syncing roster schema on {args.database} (additive only)")

        if not table_exists(cursor, "tfs_user"):
            print("tfs_user not found. This is not an HRMS database. Aborting (no writes).")
            return

        user_before = table_row_count(cursor, "tfs_user")
        print(f"tfs_user rows before: {user_before}")

        added = []
        added.extend(add_missing_columns(cursor, "tfs_user", TFS_USER_COLUMNS))

        for name, ddl in CREATE_TABLES_SQL:
            existed = table_exists(cursor, name)
            cursor.execute(ddl)
            print(f"{'skip' if existed else 'created'} {name}")

        if table_exists(cursor, "roster_month"):
            added.extend(add_missing_columns(cursor, "roster_month", ROSTER_MONTH_COLUMNS))

        if table_exists(cursor, "roster_change_request"):
            added.extend(
                add_missing_columns(cursor, "roster_change_request", CHANGE_REQUEST_COLUMNS)
            )
            ensure_change_request_status_enum(cursor)
            if not index_exists(cursor, "roster_change_request", "idx_roster_change_batch"):
                if column_exists(cursor, "roster_change_request", "batch_id"):
                    cursor.execute(
                        "ALTER TABLE roster_change_request ADD KEY idx_roster_change_batch (batch_id, status)"
                    )
                    print("added idx_roster_change_batch")

        migrate_week_lock_table(cursor)

        conn.commit()
        user_after = table_row_count(cursor, "tfs_user")
        print(f"tfs_user rows after: {user_after}")
        if user_before != user_after:
            print("WARNING: tfs_user row count changed; investigate before hosting")
        print("done. added columns:", ", ".join(added) if added else "nothing new")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()

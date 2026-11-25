#!/bin/bash
# Copy useful LIVE data mytfs -> mytfs_test every 2 minutes.
# Never writes mytfs. Abort if TARGET is not mytfs_test.
#
# Crontab (Hostinger, where mysql client can see both DBs):
#   */5 * * * * /path/to/sync_mytfs_live_to_test.sh >> /var/log/mytfs_sync.log 2>&1
#
# --replace: test rows for these tables match live (same ids overwritten).
# Clock / task SOP tables are NOT copied: they exist on test from Flask,
# not on live yet. Test clock-in/SOP drafts stay; tracker/QC rows follow live.

set -euo pipefail

MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASS="${MYSQL_PASS:-}"
SOURCE_DB="mytfs"
TARGET_DB="mytfs_test"

if [ "$TARGET_DB" != "mytfs_test" ]; then
  echo "Refusing to run: TARGET_DB must be mytfs_test (got $TARGET_DB)"
  exit 1
fi
if [ "$SOURCE_DB" = "$TARGET_DB" ]; then
  echo "Refusing to run: source and target are the same"
  exit 1
fi

export MYSQL_PWD="$MYSQL_PASS"
MYSQL=(mysql -u"$MYSQL_USER" -N -s)
DUMP=(mysqldump -u"$MYSQL_USER" --single-transaction --skip-triggers --no-create-info --replace)

table_exists() {
  local db="$1" table="$2"
  local n
  n="$("${MYSQL[@]}" -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${db}' AND table_name='${table}'")"
  [ "${n:-0}" -ge 1 ]
}

# People / work / QC / roster that the UI reads. Skip missing tables so
# crontab does not die if live is one migration behind.
TABLES=(
  tfs_user
  user_role
  team
  project
  project_category
  task
  user_permission
  task_work_tracker
  qc_afd
  qc_audit
  qc_correction_history
  qc_records
  qc_rework_history
  qa_work_tracker
  temp_qc
  org_holiday
  roster_month
  roster_day
  roster_leave
  roster_change_request
  roster_week_lock
  kra_day_note
  kra_month_input
  report_email_recipient
)

ok=0
skip=0
for table in "${TABLES[@]}"; do
  if ! table_exists "$SOURCE_DB" "$table"; then
    echo "skip (not on live): $table"
    skip=$((skip + 1))
    continue
  fi
  if ! table_exists "$TARGET_DB" "$table"; then
    echo "skip (not on test — create schema first): $table"
    skip=$((skip + 1))
    continue
  fi
  "${DUMP[@]}" "$SOURCE_DB" "$table" | mysql -u"$MYSQL_USER" "$TARGET_DB"
  echo "synced $table"
  ok=$((ok + 1))
done

echo "$(date -Is) done synced=$ok skipped=$skip -> $TARGET_DB"
unset MYSQL_PWD

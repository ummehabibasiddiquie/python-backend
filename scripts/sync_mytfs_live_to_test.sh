#!/bin/bash
# Live mytfs -> test mytfs_test only. Never writes mytfs.
# crontab: */5 * * * * /root/db-sync/sync.sh >> /root/db-sync/sync.log 2>&1
#
# --complete-insert: test has extra clock columns on task_work_tracker;
# named INSERTs keep those columns. tfs_user is omitted so test
# deactivations are not overwritten from live.

MYSQL_USER="root"
MYSQL_PASS='YOUR_PASSWORD'

SOURCE_DB="mytfs"
TARGET_DB="mytfs_test"

if [ "$TARGET_DB" != "mytfs_test" ]; then
  echo "Refusing: TARGET_DB must be mytfs_test"
  exit 1
fi

TABLES="
task_work_tracker \
user_monthly_tracker \
project_monthly_tracker \
qc_audit \
qc_correction_history \
qc_records \
qc_rework_history \
qa_work_tracker \
temp_qc \
roster_month \
roster_day \
roster_leave \
roster_change_request \
roster_week_lock \
kra_day_note \
kra_month_input \
report_email_recipient \
sop_topic \
sop_item"

mysqldump \
  -u"$MYSQL_USER" \
  -p"$MYSQL_PASS" \
  --single-transaction \
  --no-create-info \
  --complete-insert \
  --skip-triggers \
  --replace \
  "$SOURCE_DB" \
  $TABLES | mysql -u"$MYSQL_USER" -p"$MYSQL_PASS" "$TARGET_DB"

echo "$(date) synced live -> mytfs_test"

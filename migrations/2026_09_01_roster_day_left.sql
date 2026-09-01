-- Additive: allow roster_day.day_type = Left (agent left the organisation).
-- Does not drop data. Prefer: python scripts/sync_roster_schema.py

ALTER TABLE roster_day
  MODIFY COLUMN day_type ENUM(
    'Working','WeekOff','Holiday','Leave','PreJoin','Left'
  ) NOT NULL DEFAULT 'Working';

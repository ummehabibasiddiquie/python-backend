-- Add minutes-per-record QA target mode
ALTER TABLE task ADD COLUMN qa_minutes_per_record DECIMAL(10,2) NULL AFTER qa_minutes_per_file;

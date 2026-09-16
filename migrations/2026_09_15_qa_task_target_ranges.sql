-- QA object-range / per-file minute targets
ALTER TABLE task ADD COLUMN qa_count_column VARCHAR(255) NULL AFTER qc_percentage;
ALTER TABLE task ADD COLUMN qa_target_ranges JSON NULL AFTER qa_count_column;
ALTER TABLE task ADD COLUMN qa_minutes_per_file DECIMAL(10,2) NULL AFTER qa_target_ranges;
ALTER TABLE qc_records ADD COLUMN object_count DECIMAL(14,2) NULL AFTER qc_generated_count;

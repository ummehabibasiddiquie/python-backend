-- Restore the 21 QC scores wiped by the old correction save, using the 8 Oct 2026 backup
-- (/root/mytfs_backup_08102026.sql). Only fills rows whose score is still empty.

-- 1. Check: should list 21 records with qc_score NULL
SELECT id, tracker_id, qc_score FROM qc_records WHERE id IN (6339, 6340, 6341, 6342, 6343, 6346, 6347, 6560, 6597, 6604, 6627, 6631, 6635, 6670, 6676, 6704, 6705, 6718, 6724, 6752, 6754);

-- 2. Restore
START TRANSACTION;

-- QC 6339 tracker 45164: 98.5%
UPDATE qc_records SET qc_score = 98.5, error_list = '[{"row":1,"category":"Adherence & Data Accuracy","subcategory":"Missing or complete Data","error":"Adherence & Data Accuracy - Missing or complete Data","points":30}]', updated_at = updated_at WHERE id = 6339 AND tracker_id = 45164 AND qc_score IS NULL;

-- QC 6340 tracker 45278: 98.75%
UPDATE qc_records SET qc_score = 98.75, error_list = '[{"row":1,"category":"Formatting","subcategory":"Change Case/Proper Case","error":"Formatting - Change Case/Proper Case","points":15},{"row":3,"category":"Adherence & Data Accuracy","subcategory":"Missing or complete Data","error":"Adherence & Data Accuracy - Missing or complete Data","points":30},{"row":5,"category":"Adherence & Data Accuracy","subcategory":"Missing or complete Data","error":"Adherence & Data Accuracy - Missing or complete Data","points":30}]', updated_at = updated_at WHERE id = 6340 AND tracker_id = 45278 AND qc_score IS NULL;

-- QC 6341 tracker 45318: 98.75%
UPDATE qc_records SET qc_score = 98.75, error_list = '[{"row":2,"category":"Formatting","subcategory":"Change Case/Proper Case","error":"Formatting - Change Case/Proper Case","points":15}]', updated_at = updated_at WHERE id = 6341 AND tracker_id = 45318 AND qc_score IS NULL;

-- QC 6342 tracker 45440: 98.5%
UPDATE qc_records SET qc_score = 98.5, error_list = '[{"row":2,"category":"Adherence & Data Accuracy","subcategory":"Missing or complete Data","error":"Adherence & Data Accuracy - Missing or complete Data","points":30},{"row":4,"category":"Adherence & Data Accuracy","subcategory":"Missing or complete Data","error":"Adherence & Data Accuracy - Missing or complete Data","points":30}]', updated_at = updated_at WHERE id = 6342 AND tracker_id = 45440 AND qc_score IS NULL;

-- QC 6343 tracker 45568: 98.13%
UPDATE qc_records SET qc_score = 98.13, error_list = '[{"row":1,"category":"Adherence & Data Accuracy","subcategory":"Missing or complete Data","error":"Adherence & Data Accuracy - Missing or complete Data","points":30},{"row":4,"category":"Adherence & Data Accuracy","subcategory":"Missing or complete Data","error":"Adherence & Data Accuracy - Missing or complete Data","points":30},{"row":5,"category":"Formatting","subcategory":"Change Case/Proper Case","error":"Formatting - Change Case/Proper Case","points":15},{"row":9,"category":"Formatting","subcategory":"Change Case/Proper Case","error":"Formatting - Change Case/Proper Case","points":15}]', updated_at = updated_at WHERE id = 6343 AND tracker_id = 45568 AND qc_score IS NULL;

-- QC 6346 tracker 45855: 98.13%
UPDATE qc_records SET qc_score = 98.13, error_list = '[{"row":1,"category":"Adherence & Data Accuracy","subcategory":"Missing or complete Data","error":"Adherence & Data Accuracy - Missing or complete Data","points":30},{"row":3,"category":"Formatting","subcategory":"Change Case/Proper Case","error":"Formatting - Change Case/Proper Case","points":15},{"row":5,"category":"Formatting","subcategory":"Change Case/Proper Case","error":"Formatting - Change Case/Proper Case","points":15}]', updated_at = updated_at WHERE id = 6346 AND tracker_id = 45855 AND qc_score IS NULL;

-- QC 6347 tracker 46177: 98.13%
UPDATE qc_records SET qc_score = 98.13, error_list = '[{"row":1,"category":"Formatting","subcategory":"Change Case/Proper Case","error":"Formatting - Change Case/Proper Case","points":15},{"row":3,"category":"Adherence & Data Accuracy","subcategory":"Missing or complete Data","error":"Adherence & Data Accuracy - Missing or complete Data","points":30},{"row":6,"category":"Formatting","subcategory":"Change Case/Proper Case","error":"Formatting - Change Case/Proper Case","points":15}]', updated_at = updated_at WHERE id = 6347 AND tracker_id = 46177 AND qc_score IS NULL;

-- QC 6560 tracker 45363: 98.59%
UPDATE qc_records SET qc_score = 98.59, error_list = '[{"row":1,"category":"Adherence & Data Accuracy","subcategory":"Missing or complete Data","error":"Adherence & Data Accuracy - Missing or complete Data","points":30},{"row":3,"category":"Formatting","subcategory":"Change Case/Proper Case","error":"Formatting - Change Case/Proper Case","points":15}]', updated_at = updated_at WHERE id = 6560 AND tracker_id = 45363 AND qc_score IS NULL;

-- QC 6597 tracker 45745: 98.5%
UPDATE qc_records SET qc_score = 98.5, error_list = '[{"row":5,"category":"Adherence & Data Accuracy","subcategory":"Missing or complete Data","error":"Adherence & Data Accuracy - Missing or complete Data","points":30},{"row":8,"category":"Adherence & Data Accuracy","subcategory":"Missing or complete Data","error":"Adherence & Data Accuracy - Missing or complete Data","points":30}]', updated_at = updated_at WHERE id = 6597 AND tracker_id = 45745 AND qc_score IS NULL;

-- QC 6604 tracker 43033: 98.5%
UPDATE qc_records SET qc_score = 98.5, error_list = '[{"row":1,"category":"Data Accuracy","subcategory":"Missing object","error":"Data Accuracy - Missing object","points":2},{"row":2,"category":"Data Accuracy","subcategory":"Missing Category/Material","error":"Data Accuracy - Missing Category/Material","points":2},{"row":4,"category":"Data Accuracy","subcategory":"Incorrect Object Boundry","error":"Data Accuracy - Incorrect Object Boundry","points":2}]', updated_at = updated_at WHERE id = 6604 AND tracker_id = 43033 AND qc_score IS NULL;

-- QC 6627 tracker 44826: 98.0%
UPDATE qc_records SET qc_score = 98.0, error_list = '[{"row":1,"category":"Data Accuracy","subcategory":"Missing object","error":"Data Accuracy - Missing object","points":2}]', updated_at = updated_at WHERE id = 6627 AND tracker_id = 44826 AND qc_score IS NULL;

-- QC 6631 tracker 45637: 98.5%
UPDATE qc_records SET qc_score = 98.5, error_list = '[{"row":2,"category":"Formatting","subcategory":"Change Case/Proper Case","error":"Formatting - Change Case/Proper Case","points":15},{"row":5,"category":"Formatting","subcategory":"Change Case/Proper Case","error":"Formatting - Change Case/Proper Case","points":15},{"row":10,"category":"Adherence & Data Accuracy","subcategory":"Missing or complete Data","error":"Adherence & Data Accuracy - Missing or complete Data","points":30}]', updated_at = updated_at WHERE id = 6631 AND tracker_id = 45637 AND qc_score IS NULL;

-- QC 6635 tracker 46194: 98.75%
UPDATE qc_records SET qc_score = 98.75, error_list = '[{"row":4,"category":"Adherence & Data Accuracy","subcategory":"Missing or complete Data","error":"Adherence & Data Accuracy - Missing or complete Data","points":30}]', updated_at = updated_at WHERE id = 6635 AND tracker_id = 46194 AND qc_score IS NULL;

-- QC 6670 tracker 42257: 98.0%
UPDATE qc_records SET qc_score = 98.0, error_list = '[{"row":1,"category":"Data Accuracy","subcategory":"Missing object","error":"Data Accuracy - Missing object","points":2},{"row":2,"category":"Data Accuracy","subcategory":"Missing object","error":"Data Accuracy - Missing object","points":2},{"row":3,"category":"Data Accuracy","subcategory":"Missing object","error":"Data Accuracy - Missing object","points":2}]', updated_at = updated_at WHERE id = 6670 AND tracker_id = 42257 AND qc_score IS NULL;

-- QC 6676 tracker 43485: 98.0%
UPDATE qc_records SET qc_score = 98.0, error_list = '[{"row":1,"category":"Data Accuracy","subcategory":"Missing object","error":"Data Accuracy - Missing object","points":2},{"row":2,"category":"Data Accuracy","subcategory":"Missing Category/Material","error":"Data Accuracy - Missing Category/Material","points":2},{"row":3,"category":"Data Accuracy","subcategory":"Missing Category/Material","error":"Data Accuracy - Missing Category/Material","points":2},{"row":4,"category":"Data Accuracy","subcategory":"Missing Category/Material","error":"Data Accuracy - Missing Category/Material","points":2}]', updated_at = updated_at WHERE id = 6676 AND tracker_id = 43485 AND qc_score IS NULL;

-- QC 6704 tracker 45161: 98.93%
UPDATE qc_records SET qc_score = 98.93, error_list = '[{"row":3,"category":"Formatting","subcategory":"Change Case/Proper Case","error":"Formatting - Change Case/Proper Case","points":15},{"row":6,"category":"Formatting","subcategory":"Change Case/Proper Case","error":"Formatting - Change Case/Proper Case","points":15}]', updated_at = updated_at WHERE id = 6704 AND tracker_id = 45161 AND qc_score IS NULL;

-- QC 6705 tracker 45274: 98.39%
UPDATE qc_records SET qc_score = 98.39, error_list = '[{"row":1,"category":"Adherence & Data Accuracy","subcategory":"Missing or complete Data","error":"Adherence & Data Accuracy - Missing or complete Data","points":30},{"row":4,"category":"Formatting","subcategory":"Change Case/Proper Case","error":"Formatting - Change Case/Proper Case","points":15}]', updated_at = updated_at WHERE id = 6705 AND tracker_id = 45274 AND qc_score IS NULL;

-- QC 6718 tracker 45445: 98.5%
UPDATE qc_records SET qc_score = 98.5, error_list = '[{"row":2,"category":"Formatting","subcategory":"Change Case/Proper Case","error":"Formatting - Change Case/Proper Case","points":15},{"row":5,"category":"Formatting","subcategory":"Change Case/Proper Case","error":"Formatting - Change Case/Proper Case","points":15}]', updated_at = updated_at WHERE id = 6718 AND tracker_id = 45445 AND qc_score IS NULL;

-- QC 6724 tracker 45576: 98.59%
UPDATE qc_records SET qc_score = 98.59, error_list = '[{"row":1,"category":"Adherence & Data Accuracy","subcategory":"Missing or complete Data","error":"Adherence & Data Accuracy - Missing or complete Data","points":30},{"row":8,"category":"Formatting","subcategory":"Change Case/Proper Case","error":"Formatting - Change Case/Proper Case","points":15}]', updated_at = updated_at WHERE id = 6724 AND tracker_id = 45576 AND qc_score IS NULL;

-- QC 6752 tracker 46181: 98.94%
UPDATE qc_records SET qc_score = 98.94, error_list = '[{"row":3,"category":"Adherence & Data Accuracy","subcategory":"Missing or complete Data","error":"Adherence & Data Accuracy - Missing or complete Data","points":30},{"row":6,"category":"Formatting","subcategory":"Change Case/Proper Case","error":"Formatting - Change Case/Proper Case","points":15},{"row":6,"category":"Formatting","subcategory":"Spacing/Extra Spacing","error":"Formatting - Spacing/Extra Spacing","points":10}]', updated_at = updated_at WHERE id = 6752 AND tracker_id = 46181 AND qc_score IS NULL;

-- QC 6754 tracker 46494: 98.0%
UPDATE qc_records SET qc_score = 98.0, error_list = '[{"row":1,"category":"Data Accuracy","subcategory":"Incorrect Category/Sub category/Material","error":"Data Accuracy - Incorrect Category/Sub category/Material","points":2}]', updated_at = updated_at WHERE id = 6754 AND tracker_id = 46494 AND qc_score IS NULL;

COMMIT;

-- 3. Verify: every row should now have a score
SELECT id, tracker_id, qc_score FROM qc_records WHERE id IN (6339, 6340, 6341, 6342, 6343, 6346, 6347, 6560, 6597, 6604, 6627, 6631, 6635, 6670, 6676, 6704, 6705, 6718, 6724, 6752, 6754);

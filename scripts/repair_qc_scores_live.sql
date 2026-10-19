-- Restore QC scores wiped by the correction save bug (before qc-backend 4e88694, 12 Oct 2026).
-- Rebuilt from each record's saved QC sample file. Only touches rows whose score is still empty.
-- Run on the LIVE database. Check step 1 first.

-- 1. Check: should list these 19 records with qc_score NULL
SELECT id, tracker_id, qc_score, error_list FROM qc_records
WHERE id IN (6787, 6788, 6794, 6825, 6826, 6829, 6844, 6869, 6878, 6879, 6881, 6891, 6898, 6910, 6911, 6921, 6923, 6938, 6966);

-- 2. Restore
START TRANSACTION;

-- QC 6787 tracker 46707 Tanvi Sudani: 98.0%
UPDATE qc_records SET qc_score = 98.0, error_list = '[{"row": 2, "qc_code": "10/06/2026/DSPG/TS/2", "category": "Data Accuracy", "subcategory": "Missing object", "error": "Data Accuracy - Missing object", "points": 2}]', updated_at = updated_at WHERE id = 6787 AND tracker_id = 46707 AND qc_score IS NULL;

-- QC 6788 tracker 46786 Tanvi Sudani: 98.0%
UPDATE qc_records SET qc_score = 98.0, error_list = '[{"row": 2, "qc_code": "10/06/2026/DSPG/TS/3", "category": "Data Accuracy", "subcategory": "Missing object", "error": "Data Accuracy - Missing object", "points": 2}]', updated_at = updated_at WHERE id = 6788 AND tracker_id = 46786 AND qc_score IS NULL;

-- QC 6794 tracker 46455 Shivkumar Prajapati: 98.0%
UPDATE qc_records SET qc_score = 98.0, error_list = '[{"row": 2, "qc_code": "10/5/2026/Supervisely/SP/01", "category": "Data Accuracy", "subcategory": "Missing object", "error": "Data Accuracy - Missing object", "points": 2}, {"row": 3, "qc_code": "10/5/2026/Supervisely/SP/02", "category": "Data Accuracy", "subcategory": "Missing object", "error": "Data Accuracy - Missing object", "points": 2}]', updated_at = updated_at WHERE id = 6794 AND tracker_id = 46455 AND qc_score IS NULL;

-- QC 6825 tracker 46808 Shivkumar Prajapati: 98.0%
UPDATE qc_records SET qc_score = 98.0, error_list = '[{"row": 2, "qc_code": "10/6/2026/Supervisely/SP/05", "category": "Data Accuracy", "subcategory": "Missing object", "error": "Data Accuracy - Missing object", "points": 2}, {"row": 3, "qc_code": "10/6/2026/Supervisely/SP/06", "category": "Data Accuracy", "subcategory": "Missing object", "error": "Data Accuracy - Missing object", "points": 2}, {"row": 4, "qc_code": "10/6/2026/Supervisely/SP/07", "category": "Data Accuracy", "subcategory": "Incorrect Object Boundry", "error": "Data Accuracy - Incorrect Object Boundry", "points": 2}]', updated_at = updated_at WHERE id = 6825 AND tracker_id = 46808 AND qc_score IS NULL;

-- QC 6826 tracker 46801 Shivkumar Prajapati: 99.0%
UPDATE qc_records SET qc_score = 99.0, error_list = '[{"row": 2, "qc_code": "10/6/2026/Supervisely/SP/03", "category": "Data Accuracy", "subcategory": "Missing object", "error": "Data Accuracy - Missing object", "points": 2}]', updated_at = updated_at WHERE id = 6826 AND tracker_id = 46801 AND qc_score IS NULL;

-- QC 6829 tracker 47013 Hetvi Tarsariya: 98.0%
UPDATE qc_records SET qc_score = 98.0, error_list = '[{"row": 2, "qc_code": "10/07/2026/Driveway_Sidewalk_Parking Lot_Ground Surface/HT/02", "category": "Data Accuracy", "subcategory": "Incorrect Object Boundry", "error": "Data Accuracy - Incorrect Object Boundry", "points": 2}, {"row": 3, "qc_code": "10/07/2026/Driveway_Sidewalk_Parking Lot_Ground Surface/HT/03", "category": "Data Accuracy", "subcategory": "Missing object", "error": "Data Accuracy - Missing object", "points": 2}]', updated_at = updated_at WHERE id = 6829 AND tracker_id = 47013 AND qc_score IS NULL;

-- QC 6844 tracker 47112 Archana Kota: 98.0%
UPDATE qc_records SET qc_score = 98.0, error_list = '[{"row": 2, "qc_code": "10/7/2026/IMG_Anotation/AK/2", "category": "Data Accuracy", "subcategory": "Missing object", "error": "Data Accuracy - Missing object", "points": 2}]', updated_at = updated_at WHERE id = 6844 AND tracker_id = 47112 AND qc_score IS NULL;

-- QC 6869 tracker 46871 Tanvi Tarsariya: 98.0%
UPDATE qc_records SET qc_score = 98.0, error_list = '[{"row": 2, "qc_code": "10/07/2026/Driveway_Sidewalk/TT/01", "category": "Data Accuracy", "subcategory": "Missing object", "error": "Data Accuracy - Missing object", "points": 2}, {"row": 2, "qc_code": "10/07/2026/Driveway_Sidewalk/TT/01", "category": "Data Accuracy", "subcategory": "Incorrect Category/Sub category/Material", "error": "Data Accuracy - Incorrect Category/Sub category/Material", "points": 2}]', updated_at = updated_at WHERE id = 6869 AND tracker_id = 46871 AND qc_score IS NULL;

-- QC 6878 tracker 47186 Mitali Tejani: 98.67%
UPDATE qc_records SET qc_score = 98.67, error_list = '[{"row": 2, "qc_code": "10/8/2026/DSPG/MT/01", "category": "Data Accuracy", "subcategory": "Incorrect Category/Sub category/Material", "error": "Data Accuracy - Incorrect Category/Sub category/Material", "points": 2}, {"row": 3, "qc_code": "10/8/2026/DSPG/MT/02", "category": "Data Accuracy", "subcategory": "Missing object", "error": "Data Accuracy - Missing object", "points": 2}]', updated_at = updated_at WHERE id = 6878 AND tracker_id = 47186 AND qc_score IS NULL;

-- QC 6879 tracker 47183 Hetvi Tarsariya: 98.0%
UPDATE qc_records SET qc_score = 98.0, error_list = '[{"row": 2, "qc_code": "10/08/2026/Driveway_Sidewalk_Parking Lot_Ground Surface/HT/01", "category": "Data Accuracy", "subcategory": "Incorrect Object Boundry", "error": "Data Accuracy - Incorrect Object Boundry", "points": 2}, {"row": 3, "qc_code": "10/08/2026/Driveway_Sidewalk_Parking Lot_Ground Surface/HT/02", "category": "Data Accuracy", "subcategory": "Missing object", "error": "Data Accuracy - Missing object", "points": 2}]', updated_at = updated_at WHERE id = 6879 AND tracker_id = 47183 AND qc_score IS NULL;

-- QC 6881 tracker 47190 Tanvi Sudani: 99.0%
UPDATE qc_records SET qc_score = 99.0, error_list = '[{"row": 2, "qc_code": "10/8/2026/DSPG/TS/1", "category": "Data Accuracy", "subcategory": "Incorrect Object Boundry", "error": "Data Accuracy - Incorrect Object Boundry", "points": 2}]', updated_at = updated_at WHERE id = 6881 AND tracker_id = 47190 AND qc_score IS NULL;

-- QC 6891 tracker 47289 Hetvi Tarsariya: 99.0%
UPDATE qc_records SET qc_score = 99.0, error_list = '[{"row": 2, "qc_code": "10/08/2026/Driveway_Sidewalk_Parking Lot_Ground Surface/HT/03", "category": "Data Accuracy", "subcategory": "Gap between boundy", "error": "Data Accuracy - Gap between boundy", "points": 2}]', updated_at = updated_at WHERE id = 6891 AND tracker_id = 47289 AND qc_score IS NULL;

-- QC 6898 tracker 47279 Mitali Tejani: 98.67%
UPDATE qc_records SET qc_score = 98.67, error_list = '[{"row": 2, "qc_code": "10/8/2026/DSPG/MT/04", "category": "Data Accuracy", "subcategory": "Incorrect Object Boundry", "error": "Data Accuracy - Incorrect Object Boundry", "points": 2}, {"row": 4, "qc_code": "10/8/2026/DSPG/MT/06", "category": "Data Accuracy", "subcategory": "Incorrect Object Boundry", "error": "Data Accuracy - Incorrect Object Boundry", "points": 2}]', updated_at = updated_at WHERE id = 6898 AND tracker_id = 47279 AND qc_score IS NULL;

-- QC 6910 tracker 47349 Mitali Tejani: 98.0%
UPDATE qc_records SET qc_score = 98.0, error_list = '[{"row": 2, "qc_code": "10/8/2026/DSPG/MT/07", "category": "Data Accuracy", "subcategory": "Missing object", "error": "Data Accuracy - Missing object", "points": 2}]', updated_at = updated_at WHERE id = 6910 AND tracker_id = 47349 AND qc_score IS NULL;

-- QC 6911 tracker 47363 Hetvi Tarsariya: 98.0%
UPDATE qc_records SET qc_score = 98.0, error_list = '[{"row": 2, "qc_code": "10/08/2026/Driveway_Sidewalk_Parking Lot_Ground Surface/HT/05", "category": "Data Accuracy", "subcategory": "Incorrect Object Boundry", "error": "Data Accuracy - Incorrect Object Boundry", "points": 2}, {"row": 3, "qc_code": "10/08/2026/Driveway_Sidewalk_Parking Lot_Ground Surface/HT/06", "category": "Data Accuracy", "subcategory": "Incorrect Object Boundry", "error": "Data Accuracy - Incorrect Object Boundry", "points": 2}]', updated_at = updated_at WHERE id = 6911 AND tracker_id = 47363 AND qc_score IS NULL;

-- QC 6921 tracker 47446 Hetvi Tarsariya: 98.0%
UPDATE qc_records SET qc_score = 98.0, error_list = '[{"row": 2, "qc_code": "10/09/2026/Driveway_Sidewalk_Parking Lot_Ground Surface/HT/01", "category": "Data Accuracy", "subcategory": "Missing object", "error": "Data Accuracy - Missing object", "points": 2}]', updated_at = updated_at WHERE id = 6921 AND tracker_id = 47446 AND qc_score IS NULL;

-- QC 6923 tracker 47439 Mitali Tejani: 98.0%
UPDATE qc_records SET qc_score = 98.0, error_list = '[{"row": 2, "qc_code": "10/9/2026/DSPG/MT/01", "category": "Data Accuracy", "subcategory": "Incorrect Object Boundry", "error": "Data Accuracy - Incorrect Object Boundry", "points": 2}]', updated_at = updated_at WHERE id = 6923 AND tracker_id = 47439 AND qc_score IS NULL;

-- QC 6938 tracker 47352 Jaykishan Kondle: 98.0%
UPDATE qc_records SET qc_score = 98.0, error_list = '[{"row": 2, "qc_code": "08/10/2026/imageannotatio/JK/04", "category": "Data Accuracy", "subcategory": "Missing Category/Material", "error": "Data Accuracy - Missing Category/Material", "points": 2}, {"row": 3, "qc_code": "08/10/2026/imageannotatio/JK/05", "category": "Data Accuracy", "subcategory": "Missing object", "error": "Data Accuracy - Missing object", "points": 2}]', updated_at = updated_at WHERE id = 6938 AND tracker_id = 47352 AND qc_score IS NULL;

-- QC 6966 tracker 47545 Tanvi Sudani: 98.67%
UPDATE qc_records SET qc_score = 98.67, error_list = '[{"row": 2, "qc_code": "10/9/2026/DSPG/TS/1", "category": "Data Accuracy", "subcategory": "Incorrect Category/Sub category/Material", "error": "Data Accuracy - Incorrect Category/Sub category/Material", "points": 2}, {"row": 4, "qc_code": "10/9/2026/DSPG/TS/3", "category": "Data Accuracy", "subcategory": "Incorrect Object Boundry", "error": "Data Accuracy - Incorrect Object Boundry", "points": 2}]', updated_at = updated_at WHERE id = 6966 AND tracker_id = 47545 AND qc_score IS NULL;

COMMIT;

-- 3. Verify: every row should now have a score
SELECT id, tracker_id, qc_score FROM qc_records
WHERE id IN (6787, 6788, 6794, 6825, 6826, 6829, 6844, 6869, 6878, 6879, 6881, 6891, 6898, 6910, 6911, 6921, 6923, 6938, 6966);

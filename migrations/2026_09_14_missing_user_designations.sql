-- Additive / idempotent. Insert designations that may be missing from user_designation.
-- Safe to re-run. Skips any title that already exists (case-insensitive trim).
-- Adjust names below if live spelling differs from these labels.

INSERT INTO `user_designation` (`designation`, `is_active`, `created_date`)
SELECT v.designation, 1, CURDATE()
FROM (
  SELECT 'Asst. Manager' AS designation
  UNION ALL SELECT 'Assistant Manager'
  UNION ALL SELECT 'Sr. HR Manager'
  UNION ALL SELECT 'Sr. HR Executive'
  UNION ALL SELECT 'Sr. System Administrator'
  UNION ALL SELECT 'Web Scraping'
  UNION ALL SELECT 'Image Annotator'
  UNION ALL SELECT 'Operations'
  UNION ALL SELECT 'Sr. Operations Executive'
  UNION ALL SELECT 'Sr. Business Analyst'
  UNION ALL SELECT 'Business Development'
  UNION ALL SELECT 'Internship'
  UNION ALL SELECT 'Assistant Team Leader'
) AS v
WHERE NOT EXISTS (
  SELECT 1
  FROM `user_designation` d
  WHERE LOWER(TRIM(d.designation)) = LOWER(TRIM(v.designation))
);

-- Already typically present (skipped if exist): Project Manager, Quality Analyst, Research Executive, etc.

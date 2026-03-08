-- ============================================================
-- Athena DDL – Job Market Intelligence Pipeline
-- Partition projection enabled for cost-efficient querying
-- ============================================================

-- Replace <YOUR_BUCKET> with your actual S3 bucket name.

-- ──────────────────────────────────────────────────────────────
-- 1. Raw Jobs Table
-- ──────────────────────────────────────────────────────────────
CREATE EXTERNAL TABLE IF NOT EXISTS job_market_raw (
  ingested_at   STRING,
  query         STRING,
  location      STRING,
  count         INT,
  records       ARRAY<STRUCT<
    id:           STRING,
    title:        STRING,
    company:      STRING,
    location:     STRING,
    description:  STRING,
    salary:       STRING,
    posted_at:    STRING,
    source:       STRING,
    url:          STRING
  >>
)
PARTITIONED BY (
  year  STRING,
  month STRING,
  day   STRING
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://<YOUR_BUCKET>/raw/'
TBLPROPERTIES (
  'projection.enabled'       = 'true',
  'projection.year.type'     = 'integer',
  'projection.year.range'    = '2024,2030',
  'projection.year.digits'   = '4',
  'projection.month.type'    = 'integer',
  'projection.month.range'   = '01,12',
  'projection.month.digits'  = '2',
  'projection.day.type'      = 'integer',
  'projection.day.range'     = '01,31',
  'projection.day.digits'    = '2',
  'storage.location.template'= 's3://<YOUR_BUCKET>/raw/year=${year}/month=${month}/day=${day}/'
);


-- ──────────────────────────────────────────────────────────────
-- 2. Processed (Normalised) Jobs Table
-- ──────────────────────────────────────────────────────────────
CREATE EXTERNAL TABLE IF NOT EXISTS job_market_processed (
  job_id           STRING,
  source           STRING,
  title            STRING,
  company          STRING,
  location         STRING,
  description      STRING,
  url              STRING,
  salary_raw       STRING,
  salary_min       DOUBLE,
  salary_max       DOUBLE,
  salary_avg       DOUBLE,
  posted_at        STRING,
  ingested_at      STRING,
  search_query     STRING,
  search_location  STRING
)
PARTITIONED BY (
  year  STRING,
  month STRING,
  day   STRING
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
WITH SERDEPROPERTIES ('ignore.malformed.json' = 'true')
LOCATION 's3://<YOUR_BUCKET>/processed/'
TBLPROPERTIES (
  'projection.enabled'       = 'true',
  'projection.year.type'     = 'integer',
  'projection.year.range'    = '2024,2030',
  'projection.year.digits'   = '4',
  'projection.month.type'    = 'integer',
  'projection.month.range'   = '01,12',
  'projection.month.digits'  = '2',
  'projection.day.type'      = 'integer',
  'projection.day.range'     = '01,31',
  'projection.day.digits'    = '2',
  'storage.location.template'= 's3://<YOUR_BUCKET>/processed/year=${year}/month=${month}/day=${day}/'
);


-- ──────────────────────────────────────────────────────────────
-- 3. Feature-Enriched Jobs Table
-- ──────────────────────────────────────────────────────────────
CREATE EXTERNAL TABLE IF NOT EXISTS job_market_features (
  job_id                STRING,
  source                STRING,
  title                 STRING,
  company               STRING,
  location              STRING,
  url                   STRING,
  salary_min            DOUBLE,
  salary_max            DOUBLE,
  salary_avg            DOUBLE,
  posted_at             STRING,
  ingested_at           STRING,
  search_query          STRING,
  experience_level      STRING,
  work_mode             STRING,
  skills                ARRAY<STRING>,
  skill_count           INT,
  feature_extracted_at  STRING
)
PARTITIONED BY (
  year  STRING,
  month STRING,
  day   STRING
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
WITH SERDEPROPERTIES ('ignore.malformed.json' = 'true')
LOCATION 's3://<YOUR_BUCKET>/features/'
TBLPROPERTIES (
  'projection.enabled'       = 'true',
  'projection.year.type'     = 'integer',
  'projection.year.range'    = '2024,2030',
  'projection.year.digits'   = '4',
  'projection.month.type'    = 'integer',
  'projection.month.range'   = '01,12',
  'projection.month.digits'  = '2',
  'projection.day.type'      = 'integer',
  'projection.day.range'     = '01,31',
  'projection.day.digits'    = '2',
  'storage.location.template'= 's3://<YOUR_BUCKET>/features/year=${year}/month=${month}/day=${day}/'
);


-- ──────────────────────────────────────────────────────────────
-- 4. Sample Analytical Queries
-- ──────────────────────────────────────────────────────────────

-- Top 10 most demanded skills this month
SELECT skill, COUNT(*) AS demand_count
FROM job_market_features
CROSS JOIN UNNEST(skills) AS t(skill)
WHERE year = '2025' AND month = '01'
GROUP BY skill
ORDER BY demand_count DESC
LIMIT 10;

-- Average salary by experience level
SELECT
  experience_level,
  ROUND(AVG(salary_avg), 0) AS avg_salary,
  COUNT(*) AS job_count
FROM job_market_features
WHERE salary_avg IS NOT NULL
GROUP BY experience_level
ORDER BY avg_salary DESC;

-- Daily ingestion volume
SELECT
  year, month, day,
  COUNT(*) AS total_jobs,
  COUNT(DISTINCT company) AS unique_companies
FROM job_market_processed
GROUP BY year, month, day
ORDER BY year DESC, month DESC, day DESC;

-- Remote vs onsite breakdown
SELECT work_mode, COUNT(*) AS count
FROM job_market_features
GROUP BY work_mode
ORDER BY count DESC;

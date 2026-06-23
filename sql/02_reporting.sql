-- ============================================================================
-- Reporting layer — materialized views refreshed daily by the insights Lambda.
-- These are the "analytics datasets" / "reporting tables" that BI tools query
-- directly (cheap, pre-aggregated, indexable).
-- ============================================================================

-- Daily skill demand (skill x day) ------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_skill_demand_daily AS
SELECT
    f.load_date,
    s.skill_name,
    COUNT(*)                       AS posting_count,
    ROUND(AVG(f.salary_avg), 0)    AS avg_salary,
    COUNT(*) FILTER (WHERE f.work_mode = 'remote') AS remote_count
FROM fact_job_posting f
JOIN bridge_job_skill b ON b.job_id = f.job_id
JOIN dim_skill        s ON s.skill_id = b.skill_id
GROUP BY f.load_date, s.skill_name
WITH NO DATA;

-- A unique index is required for REFRESH ... CONCURRENTLY.
CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_skill_demand_daily
    ON mv_skill_demand_daily (load_date, skill_name);

-- Salary distribution by experience level ------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_salary_by_level AS
SELECT
    f.load_date,
    f.experience_level,
    COUNT(*)                                                              AS posting_count,
    ROUND(MIN(f.salary_avg), 0)                                          AS min_salary,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.salary_avg)::numeric, 0) AS median_salary,
    ROUND(AVG(f.salary_avg), 0)                                          AS avg_salary,
    ROUND(MAX(f.salary_avg), 0)                                          AS max_salary
FROM fact_job_posting f
WHERE f.salary_avg IS NOT NULL
GROUP BY f.load_date, f.experience_level
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_salary_by_level
    ON mv_salary_by_level (load_date, experience_level);

-- Company hiring leaderboard (rolling, not date-partitioned) ------------------
CREATE OR REPLACE VIEW v_top_hiring_companies AS
SELECT
    c.company_name,
    COUNT(*)                    AS open_postings,
    ROUND(AVG(f.salary_avg), 0) AS avg_salary,
    MAX(f.load_date)            AS last_seen
FROM fact_job_posting f
JOIN dim_company c ON c.company_id = f.company_id
GROUP BY c.company_name
ORDER BY open_postings DESC;

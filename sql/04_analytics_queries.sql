-- ============================================================================
-- Analytics / BI query cookbook (PostgreSQL serving layer).
-- Copy-paste ready; these are the questions recruiters & analysts actually ask.
-- ============================================================================

-- 1. Top 10 most in-demand skills overall ------------------------------------
SELECT s.skill_name, COUNT(*) AS demand
FROM fact_job_posting f
JOIN bridge_job_skill b ON b.job_id = f.job_id
JOIN dim_skill        s ON s.skill_id = b.skill_id
GROUP BY s.skill_name
ORDER BY demand DESC
LIMIT 10;

-- 2. Median salary by experience level ---------------------------------------
SELECT experience_level,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary_avg) AS median_salary,
       COUNT(*) AS postings
FROM fact_job_posting
WHERE salary_avg IS NOT NULL
GROUP BY experience_level
ORDER BY median_salary DESC NULLS LAST;

-- 3. Highest-paying skills (avg salary of postings requiring each skill) ------
SELECT s.skill_name,
       ROUND(AVG(f.salary_avg), 0) AS avg_salary,
       COUNT(*)                    AS postings
FROM fact_job_posting f
JOIN bridge_job_skill b ON b.job_id = f.job_id
JOIN dim_skill        s ON s.skill_id = b.skill_id
WHERE f.salary_avg IS NOT NULL
GROUP BY s.skill_name
HAVING COUNT(*) >= 5
ORDER BY avg_salary DESC
LIMIT 15;

-- 4. Remote vs hybrid vs onsite share ----------------------------------------
SELECT work_mode,
       COUNT(*) AS postings,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM fact_job_posting
GROUP BY work_mode
ORDER BY postings DESC;

-- 5. Skill co-occurrence — which skills are demanded together (self-join) -----
SELECT a.skill_name AS skill_a, b2.skill_name AS skill_b, COUNT(*) AS together
FROM bridge_job_skill x
JOIN bridge_job_skill y  ON x.job_id = y.job_id AND x.skill_id < y.skill_id
JOIN dim_skill a  ON a.skill_id  = x.skill_id
JOIN dim_skill b2 ON b2.skill_id = y.skill_id
GROUP BY a.skill_name, b2.skill_name
ORDER BY together DESC
LIMIT 20;

-- 6. Week-over-week skill momentum (uses the trend view) ----------------------
SELECT * FROM v_skill_momentum
WHERE week_start = date_trunc('week', CURRENT_DATE)::date
ORDER BY wow_pct_change DESC NULLS LAST
LIMIT 10;

-- 7. Daily ingestion / load volume (pipeline health) --------------------------
SELECT load_date,
       COUNT(*)                         AS jobs_loaded,
       COUNT(DISTINCT company_id)       AS companies,
       ROUND(AVG(skill_count), 1)       AS avg_skills_per_job
FROM fact_job_posting
GROUP BY load_date
ORDER BY load_date DESC
LIMIT 30;

-- 8. Companies hiring the most senior data engineers --------------------------
SELECT c.company_name, COUNT(*) AS senior_roles
FROM fact_job_posting f
JOIN dim_company c ON c.company_id = f.company_id
WHERE f.experience_level = 'senior'
GROUP BY c.company_name
ORDER BY senior_roles DESC
LIMIT 10;

-- ============================================================================
-- Historical trend tracking — slowly-growing snapshot tables that let you
-- chart week-over-week / month-over-month movement without rescanning the fact.
-- The insights Lambda appends one snapshot row per skill per day.
-- ============================================================================

CREATE TABLE IF NOT EXISTS trend_skill_weekly (
    week_start    DATE   NOT NULL,
    skill_name    TEXT   NOT NULL,
    posting_count INTEGER NOT NULL,
    avg_salary    NUMERIC(12,2),
    PRIMARY KEY (week_start, skill_name)
);

-- Snapshot procedure: roll the last completed ISO week into the trend table.
CREATE OR REPLACE FUNCTION snapshot_skill_weekly()
RETURNS void LANGUAGE plpgsql AS $$
DECLARE
    wk_start DATE := date_trunc('week', CURRENT_DATE)::date;
BEGIN
    INSERT INTO trend_skill_weekly (week_start, skill_name, posting_count, avg_salary)
    SELECT wk_start,
           s.skill_name,
           COUNT(*),
           ROUND(AVG(f.salary_avg), 2)
    FROM fact_job_posting f
    JOIN bridge_job_skill b ON b.job_id = f.job_id
    JOIN dim_skill        s ON s.skill_id = b.skill_id
    WHERE f.load_date >= wk_start
    GROUP BY s.skill_name
    ON CONFLICT (week_start, skill_name) DO UPDATE
        SET posting_count = EXCLUDED.posting_count,
            avg_salary    = EXCLUDED.avg_salary;
END;
$$;

-- Week-over-week momentum: change vs the previous snapshot for each skill.
CREATE OR REPLACE VIEW v_skill_momentum AS
SELECT
    skill_name,
    week_start,
    posting_count,
    LAG(posting_count) OVER (PARTITION BY skill_name ORDER BY week_start) AS prev_count,
    posting_count
        - LAG(posting_count) OVER (PARTITION BY skill_name ORDER BY week_start) AS wow_change,
    ROUND(
        100.0 * (posting_count - LAG(posting_count) OVER (PARTITION BY skill_name ORDER BY week_start))
        / NULLIF(LAG(posting_count) OVER (PARTITION BY skill_name ORDER BY week_start), 0),
        1
    ) AS wow_pct_change
FROM trend_skill_weekly;

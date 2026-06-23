-- ============================================================================
-- PostgreSQL Serving Layer — Star Schema (Kimball dimensional model)
-- Job Market Intelligence Platform
--
-- Run order: 01_schema.sql -> 02_reporting.sql -> 03_trends.sql -> 04_views.sql
-- Target: PostgreSQL 14+ (RDS db.t3.micro / t4g.micro is Free-Tier eligible)
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS public;

-- ----------------------------------------------------------------------------
-- Dimensions
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_company (
    company_id   BIGSERIAL PRIMARY KEY,
    company_name TEXT NOT NULL UNIQUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dim_skill (
    skill_id   BIGSERIAL PRIMARY KEY,
    skill_name TEXT NOT NULL UNIQUE,
    category   TEXT,                      -- e.g. language / cloud / orchestration
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ----------------------------------------------------------------------------
-- Fact: one row per job posting (grain = job posting)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_job_posting (
    job_id               TEXT PRIMARY KEY,
    source               TEXT,
    title                TEXT,
    company_id           BIGINT REFERENCES dim_company(company_id),
    location             TEXT,
    url                  TEXT,
    salary_min           NUMERIC(12,2),
    salary_max           NUMERIC(12,2),
    salary_avg           NUMERIC(12,2),
    experience_level     TEXT,            -- entry / mid / senior / manager / unknown
    work_mode            TEXT,            -- remote / hybrid / onsite / unknown
    skill_count          INTEGER DEFAULT 0,
    posted_at            TIMESTAMPTZ,
    ingested_at          TIMESTAMPTZ,
    feature_extracted_at TIMESTAMPTZ,
    load_date            DATE NOT NULL DEFAULT CURRENT_DATE
);

-- Bridge: many-to-many job <-> skill
CREATE TABLE IF NOT EXISTS bridge_job_skill (
    job_id   TEXT NOT NULL REFERENCES fact_job_posting(job_id) ON DELETE CASCADE,
    skill_id BIGINT NOT NULL REFERENCES dim_skill(skill_id) ON DELETE CASCADE,
    PRIMARY KEY (job_id, skill_id)
);

-- ----------------------------------------------------------------------------
-- Indexes (query-shaped: load_date scans, level/mode filters, skill joins)
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_fact_load_date    ON fact_job_posting (load_date);
CREATE INDEX IF NOT EXISTS idx_fact_exp_level     ON fact_job_posting (experience_level);
CREATE INDEX IF NOT EXISTS idx_fact_work_mode     ON fact_job_posting (work_mode);
CREATE INDEX IF NOT EXISTS idx_fact_company       ON fact_job_posting (company_id);
CREATE INDEX IF NOT EXISTS idx_bridge_skill       ON bridge_job_skill (skill_id);

-- ----------------------------------------------------------------------------
-- Insights output table (one curated row per day)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS daily_insight (
    insight_date DATE PRIMARY KEY,
    headline     TEXT,
    payload      JSONB,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

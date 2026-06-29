# Real-Time Job Market Intelligence Data Platform

[![CI](https://github.com/jeeva-s0604/aws-job-market-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/jeeva-s0604/aws-job-market-pipeline/actions/workflows/ci.yml)
![python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)
![license](https://img.shields.io/badge/license-MIT-green)

A **production-grade, serverless, event-driven AWS data platform** that ingests
job postings daily, lands them in a 3-tier S3 data lake, transforms / deduplicates
/ enriches them through chained Lambdas, loads a **PostgreSQL star schema** behind
a **data-quality gate**, tracks historical trends, and **auto-generates daily
market insights** — all on a Free-Tier footprint.

> Lake **and** warehouse: Amazon **Athena** queries the S3 lake directly;
> **PostgreSQL/RDS** serves an indexed dimensional model for BI & reporting.

---

## Architecture

```
 EventBridge (06:00)        ┌────────────── S3 DATA LAKE ──────────────┐
        │                   │ raw/  →  processed/  →  features/         │
        ▼                   └───┬──────────┬──────────────┬────────────┘
  ┌────────────┐  PutObject     │ event    │ event        │ event
  │ Ingestor   │───────────────►│          │              │
  └────────────┘            ┌───▼───┐  ┌───▼────────┐  ┌──▼──────────────┐
   APIs (Apify/JSearch)     │Transf.│  │ Feature    │  │ Loader (PG)     │
                            │+dedupe│  │ Extractor  │  │ DQ gate → upsert│
                            └───────┘  └────────────┘  └──────┬──────────┘
  ┌────────────┐                                              │
  │  Athena    │◄── partition projection (lake SQL)           ▼
  └────────────┘                                      ┌────────────────┐
 EventBridge (08:00) ──► ┌────────────┐  refresh MVs  │ PostgreSQL/RDS │
                         │ Insights   │──────────────►│ dims+facts+MVs │
                         │ trends+SNS │   daily_insight└────────────────┘
                         └────────────┘
 Observability: JSON logs + EMF metrics → CloudWatch Alarms + Dashboard + SNS
```

Full write-up: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) ·
data model & partitioning: [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) ·
ops: [`docs/RUNBOOK.md`](docs/RUNBOOK.md).

---

## What it does

| Capability | How |
|------------|-----|
| **Ingest** | Daily EventBridge cron → Lambda pulls postings from APIs → `raw/` |
| **3-tier data lake** | `raw/` → `processed/` → `features/`, `year/month/day` partitioned, S3 lifecycle |
| **Transform** | Schema normalisation, salary min/max/avg parsing, SHA-256 dedup (30-day window) |
| **Enrich** | Skill tokenisation (20+ skills), experience level, remote/hybrid/onsite |
| **Data quality gate** | Schema/type/range/freshness checks; loads abort below 80% pass rate |
| **Serving layer** | PostgreSQL Kimball star schema (fact + company/skill dims + bridge) |
| **Reporting** | Materialized views (skill demand, salary by level), company leaderboard |
| **Historical trends** | Weekly snapshots + `LAG()` window-function momentum |
| **Auto insights** | Daily top/rising skills, salary bands, remote share → `daily_insight` + SNS |
| **Lake SQL** | Athena partition projection — no Glue crawler, no `MSCK REPAIR` |
| **Monitoring** | Structured JSON logs, EMF metrics, CloudWatch alarms + dashboard, SNS |
| **CI/CD** | GitHub Actions: Ruff lint+format, pytest+coverage (3.11/3.12), packaging, OIDC deploy |

---

## Project structure

```
aws-job-market-pipeline/
├── lambdas/
│   ├── common/              # shared: structured logging, EMF metrics, DQ validation
│   ├── ingestor/            # APIs → raw/
│   ├── transformer/         # normalise + dedupe → processed/
│   ├── feature_extractor/   # skills / level / mode → features/
│   ├── loader/              # DQ gate + upsert → PostgreSQL star schema
│   └── insights/            # refresh reporting MVs, trends, daily_insight + SNS
├── sql/                     # PostgreSQL DDL: schema, reporting, trends, analytics
├── athena/                  # lake DDL with partition projection (3 tiers)
├── infra/
│   ├── setup_aws.py         # S3 + EventBridge + S3-notification wiring
│   └── monitoring.py        # SNS + CloudWatch alarms + dashboard
├── tests/                   # unit + integration (moto) + data-quality tests
├── docs/                    # architecture, data model, runbook, interview prep, resume
├── .github/workflows/       # ci.yml, deploy.yml
├── Makefile  pyproject.toml  requirements*.txt  .env.example
```

---

## Quickstart

```bash
git clone https://github.com/jeeva-s0604/aws-job-market-pipeline.git
cd aws-job-market-pipeline
make install          # dev dependencies
make lint             # ruff lint + format check
make test             # full test suite (no AWS / DB needed — moto + mocks)
make cov              # tests with coverage report
make package          # build deployment zips for every Lambda → build/
```

The pipeline runs locally end-to-end with **mock data** (no API key) and
**moto-mocked S3** (no AWS account).

### Deploy to AWS (Free-Tier)

1. **Bootstrap lake + schedules + S3 notifications**
   ```bash
   python infra/setup_aws.py --bucket my-job-pipeline --region ap-south-1 \
     --ingestor-arn ... --transformer-arn ... --extractor-arn ... \
     --loader-arn ... --insights-arn ...
   ```
2. **Create the PostgreSQL schema** (RDS `db.t4g.micro`)
   ```bash
   psql "$DATABASE_URL" -f sql/01_schema.sql -f sql/02_reporting.sql -f sql/03_trends.sql
   ```
3. **Register Athena tables** — run `athena/create_tables.sql` (replace `<YOUR_BUCKET>`).
4. **Provision monitoring**
   ```bash
   python infra/monitoring.py --region ap-south-1 --email you@example.com
   ```
5. **CI/CD** — pushes run `ci.yml`; deploy via the manual `deploy.yml` (GitHub OIDC).

Configuration lives in environment variables — see [`.env.example`](.env.example).
DB credentials resolve from **AWS Secrets Manager** (`DB_SECRET_ARN`) in production.

---

## Sample analytics

```sql
-- Top skills (PostgreSQL serving layer)
SELECT s.skill_name, COUNT(*) AS demand
FROM fact_job_posting f
JOIN bridge_job_skill b USING (job_id)
JOIN dim_skill s USING (skill_id)
GROUP BY 1 ORDER BY 2 DESC LIMIT 10;

-- Median salary by experience level
SELECT experience_level,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary_avg) AS median_salary
FROM fact_job_posting WHERE salary_avg IS NOT NULL GROUP BY 1;
```

More in [`sql/04_analytics_queries.sql`](sql/04_analytics_queries.sql) (lake
equivalents in [`athena/create_tables.sql`](athena/create_tables.sql)).

---

## Engineering practices

- **Idempotent** loads (`INSERT … ON CONFLICT`) + SHA-256 dedup → exactly-once
  *effects* under at-least-once S3 delivery.
- **Immutable raw** landing → fully reproducible reprocessing (re-trigger, never
  re-scrape).
- **Data quality as a gate**, with the pass rate exposed as an alarmable metric.
- **Observability built in** — structured logs, custom metrics, alarms, dashboard.
- **Tested**: unit (pure functions), integration (moto S3), and DQ tests; lint +
  format enforced in CI.

---

## Tech stack

`Python 3.12` · `SQL` · `PostgreSQL` · `AWS Lambda` · `Amazon S3` ·
`Amazon EventBridge` · `Amazon Athena` · `AWS Secrets Manager` · `Amazon SNS` ·
`Amazon CloudWatch` · `GitHub Actions` · `Boto3` · `psycopg2` · `pytest` ·
`moto` · `Ruff`

---

## For recruiters & interviews

- 📄 Resume bullets + LinkedIn description: [`docs/RESUME_LINKEDIN.md`](docs/RESUME_LINKEDIN.md)
- 🎤 Interview prep (50 Data Engineering + 25 AWS + 25 SQL Q&A): [`docs/INTERVIEW_PREP.md`](docs/INTERVIEW_PREP.md)

---

*Built by Jeeva S — [linkedin.com/in/jeeva-s0604](https://linkedin.com/in/jeeva-s0604)*

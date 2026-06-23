# Resume Bullets & LinkedIn Description

## ATS-friendly resume bullets

Pick 3–5; they're written with action verbs + tools + outcome, and seeded with
keywords ATS scanners look for (Python, SQL, AWS, Lambda, S3, Athena, ETL,
PostgreSQL, data lake, CI/CD).

- Built a **serverless, event-driven AWS data platform** (S3, Lambda,
  EventBridge, Athena, PostgreSQL/RDS) that ingests, transforms, and serves job-
  market data daily on a **zero-idle, Free-Tier** footprint.
- Designed a **3-tier (raw → processed → features) S3 data lake** with
  `year/month/day` partitioning and **Athena partition projection**, eliminating
  Glue crawlers and `MSCK REPAIR` while keeping query scans to a single partition.
- Engineered **idempotent ETL** in Python: SHA-256 fingerprint deduplication over
  a 30-day window and `INSERT ... ON CONFLICT` upserts, guaranteeing exactly-once
  effects under at-least-once S3 event delivery.
- Modeled a **Kimball star schema** in PostgreSQL (fact + company/skill dimensions
  + job–skill bridge) and built **materialized views** and **window-function**
  trend reporting (week-over-week skill momentum, median salary by level).
- Implemented a **data-quality gate** (schema, type, range, freshness checks) that
  blocks loads below an 80% pass rate and emits the pass rate as a CloudWatch
  metric for alerting.
- Added **observability**: structured JSON logging (CloudWatch Logs Insights),
  custom **EMF metrics**, CloudWatch **alarms** (errors/throttles/duration/DQ),
  an SNS alert topic, and a dashboard.
- Set up **CI/CD with GitHub Actions** (Ruff lint + format, pytest with coverage
  on Python 3.11/3.12, Lambda packaging) and an OIDC-based deploy workflow.
- Automated **daily insight generation** (top/rising skills, salary bands, remote
  share) written to PostgreSQL and published via SNS.

### One-line summary (for a resume header / profile)

> Data Engineer — built a production-grade, serverless AWS pipeline (Python, SQL,
> S3, Lambda, Athena, PostgreSQL) with a partitioned data lake, dimensional
> warehouse, data-quality gating, monitoring, and CI/CD.

---

## LinkedIn "Projects" description

**Real-Time Job Market Intelligence Data Platform**
*Python · SQL · AWS (S3, Lambda, EventBridge, Athena) · PostgreSQL · GitHub Actions*

An end-to-end, serverless data platform that turns raw job postings into
analytics-ready market intelligence — entirely event-driven and Free-Tier.

A daily EventBridge schedule triggers a Lambda that ingests postings into a
3-tier S3 data lake (raw → processed → features). Each S3 write chains the next
Lambda: normalising and deduplicating records, engineering ML-ready features
(skills, experience level, work mode), and loading a Kimball star schema in
PostgreSQL behind a data-quality gate. Amazon Athena queries the lake directly
via partition projection; a final Lambda refreshes materialized reporting views,
computes week-over-week trends with SQL window functions, and publishes a daily
insight digest over SNS.

The project follows data-engineering best practices throughout: immutable raw
landing for reproducibility, idempotent upserts for exactly-once effects,
structured logging and custom CloudWatch metrics, alarms + dashboards for
monitoring, a tested codebase (unit + integration + data-quality tests), and
CI/CD via GitHub Actions.

**Highlights**
- Serverless & event-driven — scales per stage, runs only when there's work
- Medallion data lake + dimensional warehouse (lake *and* serving layer)
- Data-quality gating with alarmable pass-rate metrics
- Full observability: JSON logs, EMF metrics, alarms, dashboard, SNS
- CI/CD: lint, format, tests, coverage, packaging, OIDC deploy

🔗 Code: github.com/jeeva-s0604/aws-job-market-pipeline

# Architecture

## Overview

A fully serverless, event-driven data platform that ingests job postings daily,
lands them in an S3 data lake, transforms and enriches them through chained
Lambdas, loads a curated star schema into PostgreSQL, and auto-generates
market insights. Athena queries the lake directly; PostgreSQL serves BI/reporting.

## End-to-end flow

```
                         EventBridge (cron 06:00 UTC)
                                    │
                                    ▼
                          ┌──────────────────┐
                          │ Lambda: Ingestor │  Apify/JSearch APIs → raw JSON
                          └────────┬─────────┘
                                   │ PutObject  raw/year=/month=/day=
                                   ▼
   ┌─────────────────────────  S3 DATA LAKE  ─────────────────────────┐
   │  raw/        (immutable landing, 90-day lifecycle)               │
   │  processed/  (normalised + deduped, 365-day)                     │
   │  features/   (ML-ready enrichment, 365-day)                      │
   └───┬───────────────────┬───────────────────────┬─────────────────┘
       │ S3 event          │ S3 event              │ S3 event
       ▼                   ▼                       ▼
 ┌─────────────┐    ┌──────────────────┐    ┌──────────────────────┐
 │ Transformer │    │ Feature Extractor│    │ Loader (PostgreSQL)  │
 │ normalise + │    │ skills / level / │    │ validate → upsert     │
 │ dedupe      │    │ work-mode        │    │ star schema           │
 └─────────────┘    └──────────────────┘    └──────────┬───────────┘
                                                        │
   ┌──────────────────┐                                 ▼
   │ Amazon Athena    │◄── partition projection   ┌──────────────────┐
   │ (lake SQL)       │     over features/        │  PostgreSQL (RDS)│
   └──────────────────┘                           │  dims + facts +  │
                                                   │  reporting MVs   │
   EventBridge (cron 08:00 UTC)                    └────────┬─────────┘
            │                                               │
            ▼                                               ▼
   ┌──────────────────┐    refresh MVs + write     ┌──────────────────┐
   │ Lambda: Insights │───────────────────────────►│ daily_insight    │
   │ trends + headline│         SNS (email)        │ + SNS alert      │
   └──────────────────┘                            └──────────────────┘

Observability (cross-cutting): structured JSON logs + EMF custom metrics
→ CloudWatch Logs Insights, Alarms (errors/throttles/duration/dq_pass_rate),
SNS topic, and a CloudWatch dashboard.
```

## Components

| Stage | Service | Trigger | Responsibility |
|-------|---------|---------|----------------|
| Ingest | Lambda `ingestor` | EventBridge cron | Pull postings from APIs → `raw/` |
| Transform | Lambda `transformer` | S3 `raw/` event | Normalise schema, parse salary, dedupe (SHA-256, 30d window) → `processed/` |
| Enrich | Lambda `feature_extractor` | S3 `processed/` event | Skill tokenisation, experience level, work mode → `features/` |
| Load | Lambda `loader` | S3 `features/` event | DQ gate + upsert into PostgreSQL star schema |
| Insights | Lambda `insights` | EventBridge cron | Refresh reporting MVs, compute trends, write `daily_insight`, SNS alert |
| Query (lake) | Athena | on-demand | Partition-projected SQL over all 3 tiers |
| Query (serving) | PostgreSQL | on-demand | BI/reporting against dims + facts + MVs |

## Why this design

- **Event-driven over orchestrated.** S3-event chaining means each stage scales
  independently and only runs when there is work — no idle scheduler, no
  always-on EC2. This keeps the whole thing inside the AWS Free Tier.
- **Medallion (raw → processed → features) lake.** Immutable raw landing makes
  every downstream step reproducible and debuggable; reprocessing is just a
  re-trigger, never a re-scrape.
- **Lake *and* warehouse.** Athena gives cheap exploratory SQL straight over S3
  (no servers); PostgreSQL gives indexed, low-latency, BI-friendly serving with
  a real dimensional model. Each is used where it's strongest.
- **DQ as a gate, not an afterthought.** The loader refuses to write a batch
  whose validation pass-rate drops below a threshold, so bad data never reaches
  the serving layer; the rejection itself is an alarmable metric.
- **Partition projection** removes `MSCK REPAIR`/Glue-crawler overhead and keeps
  Athena scans cheap and predictable.

## Technology decisions

| Need | Choice | Alternative considered | Rationale |
|------|--------|------------------------|-----------|
| Compute | Lambda | Glue/EMR jobs | Volume is small (100s–1000s/day); Lambda is free-tier and zero-idle |
| Lake format | partitioned JSON | Parquet | Simpler for JSON APIs; Athena reads both. Parquet is the documented next step |
| Lake query | Athena + projection | Glue crawler | No crawler cost; deterministic partitions |
| Serving DB | PostgreSQL (RDS) | Redshift | Free-tier eligible; full ANSI SQL, window funcs, JSONB |
| Scheduling | EventBridge | cron on EC2 | Serverless, no host to patch |
| Secrets | Secrets Manager | env vars | No plaintext DB passwords in Lambda config |
| Observability | EMF + CloudWatch | 3rd-party APM | Native, no extra cost, metrics without `PutMetricData` |
| CI/CD | GitHub Actions | CodePipeline | Free for public repos, lint+test+package in one place |

See [`DATA_MODEL.md`](./DATA_MODEL.md) for schema, partitioning, and storage strategy,
and [`RUNBOOK.md`](./RUNBOOK.md) for monitoring and operations.

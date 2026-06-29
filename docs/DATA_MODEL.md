# Data Model, Partitioning & Storage Strategy

## 1. Lake zones (medallion)

| Zone | Prefix | Format | Schema | Lifecycle |
|------|--------|--------|--------|-----------|
| Raw | `raw/` | JSON (envelope + `records[]`) | source-shaped, untouched | expire 90d |
| Processed | `processed/` | JSON (canonical) | normalised, deduped, typed | expire 365d |
| Features | `features/` | JSON (enriched) | + `skills[]`, `experience_level`, `work_mode` | expire 365d |

Raw is **immutable**: we never edit a landed object, so any transformation can
be replayed deterministically by re-triggering downstream Lambdas.

## 2. Partition strategy (lake)

All three zones are partitioned by ingestion date:

```
features/year=2025/month=01/day=15/<query>_<location>_<HHMMSS>_features.json
```

- **Why date partitioning?** Every analytical question is time-scoped ("this
  month's top skills", "WoW trend"), so date is the highest-selectivity pruning
  key. It also aligns 1:1 with the daily batch and with S3 lifecycle rules.
- **Athena partition projection** is configured in `athena/create_tables.sql`
  (`year` 2024–2030, `month` 01–12, `day` 01–31). This means **no Glue crawler
  and no `MSCK REPAIR TABLE`** — Athena computes partition locations from the
  query predicate, so a single-day query scans exactly one day's objects.
- **Granularity choice:** day-level, not hour-level. Daily batches produce a
  handful of objects/day; hour partitions would create many tiny files (the
  "small files problem") and inflate S3 LIST/GET costs for no pruning benefit.

## 3. Serving layer — dimensional (Kimball star) schema

```
        dim_company                         dim_skill
        ┌───────────────┐                   ┌────────────┐
        │ company_id PK │                   │ skill_id PK│
        │ company_name  │                   │ skill_name │
        └──────┬────────┘                   │ category   │
               │                            └──────┬─────┘
               │ 1                                 │ 1
               │                                   │
               │ *               bridge_job_skill  │ *
        ┌──────▼───────────────────┐   ┌───────────▼──────────┐
        │ fact_job_posting         │ * │ job_id  FK           │
        │ job_id PK                │◄──┤ skill_id FK          │
        │ company_id FK            │   └──────────────────────┘
        │ salary_min/max/avg       │
        │ experience_level         │
        │ work_mode, skill_count   │
        │ posted_at, load_date ... │
        └──────────────────────────┘
```

- **Grain:** one row in `fact_job_posting` per job posting.
- **`bridge_job_skill`** resolves the many-to-many between jobs and skills,
  which is what makes "top skills" and "skill co-occurrence" queries clean joins
  instead of array unnesting.
- **`load_date`** is the warehouse partition key for trend/reporting queries and
  is indexed.
- **Idempotency:** every write is an `INSERT ... ON CONFLICT DO UPDATE` (upsert),
  so re-running the loader on the same `features/` object is safe — re-delivery
  of an S3 event (at-least-once) never duplicates rows.

### Reporting & trend objects

| Object | Type | Purpose |
|--------|------|---------|
| `mv_skill_demand_daily` | materialized view | skill × day demand + avg salary (BI source) |
| `mv_salary_by_level` | materialized view | min/median/avg/max salary by experience level |
| `v_top_hiring_companies` | view | rolling company leaderboard |
| `trend_skill_weekly` | table | weekly snapshots for long-horizon trend charts |
| `v_skill_momentum` | view | WoW change via `LAG()` window function |
| `daily_insight` | table | one curated insight row/day (JSONB payload + headline) |

Materialized views are refreshed `CONCURRENTLY` by the insights Lambda (a unique
index exists on each so concurrent refresh is allowed and reads aren't blocked).

## 4. Storage strategy & cost control

- **S3 lifecycle:** raw expires at 90 days (cheap to re-derive), curated zones at
  365 days. Configured in `infra/setup_aws.py`.
- **Versioning** on the bucket guards against accidental overwrite of raw data.
- **PostgreSQL on RDS `db.t4g.micro`** (Free-Tier eligible, 20 GB gp2). The fact
  table is narrow and indexed on the columns actually filtered/joined
  (`load_date`, `experience_level`, `work_mode`, `company_id`, `skill_id`).
- **Athena cost:** partition projection + date predicates keep per-query scan to
  a single partition; converting curated zones to **Parquet + Snappy** is the
  documented next optimisation (columnar pruning → ~10× less scanned bytes).

## 5. Data quality contract

`lambdas/common/validation.py` enforces, before any load:

- **Schema/required-field** presence (`job_id`, `title`, `company`).
- **Type** checks (numeric salaries, string fields).
- **Range** checks (salary within plausible bounds; `min ≤ max`).
- **Freshness** (postings within 90 days are clean; stale → warning, not drop).

The loader computes a batch **pass rate** and aborts the load (raising, so the
Lambda fails and CloudWatch alarms) if it falls below `DQ_PASS_RATE_THRESHOLD`
(default 0.80). The pass rate is emitted as the `dq_pass_rate` metric.

# Interview Preparation

Questions are grounded in **this** project so you can answer from real,
defensible experience. Each has a short model answer; expand with specifics from
the code.

---

## A. Data Engineering (50)

1. **Walk me through this pipeline end to end.** EventBridge triggers the
   ingestor → raw JSON to S3 → S3 event fires the transformer (normalise +
   dedupe) → features Lambda (skills/level/mode) → loader validates and upserts a
   PostgreSQL star schema → insights Lambda refreshes reporting views and emits a
   daily headline. Athena queries the lake directly.
2. **Why event-driven instead of an orchestrator like Airflow?** Volume is low
   and bursty; S3-event chaining scales per stage, runs only when there's work,
   and stays in the Free Tier. Airflow/MWAA would be an always-on cost for a
   handful of daily tasks.
3. **What is the medallion architecture and where is it here?** Raw → processed →
   features zones in S3. Raw is immutable landing; processed is normalised/deduped;
   features is enriched/ML-ready. Each promotes data quality and reusability.
4. **Why keep raw immutable?** Reproducibility and debuggability — any downstream
   logic can be replayed without re-scraping the source. Cheap insurance.
5. **How do you handle schema drift from the source API?** The normaliser maps
   many source field aliases to one canonical schema; the validation layer flags
   missing/typed fields; DQ pass-rate alarms surface drift early.
6. **How is deduplication implemented?** SHA-256 fingerprint of
   `title|company|location|job_id`, lower-cased, checked against a rolling 30-day
   index in S3; the index is pruned by a freshness cutoff each run.
7. **Why a 30-day dedup window rather than forever?** Job reposts recur; an
   unbounded index grows unbounded and would suppress legitimately re-opened
   roles. The window bounds memory and matches reposting cadence.
8. **What's your idempotency story?** S3 events are at-least-once. Loads are
   `INSERT ... ON CONFLICT DO UPDATE`, so re-delivery upserts the same row — no
   duplicates. Dedup index + fingerprints add a second layer.
9. **Lake vs warehouse — why both?** Athena gives cheap, serverless, exploratory
   SQL over S3; PostgreSQL gives indexed, low-latency, BI-friendly serving with a
   real dimensional model. Each used where strongest.
10. **Explain the star schema you built.** `fact_job_posting` (grain = one
    posting) with `dim_company`, `dim_skill`, and a `bridge_job_skill` for the
    many-to-many between jobs and skills.
11. **Why a bridge table instead of an array column?** It turns "top skills" and
    "skill co-occurrence" into clean indexed joins instead of array unnesting, and
    normalises skill names into one dimension.
12. **How do you load the dimensions?** Upsert-and-return-id with a per-batch
    in-memory cache so a repeated company/skill is resolved once per batch.
13. **What's your partition strategy?** Date partitions (`year/month/day`) in S3
    matching the daily batch and lifecycle rules; `load_date` indexed in Postgres.
14. **Why date as the partition key?** Highest-selectivity pruning key — almost
    every query is time-scoped — and it aligns with batch cadence and lifecycle.
15. **Athena partition projection — what and why?** Athena derives partition
    locations from the query predicate via DDL ranges, eliminating Glue crawlers
    and `MSCK REPAIR`. Cheaper, deterministic, zero-maintenance.
16. **The small-files problem — how do you avoid it?** Day-level (not hour-level)
    partitions and batched writes keep object counts low; Parquet compaction is the
    documented next step.
17. **Why would you move curated zones to Parquet?** Columnar + compression →
    Athena scans only needed columns and far fewer bytes (~10× cheaper queries),
    plus predicate pushdown.
18. **What data-quality checks run, and when?** Schema/required-field, type,
    range (salary bounds, min≤max), and freshness — in the loader, before any write.
19. **What happens when DQ fails?** Below the pass-rate threshold the loader
    raises; the Lambda fails, the batch isn't written, and `dq_batch_rejected` /
    the Lambda error alarm fire.
20. **Hard-fail vs quarantine — how did you choose?** Hard structural errors drop
    the record; soft issues (stale dates) keep the record but log a warning, so we
    don't lose otherwise-good data.
21. **How do you compute trends?** Weekly snapshots into `trend_skill_weekly`,
    then `LAG()` window functions in `v_skill_momentum` for WoW change.
22. **Why materialized views for reporting?** Pre-aggregated, indexable, and cheap
    to read repeatedly by BI; refreshed `CONCURRENTLY` so reads aren't blocked.
23. **Why is a unique index required on those MVs?** `REFRESH ... CONCURRENTLY`
    needs one to diff rows without an exclusive lock.
24. **How are insights generated automatically?** The insights Lambda runs queries
    (top/rising skills, median salary by level, remote share), builds a headline,
    upserts `daily_insight`, and publishes to SNS.
25. **How do you backfill / reprocess?** Re-trigger downstream stages on existing
    raw objects; idempotent upserts make it safe. No source re-scrape.
26. **Late-arriving data — how handled?** Freshness check tolerates a window;
    `load_date` records when we saw it, `posted_at` when it was posted, so both
    arrival and event time are preserved.
27. **Event time vs processing time here?** `posted_at` = event time, `ingested_at`
    / `load_date` = processing time. Trends use `load_date`; recency uses `posted_at`.
28. **How would you add a second source?** New ingestor branch writing the same
    raw envelope; the normaliser already maps aliases, so processed/features/serving
    are unchanged. `source` column keeps provenance.
29. **How do you guarantee at-least-once vs exactly-once?** S3/Lambda give
    at-least-once; exactly-once *effect* comes from idempotent upserts + dedupe.
30. **Where could this lose data?** Lambda retries exhausting to a poison message —
    mitigated by a DLQ (documented next step) and immutable raw enabling replay.
31. **How do you test without AWS?** Pure functions (normalise, salary parse,
    fingerprint, skill/level/mode, validation) are unit-tested locally; the loader
    is tested with a mocked psycopg2 connection; `moto` mocks S3 for integration.
32. **What's your CI doing?** Ruff lint + format check, pytest with coverage on
    3.11/3.12, and a packaging job that builds each Lambda zip.
33. **How is the code structured for reuse?** Shared `common/` package (logging,
    metrics, validation) bundled into each Lambda zip via the Makefile.
34. **Secrets management?** DB credentials from Secrets Manager (preferred) with
    env-var fallback for local dev; no plaintext passwords in Lambda config.
35. **How do you observe the pipeline?** Structured JSON logs → Logs Insights;
    EMF custom metrics → CloudWatch; alarms on errors/throttles/duration/DQ; a
    dashboard; SNS alerting.
36. **Why EMF over PutMetricData?** No extra IAM/API call — print an EMF blob and
    CloudWatch ingests it as a metric. Cheaper and simpler in Lambda.
37. **How do you bound cost?** Free-tier services, S3 lifecycle expiry, partition
    projection + date predicates, narrow indexed fact table, micro RDS instance.
38. **What SLAs/SLOs would you set?** Freshness (data ≤ 24 h old), completeness
    (DQ pass rate ≥ 80%), and pipeline success (all stages green daily).
39. **How would you scale 100×?** Switch ingest to batched/paginated pulls,
    curated zones to Parquet, loader to `COPY`/batched executemany, and consider
    Glue/Spark if volume justifies it.
40. **Why Lambda over Glue here?** Sub-thousand records/day; Lambda is free-tier
    and zero-idle. Glue/EMR earn their keep at GB–TB scale, not here.
41. **How do you handle PII / compliance?** Postings are public; no PII stored. If
    added, encrypt at rest (default S3/RDS), restrict via IAM, and tokenise.
42. **What's your DLQ / retry strategy?** Lambda async retries (2x) then a
    documented SQS DLQ; immutable raw enables manual replay after a fix.
43. **How do you version schema changes?** Additive columns with defaults +
    `ON CONFLICT` upserts; migrations are ordered SQL files (`01_`…`04_`).
44. **Why `numeric` not `float` for salary in Postgres?** Exact decimal money
    avoids float rounding error in aggregates.
45. **How do you prevent duplicate skills in the dimension?** `UNIQUE(skill_name)`
    + `ON CONFLICT DO UPDATE ... RETURNING skill_id`.
46. **What's the grain of `mv_skill_demand_daily` and why?** skill × `load_date` —
    the lowest grain that still answers daily/weekly skill-demand questions cheaply.
47. **How do you measure pipeline freshness?** `max(load_date)` vs now, plus
    per-stage `*_duration_ms` and last-success timestamps in logs.
48. **What would you add next?** Parquet conversion, Glue Data Catalog, dbt for
    transformation lineage/tests, SQS DLQs, and a QuickSight/Metabase dashboard.
49. **What was the hardest correctness issue?** Idempotency under at-least-once S3
    delivery — solved with upserts + fingerprint dedup so retries never duplicate.
50. **If a recruiter asks the business value?** It quantifies skill demand, salary
    bands, and remote share over time — directly useful for upskilling and job
    targeting, and demonstrable as a live, automated data product.

---

## B. AWS (25)

1. **S3 storage classes — when use which?** Standard for hot curated data;
   Standard-IA / Glacier for cold raw archives via lifecycle transitions.
2. **What is S3 partitioning and how does Athena use it?** Key prefixes
   (`year=/month=/day=`) become partitions; Athena prunes scans by predicate,
   here via partition projection (no crawler).
3. **S3 event notifications — delivery semantics?** At-least-once; design
   consumers to be idempotent (we use upserts).
4. **Lambda cold starts — causes and mitigations?** First init / scale-out;
   mitigate with smaller packages, provisioned concurrency, and lazy imports
   (we import psycopg2 inside the handler path).
5. **Lambda limits relevant here?** 15-min max timeout (we use 180 s), /tmp 512 MB+,
   memory↔CPU coupling, payload size — all comfortably within bounds.
6. **How does Lambda get DB creds securely?** Secrets Manager `GetSecretValue` via
   the execution role; rotation supported; no plaintext env secrets.
7. **EventBridge vs CloudWatch Events?** EventBridge is the superset (schemas,
   buses, partner events); cron scheduling here is `cron(0 6 * * ? *)`.
8. **Athena pricing model and how you reduce it?** $/TB scanned — reduce with
   partition pruning, columnar Parquet, and selecting only needed columns.
9. **Partition projection vs Glue crawler?** Projection computes partitions from
   DDL ranges (free, deterministic); crawler discovers them (costs, scheduling).
10. **What is Glue Data Catalog?** A Hive-compatible metastore Athena/Spark share;
    here Athena tables register against S3 locations.
11. **RDS Free-Tier specifics?** 750 h/month of `db.t3/t4g.micro`, 20 GB storage,
    single-AZ — enough for this serving layer.
12. **How would you secure Lambda↔RDS?** Lambda in the RDS VPC/subnets, security
    group allowing 5432 from the Lambda SG only, RDS not publicly accessible.
13. **IAM least privilege example here?** Loader role: `s3:GetObject` on
    `features/*`, `secretsmanager:GetSecretValue` on the one secret, and basic
    Lambda logging — nothing else.
14. **What is an SNS topic used for here?** Fan-out of alarms and the daily insight
    to email/Slack subscribers.
15. **CloudWatch Logs vs Metrics vs Alarms?** Logs = text/JSON events; Metrics =
    time series; Alarms = thresholds on metrics that trigger actions (SNS).
16. **What is EMF?** Embedded Metric Format — JSON in logs that CloudWatch parses
    into metrics, avoiding `PutMetricData` calls.
17. **How do S3 lifecycle rules work here?** Expire `raw/` at 90d, curated at 365d;
    can also transition to cheaper classes.
18. **Versioning on S3 — why?** Protects raw landing from accidental
    overwrite/delete; enables recovery.
19. **How would you deploy Lambdas via CI?** GitHub OIDC → assume an AWS role →
    `aws lambda update-function-code` with the built zip (see `deploy.yml`).
20. **Why OIDC over long-lived AWS keys in GitHub?** No stored secrets; short-lived
    creds via web-identity federation; least-privilege per environment.
21. **What's the Athena results location?** A separate S3 prefix for query output;
    set in workgroup or query config.
22. **How do you handle Lambda dependencies like psycopg2?** Bundle into the zip
    (Makefile `pip install -t`) or use a Lambda layer; `psycopg2-binary` for the
    Amazon Linux runtime.
23. **DynamoDB vs RDS for this serving layer?** RDS — we need ad-hoc joins,
    aggregates, and window functions; DynamoDB suits known-key access patterns.
24. **How to make ingestion resilient to API failures?** Timeouts, try/except per
    query×location, partial-success writes, and retries/DLQ for the async path.
25. **Cost guardrails on AWS?** Budgets + alerts, S3 lifecycle, partition pruning,
    micro instances, and turning idle resources off (serverless does this by default).

---

## C. SQL (25)

1. **INNER vs LEFT JOIN — where in this project?** Fact↔dim joins are INNER (every
   fact has a company); rising-skills compares weeks with LEFT JOIN to keep
   skills absent last week.
2. **Write "top 10 skills".** `SELECT skill_name, COUNT(*) FROM fact f JOIN
   bridge b USING(job_id) JOIN dim_skill s USING(skill_id) GROUP BY 1 ORDER BY 2
   DESC LIMIT 10;`
3. **GROUP BY vs window functions?** GROUP BY collapses rows; window functions
   compute across a partition while keeping rows — used in `v_skill_momentum`.
4. **Explain `LAG()` in the momentum view.** Returns the previous week's
   `posting_count` per skill ordered by week, enabling WoW deltas without a self-join.
5. **How do you compute a median in Postgres?** `PERCENTILE_CONT(0.5) WITHIN GROUP
   (ORDER BY salary_avg)` — used in `mv_salary_by_level`.
6. **`ROW_NUMBER` vs `RANK` vs `DENSE_RANK`?** Tie handling: unique sequence vs
   gapped ties vs gapless ties.
7. **What does `ON CONFLICT DO UPDATE` do?** PostgreSQL upsert — insert, or update
   on a unique/PK conflict; the basis of our idempotent loads.
8. **Why `ON CONFLICT DO NOTHING` for the bridge?** A job↔skill link is idempotent;
   re-inserting the same pair should be a no-op.
9. **NULL handling — `COALESCE` / `NULLIF` examples here?** `NULLIF(denominator,0)`
   avoids divide-by-zero in remote-share %; `COALESCE(prior,0)` for new skills.
10. **CTE vs subquery?** CTEs (`WITH this_week AS ...`) improve readability and let
    you reference a result multiple times; used in rising-skills.
11. **How would you find skills demanded together?** Self-join the bridge on
    `job_id` with `skill_id < skill_id` to avoid mirror/duplicate pairs (query #5).
12. **What indexes did you add and why?** `load_date`, `experience_level`,
    `work_mode`, `company_id`, `skill_id` — the columns actually filtered/joined.
13. **How does an index help a GROUP BY/JOIN?** Avoids full scans/sorts; enables
    index scans and efficient hash/merge joins on the keyed columns.
14. **`HAVING` vs `WHERE`?** WHERE filters rows pre-aggregation; HAVING filters
    groups post-aggregation (e.g. `HAVING COUNT(*) >= 5` for highest-paying skills).
15. **Write median salary by experience level.** See `04_analytics_queries.sql` #2.
16. **What is a materialized view and its trade-off?** A stored query result —
    fast reads, but stale until refreshed; we refresh daily `CONCURRENTLY`.
17. **Why `REFRESH ... CONCURRENTLY` and its requirement?** Doesn't lock readers;
    requires a unique index on the MV.
18. **Transaction isolation — why one transaction per batch?** All-or-nothing load
    per file: a mid-batch failure rolls back, keeping the warehouse consistent.
19. **How to detect duplicates in SQL?** `SELECT job_id, COUNT(*) FROM fact GROUP
    BY job_id HAVING COUNT(*) > 1;` (should be empty given the PK).
20. **`DISTINCT` vs `GROUP BY`?** Both dedupe; GROUP BY also aggregates. We use
    `COUNT(DISTINCT company_id)` for unique-company counts.
21. **Window frame: running total of jobs by day?** `SUM(COUNT(*)) OVER (ORDER BY
    load_date)` after grouping by day.
22. **`PERCENTILE_CONT` vs `PERCENTILE_DISC`?** Continuous interpolates between
    values; discrete returns an actual data point.
23. **How would you pivot remote/hybrid/onsite into columns?** `COUNT(*) FILTER
    (WHERE work_mode='remote')` etc. — the `FILTER` clause (used in reporting MV).
24. **Explain the query plan you'd check for a slow report.** `EXPLAIN ANALYZE` —
    look for seq scans on `fact`, missing index usage, and costly sorts.
25. **How do you guard divide-by-zero in pct calcs?** `/ NULLIF(x, 0)` (returns
    NULL instead of erroring) — used throughout the analytics queries.

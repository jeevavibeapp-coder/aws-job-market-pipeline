# Operations Runbook — Monitoring, Logging & Alerting

## Logging

Every Lambda logs **structured JSON** via `lambdas/common/logging_utils.py`.
Records carry `timestamp`, `level`, `logger`, `message`, plus any `ctx` fields
(e.g. `stage`, `duration_ms`, validation report). Query in **CloudWatch Logs
Insights**:

```
fields @timestamp, level, stage, duration_ms, message
| filter level = "ERROR"
| sort @timestamp desc
| limit 50
```

```
-- Data-quality pass rate over time
fields @timestamp, pass_rate, invalid
| filter ispresent(pass_rate)
| sort @timestamp desc
```

## Custom metrics (EMF)

Emitted to namespace `JobMarketPipeline` with **no PutMetricData IAM
permission** required (CloudWatch Embedded Metric Format printed to stdout):

| Metric | Unit | Emitted by | Meaning |
|--------|------|------------|---------|
| `<stage>_duration_ms` | Milliseconds | all (via `timed`) | per-stage latency |
| `<stage>_errors` | Count | all (via `timed`) | per-stage failures |
| `rows_loaded` | Count | loader | rows upserted into PostgreSQL |
| `dq_pass_rate` | None | loader | batch validation pass rate (0–1) |
| `dq_invalid_records` | Count | loader | records dropped by DQ |
| `dq_batch_rejected` | Count | loader | batches rejected by the DQ gate |
| `insights_generated` | Count | insights | daily insight produced |

## Alarms (provisioned by `infra/monitoring.py`)

| Alarm | Condition | Action |
|-------|-----------|--------|
| `<fn>-errors` | Lambda `Errors ≥ 1` in 5 min | SNS notify |
| `<fn>-throttles` | Lambda `Throttles ≥ 1` in 5 min | SNS notify |
| `<fn>-duration-p99` | p99 `Duration > 170 s` (near 180 s timeout) | SNS notify |
| `pipeline-data-quality-low` | `dq_pass_rate < 0.8` (1 h avg) | SNS notify |

Set up:

```bash
python infra/monitoring.py --region ap-south-1 --email you@example.com
# confirm the SNS subscription email, then alerts + dashboard are live
```

A CloudWatch dashboard `JobMarketPipeline` charts invocations, errors, rows
loaded, and DQ pass rate.

## Common incidents

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| `*-errors` alarm on loader | DB unreachable / Secrets rotated | check RDS status, Secrets Manager value, Lambda VPC/SG to RDS |
| `pipeline-data-quality-low` | upstream API schema drift | inspect `errors[]` in the validation log; patch `validation.py` / normaliser |
| `dq_batch_rejected` spike | bad ingest batch | raw object is immutable — fix transform and re-trigger; no re-scrape needed |
| Insights MV refresh warnings | first run / empty data | benign; MVs populate once facts exist |
| Athena returns 0 rows | partition predicate outside projection range | widen `projection.year.range` in DDL |

## Replaying data

Because `raw/` is immutable and every write is idempotent, reprocessing is just
re-triggering downstream stages — e.g. copy a raw object onto itself to re-emit
the S3 event, or invoke the transformer with a synthetic S3 event payload. No
duplicates result (SHA-256 dedupe + `ON CONFLICT` upserts).

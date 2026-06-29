"""
Lambda: PostgreSQL Loader (serving layer)
Triggered by: S3 PUT event on features/ prefix

Reads feature-enriched records from S3, runs data-quality validation, then
upserts them into the PostgreSQL star schema (dim_company, dim_skill,
fact_job_posting, bridge_job_skill). This is the warehouse/serving layer that
powers reporting tables and BI dashboards.

Credentials are resolved from AWS Secrets Manager (preferred) or env vars,
so no plaintext passwords live in the Lambda configuration.
"""

import json
import os
import sys
from datetime import UTC, datetime

import boto3

# Allow `from common import ...` whether running in Lambda (layer) or locally.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.logging_utils import emit_metric, get_logger, timed  # noqa: E402
from common.validation import validate_batch  # noqa: E402

logger = get_logger("loader")
s3 = boto3.client("s3")

DB_SECRET_ARN = os.environ.get("DB_SECRET_ARN", "")
PASS_RATE_THRESHOLD = float(os.environ.get("DQ_PASS_RATE_THRESHOLD", "0.80"))


def _get_db_config() -> dict:
    """Resolve DB connection params from Secrets Manager, falling back to env."""
    if DB_SECRET_ARN:
        secret = boto3.client("secretsmanager").get_secret_value(SecretId=DB_SECRET_ARN)
        cfg = json.loads(secret["SecretString"])
        return {
            "host": cfg["host"],
            "port": int(cfg.get("port", 5432)),
            "dbname": cfg.get("dbname", "jobmarket"),
            "user": cfg["username"],
            "password": cfg["password"],
        }
    return {
        "host": os.environ["DB_HOST"],
        "port": int(os.environ.get("DB_PORT", "5432")),
        "dbname": os.environ.get("DB_NAME", "jobmarket"),
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
    }


def _connect():
    import psycopg2  # imported lazily so unit tests don't require the driver

    return psycopg2.connect(connect_timeout=10, **_get_db_config())


UPSERT_COMPANY = """
INSERT INTO dim_company (company_name)
VALUES (%s)
ON CONFLICT (company_name) DO UPDATE SET company_name = EXCLUDED.company_name
RETURNING company_id;
"""

UPSERT_SKILL = """
INSERT INTO dim_skill (skill_name)
VALUES (%s)
ON CONFLICT (skill_name) DO UPDATE SET skill_name = EXCLUDED.skill_name
RETURNING skill_id;
"""

UPSERT_FACT = """
INSERT INTO fact_job_posting (
    job_id, source, title, company_id, location, url,
    salary_min, salary_max, salary_avg, experience_level, work_mode,
    skill_count, posted_at, ingested_at, feature_extracted_at, load_date
)
VALUES (%(job_id)s, %(source)s, %(title)s, %(company_id)s, %(location)s, %(url)s,
        %(salary_min)s, %(salary_max)s, %(salary_avg)s, %(experience_level)s, %(work_mode)s,
        %(skill_count)s, %(posted_at)s, %(ingested_at)s, %(feature_extracted_at)s, %(load_date)s)
ON CONFLICT (job_id) DO UPDATE SET
    salary_avg = EXCLUDED.salary_avg,
    experience_level = EXCLUDED.experience_level,
    work_mode = EXCLUDED.work_mode,
    skill_count = EXCLUDED.skill_count,
    feature_extracted_at = EXCLUDED.feature_extracted_at,
    load_date = EXCLUDED.load_date;
"""

LINK_SKILL = """
INSERT INTO bridge_job_skill (job_id, skill_id)
VALUES (%s, %s)
ON CONFLICT (job_id, skill_id) DO NOTHING;
"""


def _parse_ts(raw):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def upsert_records(conn, records: list[dict]) -> int:
    """Idempotently upsert a batch into the star schema within one transaction."""
    company_cache: dict[str, int] = {}
    skill_cache: dict[str, int] = {}
    written = 0
    load_date = datetime.now(UTC).date()

    with conn.cursor() as cur:
        for rec in records:
            # Strip first, THEN default: a whitespace-only value must become
            # "Unknown", not an empty string in dim_company.
            company = (rec.get("company") or "").strip() or "Unknown"
            if company not in company_cache:
                cur.execute(UPSERT_COMPANY, (company,))
                company_cache[company] = cur.fetchone()[0]

            cur.execute(
                UPSERT_FACT,
                {
                    "job_id": rec["job_id"],
                    "source": rec.get("source"),
                    "title": rec.get("title"),
                    "company_id": company_cache[company],
                    "location": rec.get("location"),
                    "url": rec.get("url"),
                    "salary_min": rec.get("salary_min"),
                    "salary_max": rec.get("salary_max"),
                    "salary_avg": rec.get("salary_avg"),
                    "experience_level": rec.get("experience_level", "unknown"),
                    "work_mode": rec.get("work_mode", "unknown"),
                    "skill_count": rec.get("skill_count", 0),
                    "posted_at": _parse_ts(rec.get("posted_at")),
                    "ingested_at": _parse_ts(rec.get("ingested_at")),
                    "feature_extracted_at": _parse_ts(rec.get("feature_extracted_at")),
                    "load_date": load_date,
                },
            )

            for skill in rec.get("skills", []) or []:
                if skill not in skill_cache:
                    cur.execute(UPSERT_SKILL, (skill,))
                    skill_cache[skill] = cur.fetchone()[0]
                cur.execute(LINK_SKILL, (rec["job_id"], skill_cache[skill]))

            written += 1

    conn.commit()
    return written


def _read_features(bucket: str, key: str) -> list[dict]:
    obj = s3.get_object(Bucket=bucket, Key=key)
    return json.loads(obj["Body"].read().decode()).get("records", [])


def lambda_handler(event, context):
    results = []

    for s3_event in event.get("Records", []):
        bucket = s3_event["s3"]["bucket"]["name"]
        key = s3_event["s3"]["object"]["key"]
        if not key.startswith("features/"):
            logger.info("Skipping non-features key", extra={"ctx": {"key": key}})
            continue

        with timed(logger, "load", source="features"):
            records = _read_features(bucket, key)
            clean, report = validate_batch(records)
            logger.info("Validation report", extra={"ctx": report.as_dict()})
            emit_metric("dq_pass_rate", report.pass_rate, "None")
            emit_metric("dq_invalid_records", report.invalid, "Count")

            if report.pass_rate < PASS_RATE_THRESHOLD:
                emit_metric("dq_batch_rejected", 1, "Count")
                logger.error(
                    "Batch rejected: pass rate below threshold",
                    extra={"ctx": {"pass_rate": report.pass_rate, "threshold": PASS_RATE_THRESHOLD}},
                )
                raise RuntimeError(
                    f"Data quality gate failed: pass_rate={report.pass_rate} "
                    f"< threshold={PASS_RATE_THRESHOLD}"
                )

            conn = _connect()
            try:
                written = upsert_records(conn, clean)
            finally:
                conn.close()

            emit_metric("rows_loaded", written, "Count")
            results.append({"source_key": key, "loaded": written, "rejected": report.invalid})

    return {"status": "success", "loaded_files": len(results), "details": results}

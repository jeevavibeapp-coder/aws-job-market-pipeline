"""
Lambda: Feature Extractor
Triggered by: S3 PUT event on processed/ prefix
Reads normalised records and engineers ML-ready features:
  - Skill tokenisation (from description)
  - Experience level parsing (from title / description)
  - Salary normalisation (min / max / avg already computed by transformer)
  - Remote / hybrid / onsite classification
Writes enriched records to features/ prefix.
"""

import json
import logging
import os
import re
from datetime import UTC, datetime

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "job-market-pipeline-raw")


# ── Skill taxonomy ────────────────────────────────────────────────────────────
SKILL_PATTERNS: dict[str, list[str]] = {
    "python": [r"\bpython\b", r"\bpyspark\b"],
    "sql": [r"\bsql\b", r"\bpostgres(?:ql)?\b", r"\bmysql\b", r"\btsql\b"],
    "spark": [r"\bapache\s+spark\b", r"\bpyspark\b", r"\bspark\s+sql\b"],
    "aws": [
        r"\baws\b",
        r"\bamazon\s+web\b",
        r"\blambda\b",
        r"\bs3\b",
        r"\bglue\b",
        r"\bredshift\b",
        r"\bathena\b",
    ],
    "azure": [r"\bazure\b", r"\bsynapse\b", r"\bdata\s+factory\b"],
    "gcp": [r"\bgcp\b", r"\bgoogle\s+cloud\b", r"\bbigquery\b", r"\bdataflow\b"],
    "airflow": [r"\bairflow\b", r"\bapache\s+airflow\b"],
    "dbt": [r"\bdbt\b", r"\bdata\s+build\s+tool\b"],
    "kafka": [r"\bkafka\b", r"\bapache\s+kafka\b"],
    "docker": [r"\bdocker\b", r"\bcontainer\b"],
    "kubernetes": [r"\bkubernetes\b", r"\bk8s\b"],
    "snowflake": [r"\bsnowflake\b"],
    "databricks": [r"\bdatabricks\b"],
    "pandas": [r"\bpandas\b"],
    "git": [r"\bgit\b", r"\bgithub\b", r"\bgitlab\b"],
    "java": [r"\bjava\b"],
    "scala": [r"\bscala\b"],
    "terraform": [r"\bterraform\b", r"\biac\b"],
    "etl": [r"\betl\b", r"\belt\b", r"\bpipeline\b"],
    "data_modeling": [r"\bdata\s+model(?:ing)?\b", r"\bdimensional\b", r"\bstar\s+schema\b"],
}

EXP_LEVEL_PATTERNS: list[tuple[str, list[str]]] = [
    (
        "entry",
        [r"\bjunior\b", r"\bentry.?level\b", r"\bgraduate\b", r"\bfresher\b", r"\b0.?[–-]?\s*2\s*years?\b"],
    ),
    ("mid", [r"\bmid.?level\b", r"\b2.?[–-]?\s*5\s*years?\b", r"\b3\+?\s*years?\b"]),
    (
        "senior",
        [r"\bsenior\b", r"\bsr\b", r"\blead\b", r"\bprincipal\b", r"\b5\+?\s*years?\b", r"\b7\+?\s*years?\b"],
    ),
    ("manager", [r"\bmanager\b", r"\bdirector\b", r"\bvp\b", r"\bhead\s+of\b"]),
]

WORK_MODE_PATTERNS: dict[str, list[str]] = {
    "remote": [r"\bremote\b", r"\bwork\s+from\s+home\b", r"\bwfh\b"],
    "hybrid": [r"\bhybrid\b"],
    "onsite": [r"\bonsite\b", r"\bon.?site\b", r"\bin.?office\b", r"\bin\s+person\b"],
}


def _text_blob(record: dict) -> str:
    return " ".join(
        filter(
            None,
            [
                record.get("title", ""),
                record.get("description", ""),
                record.get("location", ""),
            ],
        )
    ).lower()


def extract_skills(text: str) -> list[str]:
    text = text.lower()
    found = []
    for skill, patterns in SKILL_PATTERNS.items():
        if any(re.search(p, text) for p in patterns):
            found.append(skill)
    return sorted(set(found))


def extract_experience_level(text: str) -> str:
    for level, patterns in EXP_LEVEL_PATTERNS:
        if any(re.search(p, text, re.IGNORECASE) for p in patterns):
            return level
    return "unknown"


def extract_work_mode(text: str) -> str:
    for mode, patterns in WORK_MODE_PATTERNS.items():
        if any(re.search(p, text, re.IGNORECASE) for p in patterns):
            return mode
    return "unknown"


def enrich(record: dict) -> dict:
    blob = _text_blob(record)
    return {
        **record,
        "skills": extract_skills(blob),
        "skill_count": len(extract_skills(blob)),
        "experience_level": extract_experience_level(blob),
        "work_mode": extract_work_mode(blob),
        "feature_extracted_at": datetime.now(UTC).isoformat(),
    }


# ── S3 helpers ────────────────────────────────────────────────────────────────


def _read_processed(bucket: str, key: str) -> dict:
    obj = s3.get_object(Bucket=bucket, Key=key)
    return json.loads(obj["Body"].read().decode())


def _write_features(records: list[dict], source_key: str, run_ts: datetime) -> str:
    year = run_ts.strftime("%Y")
    month = run_ts.strftime("%m")
    day = run_ts.strftime("%d")
    stem = source_key.rsplit("/", 1)[-1].replace("_transformed.json", "")
    dest_key = f"features/year={year}/month={month}/day={day}/{stem}_features.json"

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=dest_key,
        Body=json.dumps(
            {
                "feature_extracted_at": run_ts.isoformat(),
                "count": len(records),
                "records": records,
            },
            default=str,
        ).encode(),
        ContentType="application/json",
    )
    logger.info("Wrote %d feature records → s3://%s/%s", len(records), BUCKET_NAME, dest_key)
    return dest_key


# ── Entry point ───────────────────────────────────────────────────────────────


def lambda_handler(event, context):
    run_ts = datetime.now(UTC)
    results = []

    for s3_event in event.get("Records", []):
        bucket = s3_event["s3"]["bucket"]["name"]
        key = s3_event["s3"]["object"]["key"]

        if not key.startswith("processed/"):
            logger.info("Skipping key outside processed/: %s", key)
            continue

        logger.info("Feature-extracting s3://%s/%s", bucket, key)
        payload = _read_processed(bucket, key)
        enriched = [enrich(r) for r in payload.get("records", [])]

        if enriched:
            dest = _write_features(enriched, key, run_ts)
            results.append({"source_key": key, "dest_key": dest, "enriched": len(enriched)})

    return {"status": "success", "processed_files": len(results), "details": results}

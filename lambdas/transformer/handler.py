"""
Lambda: Job Market Transformer
Triggered by: S3 PUT event on raw/ prefix
Reads raw JSON, normalises schema, casts types, deduplicates (30-day window),
and writes Parquet-equivalent JSON to processed/ prefix.
"""

import json
import re
import hashlib
import boto3
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

BUCKET_NAME          = os.environ.get("S3_BUCKET_NAME", "job-market-pipeline-raw")
DEDUP_INDEX_KEY      = "metadata/dedup_index.json"
FRESHNESS_DAYS       = int(os.environ.get("FRESHNESS_DAYS", "30"))


# ── Schema normalisation helpers ──────────────────────────────────────────────

def _clean_str(val) -> Optional[str]:
    if val is None:
        return None
    return str(val).strip() or None


def _parse_salary(raw: str) -> dict:
    """Extract min / max / avg salary (USD) from free-text strings."""
    if not raw:
        return {"salary_min": None, "salary_max": None, "salary_avg": None}

    nums = re.findall(r"[\d,]+", raw.replace("$", "").replace("k", "000"))
    amounts = []
    for n in nums:
        try:
            amounts.append(float(n.replace(",", "")))
        except ValueError:
            pass

    if not amounts:
        return {"salary_min": None, "salary_max": None, "salary_avg": None}

    sal_min = min(amounts)
    sal_max = max(amounts)
    return {
        "salary_min": sal_min,
        "salary_max": sal_max,
        "salary_avg": round((sal_min + sal_max) / 2, 2),
    }


def _parse_date(raw) -> Optional[str]:
    if not raw:
        return None
    if isinstance(raw, (int, float)):
        try:
            return datetime.fromtimestamp(raw, tz=timezone.utc).isoformat()
        except Exception:
            pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(raw)[:19], fmt[:len(fmt)]).isoformat()
        except ValueError:
            pass
    return str(raw)


def _normalise(raw_record: dict, ingest_meta: dict) -> dict:
    """Map any raw API shape to canonical schema."""
    sal = _parse_salary(raw_record.get("salary", "") or raw_record.get("salaryRange", ""))
    return {
        # identifiers
        "job_id":        _clean_str(raw_record.get("id") or raw_record.get("jobId")),
        "source":        _clean_str(raw_record.get("source", ingest_meta.get("source", "unknown"))),
        # job details
        "title":         _clean_str(raw_record.get("title") or raw_record.get("jobTitle")),
        "company":       _clean_str(raw_record.get("company") or raw_record.get("companyName")),
        "location":      _clean_str(raw_record.get("location") or raw_record.get("jobLocation")),
        "description":   _clean_str(raw_record.get("description") or raw_record.get("jobDescription")),
        "url":           _clean_str(raw_record.get("url") or raw_record.get("jobUrl")),
        # salary
        "salary_raw":    _clean_str(raw_record.get("salary") or raw_record.get("salaryRange")),
        "salary_min":    sal["salary_min"],
        "salary_max":    sal["salary_max"],
        "salary_avg":    sal["salary_avg"],
        # dates
        "posted_at":     _parse_date(raw_record.get("posted_at") or raw_record.get("postedAt")),
        "ingested_at":   ingest_meta.get("ingested_at"),
        # query context
        "search_query":  ingest_meta.get("query"),
        "search_location": ingest_meta.get("location"),
    }


# ── Deduplication ─────────────────────────────────────────────────────────────

def _record_fingerprint(rec: dict) -> str:
    sig = f"{rec.get('title','')}|{rec.get('company','')}|{rec.get('location','')}|{rec.get('job_id','')}"
    return hashlib.sha256(sig.lower().encode()).hexdigest()


def _load_dedup_index() -> dict:
    try:
        obj  = s3.get_object(Bucket=BUCKET_NAME, Key=DEDUP_INDEX_KEY)
        return json.loads(obj["Body"].read().decode())
    except s3.exceptions.NoSuchKey:
        return {}
    except Exception as exc:
        logger.warning("Could not load dedup index: %s", exc)
        return {}


def _save_dedup_index(index: dict):
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=DEDUP_INDEX_KEY,
        Body=json.dumps(index, default=str).encode(),
        ContentType="application/json",
    )


def _prune_old_entries(index: dict, cutoff: datetime) -> dict:
    return {k: v for k, v in index.items() if v >= cutoff.isoformat()}


def deduplicate(records: list[dict]) -> tuple[list[dict], int]:
    """Remove records already seen within the freshness window."""
    cutoff    = datetime.now(timezone.utc) - timedelta(days=FRESHNESS_DAYS)
    index     = _load_dedup_index()
    index     = _prune_old_entries(index, cutoff)
    unique    = []
    dup_count = 0
    now_iso   = datetime.now(timezone.utc).isoformat()

    for rec in records:
        fp = _record_fingerprint(rec)
        if fp in index:
            dup_count += 1
        else:
            index[fp] = now_iso
            unique.append(rec)

    _save_dedup_index(index)
    return unique, dup_count


# ── S3 helpers ────────────────────────────────────────────────────────────────

def _read_raw_file(bucket: str, key: str) -> dict:
    obj = s3.get_object(Bucket=bucket, Key=key)
    return json.loads(obj["Body"].read().decode())


def _write_processed(records: list[dict], source_key: str, run_ts: datetime) -> str:
    year  = run_ts.strftime("%Y")
    month = run_ts.strftime("%m")
    day   = run_ts.strftime("%d")
    stem  = source_key.rsplit("/", 1)[-1].replace(".json", "")
    dest_key = f"processed/year={year}/month={month}/day={day}/{stem}_transformed.json"

    s3.put_object(
        Bucket      = BUCKET_NAME,
        Key         = dest_key,
        Body        = json.dumps({"transformed_at": run_ts.isoformat(), "count": len(records), "records": records}, default=str).encode(),
        ContentType = "application/json",
    )
    logger.info("Wrote %d processed records → s3://%s/%s", len(records), BUCKET_NAME, dest_key)
    return dest_key


# ── Entry point ───────────────────────────────────────────────────────────────

def lambda_handler(event, context):
    run_ts  = datetime.now(timezone.utc)
    results = []

    for s3_event in event.get("Records", []):
        bucket = s3_event["s3"]["bucket"]["name"]
        key    = s3_event["s3"]["object"]["key"]

        if not key.startswith("raw/"):
            logger.info("Skipping non-raw key: %s", key)
            continue

        logger.info("Processing s3://%s/%s", bucket, key)
        raw_payload = _read_raw_file(bucket, key)

        ingest_meta = {
            "ingested_at": raw_payload.get("ingested_at"),
            "query":       raw_payload.get("query"),
            "location":    raw_payload.get("location"),
            "source":      "apify",
        }
        raw_records  = raw_payload.get("records", [])
        normalised   = [_normalise(r, ingest_meta) for r in raw_records]
        unique, dups = deduplicate(normalised)

        logger.info("Records: raw=%d  unique=%d  duplicates=%d", len(raw_records), len(unique), dups)

        if unique:
            dest = _write_processed(unique, key, run_ts)
            results.append({"source_key": key, "dest_key": dest, "written": len(unique), "duplicates": dups})

    return {"status": "success", "processed_files": len(results), "details": results}

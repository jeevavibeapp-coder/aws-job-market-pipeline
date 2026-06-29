"""
Lambda: Job Market Ingestor
Triggered by: EventBridge (daily schedule)
Fetches job listings from JSearch API (via Apify) and stores raw JSON to S3.
"""

import json
import logging
import os
import urllib.parse
import urllib.request
from datetime import UTC, datetime

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

# ── Config ────────────────────────────────────────────────────────────────────
BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "job-market-pipeline-raw")
APIFY_TOKEN = os.environ.get("APIFY_API_TOKEN", "")
ACTOR_ID = os.environ.get("APIFY_ACTOR_ID", "bebity~linkedin-jobs-scraper")
SEARCH_TERMS = os.environ.get("SEARCH_TERMS", "Data Engineer,Junior Data Engineer,ETL Developer").split(",")
LOCATIONS = os.environ.get("LOCATIONS", "India,Remote").split(",")
MAX_RESULTS = int(os.environ.get("MAX_RESULTS", "100"))


def fetch_jobs_from_apify(search_query: str, location: str) -> list[dict]:
    """Call Apify actor synchronously and return list of job records."""
    if not APIFY_TOKEN:
        logger.warning("APIFY_API_TOKEN not set – returning mock data.")
        return _mock_jobs(search_query, location)

    run_input = {
        "searchQueries": [search_query],
        "location": location,
        "maxResults": MAX_RESULTS,
    }
    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items"
    url += f"?token={APIFY_TOKEN}&timeout=120"

    req = urllib.request.Request(
        url,
        data=json.dumps(run_input).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=130) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        logger.error("Apify call failed for '%s' / '%s': %s", search_query, location, exc)
        return []


def _mock_jobs(query: str, location: str) -> list[dict]:
    """Return synthetic records so the pipeline can be tested without API keys."""
    base = [
        {
            "id": f"mock-{query[:3].lower()}-001",
            "title": f"{query} – Sample Role",
            "company": "Acme Corp",
            "location": location,
            "description": f"Looking for a skilled {query} to join our data team.",
            "salary": "$80,000 – $100,000",
            "posted_at": datetime.now(UTC).isoformat(),
            "source": "mock",
            "url": "https://example.com/jobs/001",
        },
        {
            "id": f"mock-{query[:3].lower()}-002",
            "title": f"Senior {query}",
            "company": "DataFlow Inc",
            "location": location,
            "description": f"Senior {query} role with AWS and Spark experience.",
            "salary": "$110,000 – $130,000",
            "posted_at": datetime.now(UTC).isoformat(),
            "source": "mock",
            "url": "https://example.com/jobs/002",
        },
    ]
    return base


def write_to_s3(records: list[dict], query: str, location: str, timestamp: datetime) -> str:
    """Persist raw records to S3 under the raw/ prefix with date partitioning."""
    year = timestamp.strftime("%Y")
    month = timestamp.strftime("%m")
    day = timestamp.strftime("%d")
    safe_query = urllib.parse.quote_plus(query.replace(" ", "_"))
    safe_location = urllib.parse.quote_plus(location.replace(" ", "_"))

    key = (
        f"raw/year={year}/month={month}/day={day}/"
        f"{safe_query}_{safe_location}_{timestamp.strftime('%H%M%S')}.json"
    )
    payload = {
        "ingested_at": timestamp.isoformat(),
        "query": query,
        "location": location,
        "count": len(records),
        "records": records,
    }
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=key,
        Body=json.dumps(payload, default=str).encode(),
        ContentType="application/json",
    )
    logger.info("Wrote %d records → s3://%s/%s", len(records), BUCKET_NAME, key)
    return key


def lambda_handler(event, context):
    """Entry point – iterates all (query × location) combos and dumps raw JSON to S3."""
    run_ts = datetime.now(UTC)
    all_keys = []
    total = 0

    for query in SEARCH_TERMS:
        for location in LOCATIONS:
            logger.info("Fetching: query='%s'  location='%s'", query.strip(), location.strip())
            records = fetch_jobs_from_apify(query.strip(), location.strip())
            if records:
                key = write_to_s3(records, query.strip(), location.strip(), run_ts)
                all_keys.append(key)
                total += len(records)

    result = {
        "status": "success",
        "ingested_at": run_ts.isoformat(),
        "total_records": total,
        "s3_keys": all_keys,
    }
    logger.info("Ingestor complete: %s", result)
    return result

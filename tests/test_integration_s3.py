"""
Integration tests: exercise the real S3 read/write paths of the transformer and
feature-extractor Lambdas against a moto-mocked S3 bucket. No AWS account needed.

These verify the S3-event chaining contract: a raw object produces a processed
object, which produces a features object with engineered fields.
"""

import json
import os

import boto3
import pytest

moto = pytest.importorskip("moto")
from moto import mock_aws  # noqa: E402

BUCKET = "test-job-pipeline"
REGION = "us-east-1"


def _s3_event(key: str) -> dict:
    return {"Records": [{"s3": {"bucket": {"name": BUCKET}, "object": {"key": key}}}]}


@pytest.fixture
def s3_setup(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    with mock_aws():
        client = boto3.client("s3", region_name=REGION)
        client.create_bucket(Bucket=BUCKET)

        # Repoint each handler's module-level client + bucket at the mock.
        from lambdas.feature_extractor import handler as fx
        from lambdas.transformer import handler as tx

        for mod in (tx, fx):
            monkeypatch.setattr(mod, "s3", client)
            monkeypatch.setattr(mod, "BUCKET_NAME", BUCKET)

        yield client, tx, fx


def _put_raw(client, key: str):
    payload = {
        "ingested_at": "2025-01-15T06:00:00+00:00",
        "query": "Data Engineer",
        "location": "Remote",
        "count": 2,
        "records": [
            {
                "id": "job-1",
                "title": "Senior Data Engineer",
                "company": "Acme",
                "location": "Remote",
                "description": "Python, SQL, AWS Lambda, Airflow. 5+ years.",
                "salary": "$120,000 - $150,000",
                "posted_at": "2025-01-14T00:00:00",
                "source": "linkedin",
                "url": "https://example.com/1",
            },
            {
                "id": "job-2",
                "title": "Junior Data Engineer",
                "company": "DataFlow",
                "location": "Remote",
                "description": "Python, SQL. Entry level. Fully remote.",
                "salary": "$70,000 - $90,000",
                "posted_at": "2025-01-14T00:00:00",
                "source": "linkedin",
                "url": "https://example.com/2",
            },
        ],
    }
    client.put_object(Bucket=BUCKET, Key=key, Body=json.dumps(payload).encode())


def _list(client, prefix):
    resp = client.list_objects_v2(Bucket=BUCKET, Prefix=prefix)
    return [o["Key"] for o in resp.get("Contents", [])]


def test_transform_then_feature_extract_chain(s3_setup):
    client, tx, fx = s3_setup
    raw_key = "raw/year=2025/month=01/day=15/data_engineer_remote_060000.json"
    _put_raw(client, raw_key)

    # Stage 1: transform
    tx_result = tx.lambda_handler(_s3_event(raw_key), None)
    assert tx_result["status"] == "success"
    processed_keys = _list(client, "processed/")
    assert len(processed_keys) == 1

    processed = json.loads(client.get_object(Bucket=BUCKET, Key=processed_keys[0])["Body"].read())
    assert processed["count"] == 2
    rec = processed["records"][0]
    assert rec["salary_min"] == 120000.0 and rec["salary_max"] == 150000.0

    # Stage 2: feature extraction over the processed object
    fx_result = fx.lambda_handler(_s3_event(processed_keys[0]), None)
    assert fx_result["status"] == "success"
    feature_keys = _list(client, "features/")
    assert len(feature_keys) == 1

    features = json.loads(client.get_object(Bucket=BUCKET, Key=feature_keys[0])["Body"].read())
    enriched = {r["title"]: r for r in features["records"]}
    senior = enriched["Senior Data Engineer"]
    assert senior["experience_level"] == "senior"
    assert senior["work_mode"] == "remote"
    assert {"python", "sql", "aws", "airflow"}.issubset(set(senior["skills"]))


def test_transformer_skips_non_raw_keys(s3_setup):
    client, tx, _ = s3_setup
    result = tx.lambda_handler(_s3_event("processed/whatever.json"), None)
    assert result["processed_files"] == 0
    assert _list(client, "processed/") == []


def test_dedup_prevents_second_load(s3_setup):
    client, tx, _ = s3_setup
    raw_key = "raw/year=2025/month=01/day=15/dup.json"
    _put_raw(client, raw_key)

    first = tx.lambda_handler(_s3_event(raw_key), None)
    assert first["details"][0]["written"] == 2

    # Same fingerprints on a second run → all deduplicated away.
    second = tx.lambda_handler(_s3_event(raw_key), None)
    assert second["processed_files"] == 0 or second["details"][0]["duplicates"] == 2


# Ensure the env var is unset so other modules don't inherit it accidentally.
@pytest.fixture(autouse=True)
def _clean_env():
    yield
    os.environ.pop("S3_BUCKET_NAME", None)

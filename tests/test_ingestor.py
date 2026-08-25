"""
Tests for the ingestor's API + S3 paths (the previously-uncovered code):
the real Apify HTTP call (success and failure), write_to_s3 partitioning /
URL-safe keys, and the lambda_handler query x location fan-out.

The HTTP call is mocked at urllib level; S3 uses moto — no network, no AWS.
"""

import json
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import MagicMock

import boto3
import pytest

from lambdas.ingestor import handler as ing

moto = pytest.importorskip("moto")
from moto import mock_aws  # noqa: E402

BUCKET = "ingestor-bucket"
REGION = "us-east-1"


@contextmanager
def _fake_response(payload_bytes):
    resp = MagicMock()
    resp.read.return_value = payload_bytes
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    yield resp


# --------------------------------------------------------------------------- #
# fetch_jobs_from_apify
# --------------------------------------------------------------------------- #
def test_fetch_returns_mock_without_token(monkeypatch):
    monkeypatch.setattr(ing, "APIFY_TOKEN", "")
    jobs = ing.fetch_jobs_from_apify("Data Engineer", "India")
    assert len(jobs) == 2
    assert jobs[0]["source"] == "mock"


def test_fetch_calls_api_and_parses_response(monkeypatch):
    monkeypatch.setattr(ing, "APIFY_TOKEN", "secret-token")
    captured = {}

    def fake_urlopen(req, timeout=0):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode())
        return _fake_response(json.dumps([{"id": "real-1", "title": "DE"}]).encode())

    monkeypatch.setattr(ing.urllib.request, "urlopen", fake_urlopen)
    jobs = ing.fetch_jobs_from_apify("Data Engineer", "Remote")

    assert jobs == [{"id": "real-1", "title": "DE"}]
    assert "secret-token" in captured["url"]
    assert captured["body"]["searchQueries"] == ["Data Engineer"]
    assert captured["body"]["location"] == "Remote"


def test_fetch_returns_empty_on_http_error(monkeypatch):
    monkeypatch.setattr(ing, "APIFY_TOKEN", "secret-token")

    def boom(req, timeout=0):
        raise OSError("connection reset")

    monkeypatch.setattr(ing.urllib.request, "urlopen", boom)
    assert ing.fetch_jobs_from_apify("DE", "Remote") == []  # error is swallowed, not raised


# --------------------------------------------------------------------------- #
# write_to_s3
# --------------------------------------------------------------------------- #
@pytest.fixture
def s3_client(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "x")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "x")
    with mock_aws():
        client = boto3.client("s3", region_name=REGION)
        client.create_bucket(Bucket=BUCKET)
        monkeypatch.setattr(ing, "s3", client)
        monkeypatch.setattr(ing, "BUCKET_NAME", BUCKET)
        yield client


def test_write_to_s3_partitions_and_payload(s3_client):
    ts = datetime(2025, 3, 7, 6, 30, 15, tzinfo=UTC)
    records = [{"id": "1", "title": "DE"}]
    key = ing.write_to_s3(records, "Data Engineer", "Remote", ts)

    assert key == "raw/year=2025/month=03/day=07/Data_Engineer_Remote_063015.json"
    body = json.loads(s3_client.get_object(Bucket=BUCKET, Key=key)["Body"].read())
    assert body["count"] == 1
    assert body["query"] == "Data Engineer"
    assert body["records"] == records


def test_write_to_s3_key_is_url_safe(s3_client):
    ts = datetime(2025, 3, 7, 6, 30, 15, tzinfo=UTC)
    key = ing.write_to_s3([{"id": "1"}], "C++ / Data", "São Paulo", ts)
    # Special characters must be percent-encoded so the S3 key stays valid.
    assert " " not in key
    assert "/" not in key.split("day=07/")[1]  # no stray slash in the filename segment
    assert s3_client.get_object(Bucket=BUCKET, Key=key)["ResponseMetadata"]["HTTPStatusCode"] == 200


# --------------------------------------------------------------------------- #
# lambda_handler fan-out
# --------------------------------------------------------------------------- #
def test_lambda_handler_fans_out_over_queries_and_locations(s3_client, monkeypatch):
    monkeypatch.setattr(ing, "APIFY_TOKEN", "")  # mock-data mode
    monkeypatch.setattr(ing, "SEARCH_TERMS", ["Data Engineer", "ETL Developer"])
    monkeypatch.setattr(ing, "LOCATIONS", ["India", "Remote"])

    result = ing.lambda_handler({}, None)

    assert result["status"] == "success"
    # 2 queries x 2 locations x 2 mock records each = 8
    assert result["total_records"] == 8
    assert len(result["s3_keys"]) == 4  # one object per (query, location)
    objs = s3_client.list_objects_v2(Bucket=BUCKET, Prefix="raw/")["Contents"]
    assert len(objs) == 4


def test_lambda_handler_skips_empty_fetches(s3_client, monkeypatch):
    monkeypatch.setattr(ing, "SEARCH_TERMS", ["DE"])
    monkeypatch.setattr(ing, "LOCATIONS", ["Remote"])
    monkeypatch.setattr(ing, "fetch_jobs_from_apify", lambda q, loc: [])  # nothing returned

    result = ing.lambda_handler({}, None)
    assert result["total_records"] == 0
    assert result["s3_keys"] == []
    assert s3_client.list_objects_v2(Bucket=BUCKET, Prefix="raw/").get("Contents", []) == []

"""
Reliability scenarios: idempotency, transaction atomicity, the DQ gate's
"open no connection / write nothing" guarantee, Secrets Manager vs env config,
insights resilience, optional SNS, and logging/metric behaviour.

DB-backed cases use the live Postgres (skip if unreachable); the rest use mocks.
"""

import json
from unittest.mock import MagicMock

import boto3
import psycopg2
import pytest

from lambdas.loader import handler as loader_h

moto = pytest.importorskip("moto")
from moto import mock_aws  # noqa: E402

BUCKET = "reliability-bucket"
REGION = "us-east-1"


def _clean_records(n=5):
    return [
        {
            "job_id": f"job-{i}",
            "title": "Data Engineer",
            "company": "Acme",
            "location": "Remote",
            "salary_avg": 100000.0,
            "salary_min": 90000.0,
            "salary_max": 110000.0,
            "experience_level": "mid",
            "work_mode": "remote",
            "skills": ["python", "sql"],
            "skill_count": 2,
        }
        for i in range(n)
    ]


def _put_features(client, key, records):
    client.put_object(Bucket=BUCKET, Key=key, Body=json.dumps({"records": records}).encode())


def _event(key):
    return {"Records": [{"s3": {"bucket": {"name": BUCKET}, "object": {"key": key}}}]}


def _fact_count(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM fact_job_posting;")
        return cur.fetchone()[0]


# --------------------------------------------------------------------------- #
# 1. At-least-once redelivery → idempotent (no duplicate facts)
# --------------------------------------------------------------------------- #
def test_at_least_once_redelivery_is_idempotent(pg_conn, pg_env, monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "x")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "x")
    with mock_aws():
        s3 = boto3.client("s3", region_name=REGION)
        s3.create_bucket(Bucket=BUCKET)
        key = "features/year=2025/month=01/day=15/batch.json"
        _put_features(s3, key, _clean_records(5))
        monkeypatch.setattr(loader_h, "s3", s3)

        loader_h.lambda_handler(_event(key), None)
        first = _fact_count(pg_conn)
        loader_h.lambda_handler(_event(key), None)  # same object delivered again
        second = _fact_count(pg_conn)

    assert first == 5
    assert second == 5  # redelivery upserts, never duplicates


# --------------------------------------------------------------------------- #
# 2. Transaction atomicity: mid-batch failure commits nothing
# --------------------------------------------------------------------------- #
def test_upsert_is_atomic_on_mid_batch_failure(pg_conn):
    good = {"job_id": "ok", "title": "DE", "company": "Acme", "skills": []}
    bad = {"job_id": None, "title": "DE", "company": "Acme", "skills": []}  # NULL PK → error
    with pytest.raises(psycopg2.Error):
        loader_h.upsert_records(pg_conn, [good, bad])
    pg_conn.rollback()
    assert _fact_count(pg_conn) == 0  # the good row was NOT partially committed
    with pg_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM dim_company;")
        assert cur.fetchone()[0] == 0


# --------------------------------------------------------------------------- #
# 3. DQ gate rejects before opening a DB connection
# --------------------------------------------------------------------------- #
def test_dq_gate_blocks_and_opens_no_connection(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "x")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "x")
    connect_calls = MagicMock()
    monkeypatch.setattr(loader_h, "_connect", connect_calls)
    with mock_aws():
        s3 = boto3.client("s3", region_name=REGION)
        s3.create_bucket(Bucket=BUCKET)
        # 4 of 5 records invalid (missing title) → pass_rate 0.2 < 0.8
        recs = _clean_records(1) + [{"job_id": f"b{i}", "company": "X"} for i in range(4)]
        key = "features/bad.json"
        _put_features(s3, key, recs)
        monkeypatch.setattr(loader_h, "s3", s3)
        with pytest.raises(RuntimeError, match="quality gate"):
            loader_h.lambda_handler(_event(key), None)
    connect_calls.assert_not_called()  # never touched the database


# --------------------------------------------------------------------------- #
# 4. Config resolution: Secrets Manager path + env fallback
# --------------------------------------------------------------------------- #
def test_get_db_config_reads_secrets_manager(monkeypatch):
    with mock_aws():
        monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
        sm = boto3.client("secretsmanager", region_name=REGION)
        secret = {
            "host": "db.internal", "port": 5432, "dbname": "prod",
            "username": "svc", "password": "pw",
        }
        arn = sm.create_secret(Name="db", SecretString=json.dumps(secret))["ARN"]
        monkeypatch.setattr(loader_h, "DB_SECRET_ARN", arn)
        cfg = loader_h._get_db_config()
    assert cfg == {"host": "db.internal", "port": 5432, "dbname": "prod", "user": "svc", "password": "pw"}


def test_get_db_config_env_fallback(monkeypatch):
    monkeypatch.setattr(loader_h, "DB_SECRET_ARN", "")
    monkeypatch.setenv("DB_HOST", "h")
    monkeypatch.setenv("DB_USER", "u")
    monkeypatch.setenv("DB_PASSWORD", "p")
    monkeypatch.setenv("DB_NAME", "n")
    monkeypatch.setenv("DB_PORT", "5599")
    cfg = loader_h._get_db_config()
    assert cfg["host"] == "h" and cfg["user"] == "u" and cfg["port"] == 5599


def test_get_db_config_missing_env_raises(monkeypatch):
    monkeypatch.setattr(loader_h, "DB_SECRET_ARN", "")
    for var in ("DB_HOST", "DB_USER", "DB_PASSWORD"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(KeyError):
        loader_h._get_db_config()


def test_insights_secrets_manager_path(monkeypatch):
    from lambdas.insights import handler as insights_h

    with mock_aws():
        monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
        sm = boto3.client("secretsmanager", region_name=REGION)
        secret = {"host": "h2", "username": "u2", "password": "p2", "dbname": "d2"}
        arn = sm.create_secret(Name="db2", SecretString=json.dumps(secret))["ARN"]
        monkeypatch.setattr(insights_h, "DB_SECRET_ARN", arn)
        cfg = insights_h._get_db_config()
    assert cfg["user"] == "u2" and cfg["host"] == "h2" and cfg["port"] == 5432


# --------------------------------------------------------------------------- #
# 5. Insights resilience: empty DB and a missing MV must not crash
# --------------------------------------------------------------------------- #
def test_insights_on_empty_db_returns_structure(pg_conn):
    from lambdas.insights import handler as insights_h

    out = insights_h.generate_insights(pg_conn)
    assert out["top_skills"] == []
    assert out["rising_skills"] == []
    assert "median_salary_by_level" in out
    assert insights_h.build_headline(out) == "No new job-market activity today."


def test_insights_survives_missing_materialized_view(pg_conn):
    from lambdas.insights import handler as insights_h

    with pg_conn.cursor() as cur:
        cur.execute("DROP MATERIALIZED VIEW IF EXISTS mv_skill_demand_daily CASCADE;")
    pg_conn.commit()
    # Refresh of the dropped MV fails internally but is swallowed; selects still work.
    out = insights_h.generate_insights(pg_conn)
    assert "top_skills" in out
    # restore for other tests
    with pg_conn.cursor() as cur:
        with open(loader_h.__file__.replace("lambdas/loader/handler.py", "sql/02_reporting.sql")) as fh:
            cur.execute(fh.read())
    pg_conn.commit()


# --------------------------------------------------------------------------- #
# 6. SNS publish is optional
# --------------------------------------------------------------------------- #
def test_insights_no_sns_when_topic_unset(pg_env, pg_conn, monkeypatch):
    from lambdas.insights import handler as insights_h

    monkeypatch.setattr(insights_h, "SNS_TOPIC_ARN", "")
    fake_client = MagicMock()
    monkeypatch.setattr(insights_h.boto3, "client", fake_client)
    insights_h.lambda_handler({}, None)
    # boto3.client('sns') must never be requested when no topic is configured.
    assert all(call.args[0] != "sns" for call in fake_client.call_args_list)


def test_insights_publishes_once_when_topic_set(pg_env, pg_conn, monkeypatch):
    from lambdas.insights import handler as insights_h

    monkeypatch.setattr(insights_h, "SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:000:topic")
    sns = MagicMock()
    monkeypatch.setattr(insights_h.boto3, "client", lambda svc, *a, **k: sns)
    insights_h.lambda_handler({}, None)
    assert sns.publish.call_count == 1


# --------------------------------------------------------------------------- #
# 7. Connection is always closed, even when the inner work raises
# --------------------------------------------------------------------------- #
def test_insights_closes_connection_on_error(monkeypatch):
    from lambdas.insights import handler as insights_h

    conn = MagicMock()
    monkeypatch.setattr(insights_h, "_connect", lambda: conn)
    monkeypatch.setattr(insights_h, "generate_insights", lambda c: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        insights_h.lambda_handler({}, None)
    conn.close.assert_called_once()


# --------------------------------------------------------------------------- #
# 8. timed() context manager: metrics on success and on failure
# --------------------------------------------------------------------------- #
def test_timed_emits_duration_on_success(capsys):
    from lambdas.common.logging_utils import get_logger, timed

    log = get_logger("t")
    with timed(log, "stage_x"):
        pass
    out = capsys.readouterr().out
    assert "stage_x_duration_ms" in out


def test_timed_emits_error_and_reraises(capsys):
    from lambdas.common.logging_utils import get_logger, timed

    log = get_logger("t")
    with pytest.raises(ValueError):
        with timed(log, "stage_y"):
            raise ValueError("nope")
    out = capsys.readouterr().out
    assert "stage_y_errors" in out
    assert "stage_y_duration_ms" in out  # finally block still emits duration

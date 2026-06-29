"""Shared pytest fixtures and path setup."""

import os
import sys

import pytest

# Make `lambdas` importable as a package and `common` importable from within it.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "lambdas"))

SQL_DIR = os.path.join(ROOT, "sql")

# Connection params for the DB-backed tests. Defaults match the local dev
# Postgres; CI overrides PGPORT/PGPASSWORD via the workflow's postgres service.
PG_PARAMS = {
    "host": os.environ.get("PGHOST", "127.0.0.1"),
    "port": int(os.environ.get("PGPORT", "5433")),
    "user": os.environ.get("PGUSER", "postgres"),
    "password": os.environ.get("PGPASSWORD", ""),
    "dbname": os.environ.get("PGDATABASE", "jobmarket_test"),
}

WAREHOUSE_TABLES = [
    "bridge_job_skill",
    "trend_skill_weekly",
    "daily_insight",
    "fact_job_posting",
    "dim_company",
    "dim_skill",
]


def _load_schema(conn):
    with conn.cursor() as cur:
        for fname in ("01_schema.sql", "02_reporting.sql", "03_trends.sql"):
            with open(os.path.join(SQL_DIR, fname)) as fh:
                cur.execute(fh.read())
    conn.commit()


@pytest.fixture(scope="session")
def pg_available():
    """Connect once to confirm a live Postgres is reachable; skip the suite if not."""
    psycopg2 = pytest.importorskip("psycopg2")
    try:
        conn = psycopg2.connect(connect_timeout=5, **PG_PARAMS)
    except psycopg2.OperationalError as exc:
        pytest.skip(f"No live PostgreSQL for DB tests ({PG_PARAMS['host']}:{PG_PARAMS['port']}): {exc}")
    _load_schema(conn)
    conn.close()
    return PG_PARAMS


@pytest.fixture
def pg_conn(pg_available):
    """A clean connection with all warehouse tables truncated before the test."""
    import psycopg2

    conn = psycopg2.connect(connect_timeout=5, **PG_PARAMS)
    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE {', '.join(WAREHOUSE_TABLES)} RESTART IDENTITY CASCADE;")
    conn.commit()
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture
def pg_env(pg_available, monkeypatch):
    """Set the DB_* env vars the loader/insights handlers read (env-var path)."""
    monkeypatch.setenv("DB_SECRET_ARN", "")
    monkeypatch.setenv("DB_HOST", PG_PARAMS["host"])
    monkeypatch.setenv("DB_PORT", str(PG_PARAMS["port"]))
    monkeypatch.setenv("DB_NAME", PG_PARAMS["dbname"])
    monkeypatch.setenv("DB_USER", PG_PARAMS["user"])
    monkeypatch.setenv("DB_PASSWORD", PG_PARAMS["password"] or "x")
    return PG_PARAMS

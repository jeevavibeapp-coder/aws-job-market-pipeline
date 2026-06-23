"""
Tests for the PostgreSQL loader's pure logic.

We mock the psycopg2 connection/cursor so no real database is needed — this
verifies the upsert orchestration (companies cached, fact upserted, skills
linked) and the transaction boundary.
"""

from unittest.mock import MagicMock

from lambdas.loader.handler import _parse_ts, upsert_records


def _make_conn(returning_ids):
    """Build a mock connection whose cursor.fetchone() yields surrogate ids."""
    cur = MagicMock()
    cur.fetchone.side_effect = [(i,) for i in returning_ids]
    ctx = MagicMock()
    ctx.__enter__.return_value = cur
    ctx.__exit__.return_value = False
    conn = MagicMock()
    conn.cursor.return_value = ctx
    return conn, cur


def test_parse_ts_handles_z_suffix_and_none():
    assert _parse_ts(None) is None
    assert _parse_ts("not-a-date") is None
    parsed = _parse_ts("2025-01-15T06:00:00Z")
    assert parsed is not None and parsed.year == 2025


def test_upsert_single_record_with_skills():
    # ids returned in call order: company(10), skill python(20), skill sql(21)
    conn, cur = _make_conn([10, 20, 21])
    records = [
        {
            "job_id": "j-1",
            "title": "Data Engineer",
            "company": "Acme",
            "skills": ["python", "sql"],
            "skill_count": 2,
            "salary_avg": 90000.0,
            "experience_level": "mid",
            "work_mode": "remote",
        }
    ]

    written = upsert_records(conn, records)

    assert written == 1
    conn.commit.assert_called_once()
    # company upsert + fact upsert + 2 skill upserts + 2 bridge links = 6 execs
    assert cur.execute.call_count == 6


def test_company_is_cached_across_records():
    # Two jobs at the same company -> company upserted only once.
    conn, cur = _make_conn([10])  # single company id needed
    records = [
        {"job_id": "j-1", "company": "Acme", "title": "DE", "skills": []},
        {"job_id": "j-2", "company": "Acme", "title": "DE2", "skills": []},
    ]
    written = upsert_records(conn, records)

    assert written == 2
    # 1 company upsert + 2 fact upserts = 3 (no skills)
    assert cur.execute.call_count == 3


def test_missing_company_defaults_to_unknown():
    conn, cur = _make_conn([99])
    written = upsert_records(conn, [{"job_id": "j-1", "title": "DE", "skills": []}])
    assert written == 1
    first_call_args = cur.execute.call_args_list[0][0]
    assert first_call_args[1] == ("Unknown",)

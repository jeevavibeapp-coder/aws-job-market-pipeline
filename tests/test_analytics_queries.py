"""
Live-PostgreSQL correctness sweep for the serving layer.

Seeds a deterministic dataset, then:
  - runs EVERY statement in sql/04_analytics_queries.sql (must execute cleanly),
  - asserts exact expected values for the key aggregates (top skills, median
    salary, remote share, skill co-occurrence),
  - exercises the trend snapshot function and the v_skill_momentum window view,
  - refreshes both reporting materialized views.
Skips automatically when no Postgres is reachable.
"""

import os
import re

from tests.conftest import ROOT

SQL_FILE = os.path.join(ROOT, "sql", "04_analytics_queries.sql")


def _statements(path):
    """Split a .sql file into executable statements, dropping comments first.

    Comments are stripped BEFORE splitting on ';' because a comment line may
    itself contain a semicolon.
    """
    raw = open(path).read()
    no_comments = "\n".join(re.sub(r"--.*$", "", ln) for ln in raw.splitlines())
    for chunk in no_comments.split(";"):
        body = chunk.strip()
        if body:
            yield body + ";"


def _seed(conn):
    """Insert a known dataset. Returns nothing; commits."""
    cur = conn.cursor()
    # companies
    cur.execute(
        "INSERT INTO dim_company (company_name) VALUES ('Acme'),('DataFlow'),('BigCo') "
        "RETURNING company_id, company_name;"
    )
    comp = {name: cid for cid, name in cur.fetchall()}
    # skills
    cur.execute(
        "INSERT INTO dim_skill (skill_name) VALUES ('python'),('sql'),('aws'),('spark') "
        "RETURNING skill_id, skill_name;"
    )
    skill = {name: sid for sid, name in cur.fetchall()}

    # facts (all load_date = today)
    facts = [
        ("j1", "Senior DE", comp["Acme"], "senior", "remote", 150000, ["python", "sql", "aws"]),
        ("j2", "DE", comp["Acme"], "mid", "hybrid", 120000, ["python", "spark"]),
        ("j3", "Jr DE", comp["DataFlow"], "entry", "onsite", 80000, ["sql"]),
        ("j4", "Senior DE", comp["BigCo"], "senior", "remote", 160000, ["python", "aws"]),
    ]
    for jid, title, cid, level, mode, sal, skills in facts:
        cur.execute(
            "INSERT INTO fact_job_posting "
            "(job_id, source, title, company_id, location, salary_avg, experience_level, "
            " work_mode, skill_count, load_date) "
            "VALUES (%s,'test',%s,%s,'Remote',%s,%s,%s,%s,CURRENT_DATE);",
            (jid, title, cid, sal, level, mode, len(skills)),
        )
        for s in skills:
            cur.execute(
                "INSERT INTO bridge_job_skill (job_id, skill_id) VALUES (%s,%s);", (jid, skill[s])
            )
    conn.commit()


def test_all_analytics_queries_execute(pg_conn):
    _seed(pg_conn)
    cur = pg_conn.cursor()
    executed = 0
    for stmt in _statements(SQL_FILE):
        cur.execute(stmt)
        if cur.description:  # SELECT → drain rows to ensure full execution
            cur.fetchall()
        executed += 1
    pg_conn.commit()
    assert executed == 8, f"expected 8 analytics statements, ran {executed}"


def test_top_skills_counts(pg_conn):
    _seed(pg_conn)
    cur = pg_conn.cursor()
    cur.execute(
        "SELECT s.skill_name, COUNT(*) FROM fact_job_posting f "
        "JOIN bridge_job_skill b USING(job_id) JOIN dim_skill s USING(skill_id) "
        "GROUP BY 1 ORDER BY 2 DESC, 1;"
    )
    rows = dict(cur.fetchall())
    assert rows["python"] == 3
    assert rows["sql"] == 2
    assert rows["aws"] == 2
    assert rows["spark"] == 1


def test_median_salary_by_level(pg_conn):
    _seed(pg_conn)
    cur = pg_conn.cursor()
    cur.execute(
        "SELECT experience_level, "
        "PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary_avg) "
        "FROM fact_job_posting WHERE salary_avg IS NOT NULL GROUP BY 1;"
    )
    med = {lvl: float(v) for lvl, v in cur.fetchall()}
    assert med["senior"] == 155000.0  # median of 150k, 160k
    assert med["mid"] == 120000.0
    assert med["entry"] == 80000.0


def test_remote_share(pg_conn):
    _seed(pg_conn)
    cur = pg_conn.cursor()
    cur.execute(
        "SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE work_mode='remote') / NULLIF(COUNT(*),0), 1) "
        "FROM fact_job_posting WHERE load_date = CURRENT_DATE;"
    )
    assert float(cur.fetchone()[0]) == 50.0  # j1,j4 remote of 4


def test_skill_cooccurrence_self_join(pg_conn):
    _seed(pg_conn)
    cur = pg_conn.cursor()
    # query #5 from the cookbook
    cur.execute(
        "SELECT a.skill_name, b2.skill_name, COUNT(*) "
        "FROM bridge_job_skill x "
        "JOIN bridge_job_skill y ON x.job_id = y.job_id AND x.skill_id < y.skill_id "
        "JOIN dim_skill a ON a.skill_id = x.skill_id "
        "JOIN dim_skill b2 ON b2.skill_id = y.skill_id "
        "GROUP BY 1,2 ORDER BY 3 DESC;"
    )
    pairs = {frozenset((a, b)): c for a, b, c in cur.fetchall()}
    # python+aws appear together in j1 and j4 → 2; python+sql only j1 → 1
    assert pairs[frozenset(("python", "aws"))] == 2
    assert pairs[frozenset(("python", "sql"))] == 1
    assert pairs[frozenset(("sql", "aws"))] == 1


def test_divide_by_zero_guard_on_empty(pg_conn):
    # No data → NULLIF guard must yield NULL, not raise.
    cur = pg_conn.cursor()
    cur.execute(
        "SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE work_mode='remote') / NULLIF(COUNT(*),0), 1) "
        "FROM fact_job_posting;"
    )
    assert cur.fetchone()[0] is None


def test_trend_snapshot_and_momentum(pg_conn):
    _seed(pg_conn)
    cur = pg_conn.cursor()
    # seed a prior-week trend row for python (count=1), then snapshot this week.
    cur.execute(
        "INSERT INTO trend_skill_weekly (week_start, skill_name, posting_count, avg_salary) "
        "VALUES (date_trunc('week', CURRENT_DATE)::date - 7, 'python', 1, 100000);"
    )
    cur.execute("SELECT snapshot_skill_weekly();")
    pg_conn.commit()

    cur.execute(
        "SELECT posting_count, prev_count, wow_change "
        "FROM v_skill_momentum "
        "WHERE skill_name='python' AND week_start = date_trunc('week', CURRENT_DATE)::date;"
    )
    cur_count, prev_count, wow = cur.fetchone()
    assert cur_count == 3       # python in j1,j2,j4 this week
    assert prev_count == 1      # from the manual prior-week row
    assert wow == 2             # LAG() window delta


def test_materialized_views_refresh_first_run_populates(pg_conn):
    """The insights refresh helper must populate MVs even on their first-ever
    refresh, when CONCURRENTLY is not yet allowed (created WITH NO DATA)."""
    from lambdas.insights.handler import _refresh_materialized_views

    _seed(pg_conn)
    # First refresh: CONCURRENTLY is impossible (unpopulated) → must fall back.
    _refresh_materialized_views(pg_conn)
    cur = pg_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM mv_skill_demand_daily;")
    assert cur.fetchone()[0] == 4  # python, sql, aws, spark for today
    cur.execute("SELECT median_salary FROM mv_salary_by_level WHERE experience_level='senior';")
    assert float(cur.fetchone()[0]) == 155000.0

    # Second refresh now succeeds CONCURRENTLY (already populated) — no error.
    _refresh_materialized_views(pg_conn)
    cur.execute("SELECT COUNT(*) FROM mv_skill_demand_daily;")
    assert cur.fetchone()[0] == 4


def test_top_hiring_companies_view(pg_conn):
    _seed(pg_conn)
    cur = pg_conn.cursor()
    cur.execute("SELECT company_name, open_postings FROM v_top_hiring_companies ORDER BY 2 DESC;")
    rows = dict(cur.fetchall())
    assert rows["Acme"] == 2  # j1, j2
    assert rows["DataFlow"] == 1
    assert rows["BigCo"] == 1

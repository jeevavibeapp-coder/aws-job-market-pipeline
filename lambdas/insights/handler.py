"""
Lambda: Insights Generator
Triggered by: EventBridge (daily, after the load window)

Refreshes the reporting tables / trend snapshots in PostgreSQL and derives
natural-language insights (top skills, fastest-rising skills, salary deltas,
remote-work share). Results are written to the `daily_insight` table and
optionally published to an SNS topic so they land in email / Slack.
"""

import json
import os
import sys
from datetime import UTC, datetime

import boto3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.logging_utils import emit_metric, get_logger, timed  # noqa: E402

logger = get_logger("insights")

DB_SECRET_ARN = os.environ.get("DB_SECRET_ARN", "")
SNS_TOPIC_ARN = os.environ.get("INSIGHTS_SNS_TOPIC_ARN", "")


def _get_db_config() -> dict:
    if DB_SECRET_ARN:
        cfg = json.loads(
            boto3.client("secretsmanager").get_secret_value(SecretId=DB_SECRET_ARN)["SecretString"]
        )
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
    import psycopg2

    return psycopg2.connect(connect_timeout=10, **_get_db_config())


# Reporting materialized views refreshed each run.
MATERIALIZED_VIEWS = ["mv_skill_demand_daily", "mv_salary_by_level"]


def _refresh_materialized_views(conn) -> None:
    """
    Refresh each reporting MV, preferring CONCURRENTLY (non-blocking for readers).

    A materialized view created WITH NO DATA has never been populated, and
    Postgres rejects CONCURRENTLY on an unpopulated view. So on the first-ever
    run we fall back to a plain (blocking) REFRESH, which populates it; every
    subsequent run then uses CONCURRENTLY.
    """
    for mv in MATERIALIZED_VIEWS:
        try:
            with conn.cursor() as cur:
                cur.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {mv};")
            conn.commit()
        except Exception as exc:  # noqa: BLE001 - first run / not yet populated
            conn.rollback()
            logger.warning(
                "Concurrent refresh failed; retrying plain refresh",
                extra={"ctx": {"mv": mv, "error": str(exc)}},
            )
            try:
                with conn.cursor() as cur:
                    cur.execute(f"REFRESH MATERIALIZED VIEW {mv};")
                conn.commit()
            except Exception as exc2:  # noqa: BLE001 - e.g. no underlying data yet
                conn.rollback()
                logger.warning("Refresh skipped", extra={"ctx": {"mv": mv, "error": str(exc2)}})

# Analytical queries that feed the generated insights.
TOP_SKILLS_SQL = """
SELECT s.skill_name, COUNT(*) AS demand
FROM fact_job_posting f
JOIN bridge_job_skill b ON b.job_id = f.job_id
JOIN dim_skill s ON s.skill_id = b.skill_id
WHERE f.load_date = CURRENT_DATE
GROUP BY s.skill_name
ORDER BY demand DESC
LIMIT 5;
"""

RISING_SKILLS_SQL = """
WITH this_week AS (
    SELECT s.skill_name, COUNT(*) AS c
    FROM fact_job_posting f
    JOIN bridge_job_skill b ON b.job_id = f.job_id
    JOIN dim_skill s ON s.skill_id = b.skill_id
    WHERE f.load_date >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY s.skill_name
),
prior_week AS (
    SELECT s.skill_name, COUNT(*) AS c
    FROM fact_job_posting f
    JOIN bridge_job_skill b ON b.job_id = f.job_id
    JOIN dim_skill s ON s.skill_id = b.skill_id
    WHERE f.load_date >= CURRENT_DATE - INTERVAL '14 days'
      AND f.load_date <  CURRENT_DATE - INTERVAL '7 days'
    GROUP BY s.skill_name
)
SELECT t.skill_name,
       t.c AS current_count,
       COALESCE(p.c, 0) AS prior_count,
       ROUND(100.0 * (t.c - COALESCE(p.c, 0)) / GREATEST(COALESCE(p.c, 0), 1), 1) AS pct_change
FROM this_week t
LEFT JOIN prior_week p ON p.skill_name = t.skill_name
WHERE t.c >= 3
ORDER BY pct_change DESC
LIMIT 5;
"""

REMOTE_SHARE_SQL = """
SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE work_mode = 'remote') / NULLIF(COUNT(*), 0), 1)
FROM fact_job_posting
WHERE load_date = CURRENT_DATE;
"""

MEDIAN_SALARY_SQL = """
SELECT experience_level,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary_avg)::numeric, 0) AS median_salary
FROM fact_job_posting
WHERE load_date = CURRENT_DATE AND salary_avg IS NOT NULL
GROUP BY experience_level
ORDER BY median_salary DESC NULLS LAST;
"""

STORE_INSIGHT_SQL = """
INSERT INTO daily_insight (insight_date, payload, headline)
VALUES (CURRENT_DATE, %s, %s)
ON CONFLICT (insight_date) DO UPDATE
SET payload = EXCLUDED.payload, headline = EXCLUDED.headline, generated_at = now();
"""


def generate_insights(conn) -> dict:
    out: dict = {"generated_at": datetime.now(UTC).isoformat()}
    _refresh_materialized_views(conn)
    with conn.cursor() as cur:
        cur.execute(TOP_SKILLS_SQL)
        out["top_skills"] = [{"skill": r[0], "demand": r[1]} for r in cur.fetchall()]

        cur.execute(RISING_SKILLS_SQL)
        out["rising_skills"] = [
            {"skill": r[0], "current": r[1], "prior": r[2], "pct_change": float(r[3])} for r in cur.fetchall()
        ]

        cur.execute(REMOTE_SHARE_SQL)
        row = cur.fetchone()
        out["remote_share_pct"] = float(row[0]) if row and row[0] is not None else None

        cur.execute(MEDIAN_SALARY_SQL)
        out["median_salary_by_level"] = [
            {"level": r[0], "median_salary": float(r[1]) if r[1] is not None else None}
            for r in cur.fetchall()
        ]

    return out


def build_headline(insights: dict) -> str:
    parts = []
    if insights.get("top_skills"):
        top = insights["top_skills"][0]
        parts.append(f"Top skill today: {top['skill']} ({top['demand']} postings)")
    if insights.get("rising_skills"):
        rise = insights["rising_skills"][0]
        if rise["pct_change"] > 0:
            parts.append(f"Fastest riser: {rise['skill']} (+{rise['pct_change']}% WoW)")
    if insights.get("remote_share_pct") is not None:
        parts.append(f"Remote share: {insights['remote_share_pct']}%")
    return " | ".join(parts) or "No new job-market activity today."


def lambda_handler(event, context):
    with timed(logger, "insights"):
        conn = _connect()
        try:
            insights = generate_insights(conn)
            headline = build_headline(insights)
            with conn.cursor() as cur:
                cur.execute(STORE_INSIGHT_SQL, (json.dumps(insights, default=str), headline))
            conn.commit()
        finally:
            conn.close()

    logger.info("Insights generated", extra={"ctx": {"headline": headline}})
    emit_metric("insights_generated", 1, "Count")

    if SNS_TOPIC_ARN:
        boto3.client("sns").publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="Daily Job-Market Insights",
            Message=f"{headline}\n\n{json.dumps(insights, indent=2, default=str)}",
        )

    return {"status": "success", "headline": headline, "insights": insights}

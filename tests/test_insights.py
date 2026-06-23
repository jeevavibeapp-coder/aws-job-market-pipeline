"""Unit tests for the insights headline builder (pure logic, no DB)."""

from lambdas.insights.handler import build_headline


def test_headline_with_full_data():
    insights = {
        "top_skills": [{"skill": "python", "demand": 42}],
        "rising_skills": [{"skill": "dbt", "pct_change": 35.0}],
        "remote_share_pct": 61.5,
    }
    headline = build_headline(insights)
    assert "python" in headline
    assert "42" in headline
    assert "dbt" in headline
    assert "61.5%" in headline


def test_headline_ignores_negative_riser():
    insights = {
        "top_skills": [{"skill": "sql", "demand": 10}],
        "rising_skills": [{"skill": "java", "pct_change": -12.0}],
        "remote_share_pct": None,
    }
    headline = build_headline(insights)
    assert "sql" in headline
    assert "java" not in headline  # declining skill not surfaced


def test_headline_empty_payload():
    assert build_headline({}) == "No new job-market activity today."

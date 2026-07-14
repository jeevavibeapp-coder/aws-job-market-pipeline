"""Unit tests for the core experience-matching rule — the heart of the AI filter."""
from app.services.ai_filter import AIJobFilter

f = AIJobFilter()


def test_accept_within_tolerance():
    # User 2.5 yrs, job needs 2 -> accept
    r = f.check_experience_match(job_exp_min=2, job_exp_max=None, user_exp=2.5, tolerance=1.0)
    assert r.status == "accept"


def test_accept_at_tolerance_boundary():
    # User 2.5 yrs, job needs 3, tolerance 1.0 -> 3 <= 3.5 accept
    r = f.check_experience_match(3, None, 2.5, tolerance=1.0)
    assert r.status == "accept"


def test_warning_zone():
    # User 2.5, job needs 4, tolerance 1.0 -> 4 <= 4.5 warning
    r = f.check_experience_match(4, None, 2.5, tolerance=1.0)
    assert r.status == "warning"


def test_reject_too_senior():
    # User 2.5, job needs 5 -> 5 > 4.5 reject
    r = f.check_experience_match(5, None, 2.5, tolerance=1.0)
    assert r.status == "reject"


def test_reject_seven_plus():
    r = f.check_experience_match(7, None, 2.5, tolerance=1.0)
    assert r.status == "reject"


def test_no_requirement_accepts():
    r = f.check_experience_match(None, None, 2.5, tolerance=1.0)
    assert r.status == "accept"


def test_skill_match_scoring():
    score, matched = f._keyword_skill_match(["Python", "SQL", "AWS", "Snowflake"], ["python", "aws"])
    assert matched == ["Python", "AWS"]
    assert score == 50.0

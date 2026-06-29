"""
Regression tests for defects found during multi-scenario testing.

Each test pins the corrected behaviour so the bug cannot silently return.
Covers transformer salary/date parsing, the docker skill regex, the loader's
whitespace-company defaulting, and validation type/range edge cases.
"""

from unittest.mock import MagicMock

from lambdas.common.validation import _coercible, validate_record
from lambdas.feature_extractor.handler import extract_skills
from lambdas.loader.handler import upsert_records
from lambdas.transformer.handler import _parse_date, _parse_salary


class TestSalaryParsing:
    def test_global_k_replace_no_longer_corrupts_text(self):
        # "week" must not inject a phantom 000 token (old bug → salary 0.0).
        r = _parse_salary("80k for 40hrs/week")
        assert r["salary_min"] == 80000.0
        assert r["salary_max"] == 80000.0

    def test_million_suffix(self):
        r = _parse_salary("$1.2M")
        assert r["salary_min"] == 1_200_000.0
        assert r["salary_max"] == 1_200_000.0

    def test_k_suffix_not_mangled_when_adjacent_digits(self):
        # "10k000" should be 10k = 10000, not 10,000,000.
        assert _parse_salary("10k")["salary_min"] == 10_000.0

    def test_range_with_symbols(self):
        r = _parse_salary("$80,000 - $100,000")
        assert (r["salary_min"], r["salary_max"], r["salary_avg"]) == (80000.0, 100000.0, 90000.0)

    def test_range_without_symbols(self):
        r = _parse_salary("80000-100000")
        assert r["salary_min"] == 80000.0 and r["salary_max"] == 100000.0

    def test_negative_salary_dropped(self):
        # Unary minus is not a valid salary; should not yield a positive figure.
        assert _parse_salary("-100000") == {"salary_min": None, "salary_max": None, "salary_avg": None}

    def test_bare_small_numbers_ignored(self):
        # "5+ years", "40 hrs" must not be read as salaries.
        assert _parse_salary("5+ years, 40 hrs/week")["salary_min"] is None

    def test_non_salary_text(self):
        assert _parse_salary("Competitive")["salary_avg"] is None
        assert _parse_salary("")["salary_min"] is None

    def test_k_lowercase_and_uppercase(self):
        assert _parse_salary("$50k")["salary_min"] == 50000.0
        assert _parse_salary("$50K")["salary_min"] == 50000.0


class TestDateParsing:
    def test_iso_with_z(self):
        out = _parse_date("2025-01-15T06:00:00Z")
        assert out.startswith("2025-01-15T06:00:00")
        assert "Z" not in out  # normalised to an offset, actually parsed

    def test_iso_with_offset(self):
        out = _parse_date("2025-01-15T06:00:00+05:30")
        assert out.startswith("2025-01-15T06:00:00")
        assert "+05:30" in out

    def test_date_only(self):
        assert _parse_date("2025-01-15") == "2025-01-15T00:00:00"

    def test_epoch(self):
        out = _parse_date(1736922600)
        assert out.startswith("2025-01-")

    def test_garbage_passthrough(self):
        assert _parse_date("yesterday") == "yesterday"

    def test_none(self):
        assert _parse_date(None) is None


class TestDockerSkillRegex:
    def test_generic_container_no_longer_matches_docker(self):
        assert "docker" not in extract_skills("we ship goods in a shipping container")

    def test_docker_word_still_matches(self):
        assert "docker" in extract_skills("experience with Docker and Kubernetes")

    def test_containerization_matches(self):
        assert "docker" in extract_skills("containerization and orchestration")


class TestValidationEdges:
    def test_bool_salary_rejected(self):
        assert _coercible(True, float) is False
        problems = validate_record({"job_id": "1", "title": "DE", "company": "X", "salary_min": True})
        assert any("salary_min" in p for p in problems)

    def test_salary_avg_now_bounds_checked(self):
        problems = validate_record({"job_id": "1", "title": "DE", "company": "X", "salary_avg": 99_000_000})
        assert any("salary_avg" in p and "bounds" in p for p in problems)


class TestLoaderWhitespaceCompany:
    def test_whitespace_company_becomes_unknown(self):
        cur = MagicMock()
        cur.fetchone.return_value = (1,)
        ctx = MagicMock()
        ctx.__enter__.return_value = cur
        conn = MagicMock()
        conn.cursor.return_value = ctx

        upsert_records(conn, [{"job_id": "j-1", "title": "DE", "company": "   ", "skills": []}])

        # First execute call is the company upsert; arg must be "Unknown", not "".
        company_arg = cur.execute.call_args_list[0][0][1]
        assert company_arg == ("Unknown",)

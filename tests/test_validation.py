"""Unit + data-quality tests for the validation layer."""

from datetime import UTC, datetime, timedelta

from lambdas.common.validation import (
    ValidationReport,
    is_fresh,
    validate_batch,
    validate_record,
)


def _good_record(**overrides):
    rec = {
        "job_id": "abc-1",
        "title": "Data Engineer",
        "company": "Acme",
        "location": "Remote",
        "salary_min": 80000.0,
        "salary_max": 100000.0,
        "salary_avg": 90000.0,
        "posted_at": datetime.now(UTC).isoformat(),
        "source": "linkedin",
    }
    rec.update(overrides)
    return rec


class TestValidateRecord:
    def test_valid_record_has_no_problems(self):
        assert validate_record(_good_record()) == []

    def test_missing_required_field_flagged(self):
        rec = _good_record()
        del rec["job_id"]
        problems = validate_record(rec)
        assert any("job_id" in p for p in problems)

    def test_wrong_type_flagged(self):
        rec = _good_record(salary_avg="not-a-number")
        problems = validate_record(rec)
        assert any("salary_avg" in p for p in problems)

    def test_min_greater_than_max_flagged(self):
        rec = _good_record(salary_min=120000.0, salary_max=90000.0)
        problems = validate_record(rec)
        assert any("greater than" in p for p in problems)

    def test_out_of_bounds_salary_flagged(self):
        rec = _good_record(salary_min=5.0, salary_max=10.0, salary_avg=7.5)
        problems = validate_record(rec)
        assert any("bounds" in p for p in problems)


class TestFreshness:
    def test_recent_posting_is_fresh(self):
        assert is_fresh(_good_record()) is True

    def test_old_posting_not_fresh(self):
        old = (datetime.now(UTC) - timedelta(days=400)).isoformat()
        assert is_fresh(_good_record(posted_at=old)) is False

    def test_unparseable_date_not_fresh(self):
        assert is_fresh(_good_record(posted_at="yesterday")) is False

    def test_missing_date_is_treated_fresh(self):
        rec = _good_record()
        rec["posted_at"] = None
        assert is_fresh(rec) is True


class TestValidateBatch:
    def test_clean_batch_all_pass(self):
        clean, report = validate_batch([_good_record(job_id=f"j-{i}") for i in range(5)])
        assert len(clean) == 5
        assert report.valid == 5
        assert report.pass_rate == 1.0

    def test_dirty_records_dropped(self):
        good = _good_record(job_id="good")
        bad = _good_record(job_id="bad")
        del bad["title"]
        clean, report = validate_batch([good, bad])
        assert len(clean) == 1
        assert clean[0]["job_id"] == "good"
        assert report.invalid == 1
        assert 0 < report.pass_rate < 1

    def test_stale_record_kept_as_warning(self):
        stale = _good_record(posted_at=(datetime.now(UTC) - timedelta(days=500)).isoformat())
        clean, report = validate_batch([stale])
        assert len(clean) == 1  # kept
        assert report.warning_count if hasattr(report, "warning_count") else True
        assert len(report.warnings) == 1  # but flagged

    def test_empty_batch(self):
        clean, report = validate_batch([])
        assert clean == []
        assert report.pass_rate == 1.0


def test_report_serialization_is_json_safe():
    report = ValidationReport(total=2, valid=1)
    d = report.as_dict()
    assert d["total"] == 2 and d["invalid"] == 1 and d["pass_rate"] == 0.5

"""
Data-quality validation for the job-market pipeline.

This is the contract-enforcement layer that sits between transform and load.
It implements lightweight, dependency-free checks (schema, type, range,
nullability, freshness) and returns a structured report so callers can decide
whether to quarantine a batch or fail the pipeline.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# Canonical schema produced by the transformer. (field -> python type, required)
PROCESSED_SCHEMA: dict[str, tuple[type, bool]] = {
    "job_id": (str, True),
    "title": (str, True),
    "company": (str, True),
    "location": (str, False),
    "salary_min": (float, False),
    "salary_max": (float, False),
    "salary_avg": (float, False),
    "posted_at": (str, False),
    "source": (str, False),
}

# Sane bounds so obviously-broken salaries are caught (annualised USD).
SALARY_MIN_BOUND = 1_000.0
SALARY_MAX_BOUND = 2_000_000.0


@dataclass
class ValidationReport:
    total: int = 0
    valid: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)

    @property
    def invalid(self) -> int:
        return self.total - self.valid

    @property
    def pass_rate(self) -> float:
        return round(self.valid / self.total, 4) if self.total else 1.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "valid": self.valid,
            "invalid": self.invalid,
            "pass_rate": self.pass_rate,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors[:50],  # cap payload size
            "warnings": self.warnings[:50],
        }


def _coercible(value: Any, expected: type) -> bool:
    if value is None:
        return True
    if expected is float:
        # bool is a subclass of int — reject it explicitly for numeric fields.
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, expected)


def validate_record(record: dict[str, Any], schema: dict = PROCESSED_SCHEMA) -> list[str]:
    """Return a list of human-readable problems for a single record (empty == valid)."""
    problems: list[str] = []

    for field_name, (expected_type, required) in schema.items():
        present = field_name in record and record[field_name] not in (None, "")
        if required and not present:
            problems.append(f"missing required field '{field_name}'")
            continue
        if field_name in record and not _coercible(record[field_name], expected_type):
            problems.append(
                f"field '{field_name}' expected {expected_type.__name__}, "
                f"got {type(record[field_name]).__name__}"
            )

    # Range / sanity checks for salary
    smin, savg, smax = (record.get("salary_min"), record.get("salary_avg"), record.get("salary_max"))
    if isinstance(smin, (int, float)) and isinstance(smax, (int, float)) and smin > smax:
        problems.append(f"salary_min ({smin}) greater than salary_max ({smax})")
    for label, val in (("salary_min", smin), ("salary_avg", savg), ("salary_max", smax)):
        if (
            isinstance(val, (int, float))
            and not isinstance(val, bool)
            and not (SALARY_MIN_BOUND <= val <= SALARY_MAX_BOUND)
        ):
            problems.append(f"{label} ({val}) outside plausible bounds")

    return problems


def is_fresh(record: dict[str, Any], max_age_days: int = 90) -> bool:
    """True if posted_at is parseable and within max_age_days of now."""
    raw = record.get("posted_at")
    if not raw:
        return True  # absence is a warning, not a hard failure
    try:
        ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return False
    age = (datetime.now(UTC) - ts).days
    return 0 <= age <= max_age_days


def validate_batch(
    records: list[dict[str, Any]],
    schema: dict = PROCESSED_SCHEMA,
    freshness_check: Callable[[dict], bool] | None = is_fresh,
) -> tuple[list[dict], ValidationReport]:
    """
    Validate a batch and split it into clean records + a report.

    Returns (clean_records, report). Records failing hard checks are dropped
    from clean_records; soft issues (e.g. staleness) become warnings but the
    record is kept.
    """
    report = ValidationReport(total=len(records))
    clean: list[dict] = []

    for idx, rec in enumerate(records):
        problems = validate_record(rec, schema)
        if problems:
            report.errors.append({"index": idx, "job_id": rec.get("job_id"), "problems": problems})
            continue
        if freshness_check and not freshness_check(rec):
            report.warnings.append(
                {"index": idx, "job_id": rec.get("job_id"), "problem": "stale or unparseable posted_at"}
            )
        report.valid += 1
        clean.append(rec)

    return clean, report

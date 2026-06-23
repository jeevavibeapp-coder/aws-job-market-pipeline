from datetime import datetime, timezone


def compute_competition_score(applicant_count: int | None, posted_at: datetime | None) -> int:
    """Returns 1 (low competition) to 100 (high competition)."""
    base = 50

    if applicant_count is not None:
        if applicant_count == 0:
            base = 5
        elif applicant_count < 10:
            base = 15
        elif applicant_count < 25:
            base = 30
        elif applicant_count < 100:
            base = 55
        elif applicant_count < 300:
            base = 75
        else:
            base = 90

    if posted_at:
        age_hours = (datetime.now(timezone.utc) - posted_at).total_seconds() / 3600
        if age_hours < 6:
            base = max(5, base - 20)
        elif age_hours < 24:
            base = max(10, base - 10)
        elif age_hours > 168:
            base = min(95, base + 15)

    return max(1, min(100, base))


def experience_overlap_score(job_min: float | None, job_max: float | None, user_exp: float) -> float:
    if job_min is None:
        return 80.0
    if job_max is not None and user_exp > job_max * 1.5:
        return 60.0
    gap = job_min - user_exp
    if gap <= 0:
        return 100.0
    if gap <= 1:
        return 85.0
    if gap <= 2:
        return 60.0
    return max(0, 60 - gap * 15)

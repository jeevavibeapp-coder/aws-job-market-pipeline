"""Freshness engine — filter and score jobs by how recently they were posted."""
from __future__ import annotations
from datetime import datetime, timezone

# Preset freshness windows exposed in the UI (hours).
FRESHNESS_WINDOWS = {
    "24h": 24,
    "3d": 72,
    "7d": 168,
    "14d": 336,
}
DEFAULT_WINDOW_HOURS = 24


def age_hours(posted_at: datetime | None) -> float | None:
    if posted_at is None:
        return None
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - posted_at).total_seconds() / 3600


def is_fresh(posted_at: datetime | None, within_hours: int = DEFAULT_WINDOW_HOURS) -> bool:
    """Jobs with no posting date are treated as fresh (kept, not discarded)."""
    hrs = age_hours(posted_at)
    if hrs is None:
        return True
    return hrs <= within_hours


def freshness_score(posted_at: datetime | None) -> int:
    """0-100 where 100 = just posted. Unknown dates get a neutral 50."""
    hrs = age_hours(posted_at)
    if hrs is None:
        return 50
    if hrs <= 6:
        return 100
    if hrs <= 24:
        return 90
    if hrs <= 72:
        return 70
    if hrs <= 168:
        return 50
    if hrs <= 336:
        return 30
    return 10


def freshness_label(posted_at: datetime | None) -> str:
    hrs = age_hours(posted_at)
    if hrs is None:
        return "Unknown"
    if hrs < 1:
        return "Just posted"
    if hrs < 24:
        return f"{int(hrs)}h ago"
    days = int(hrs // 24)
    if days == 1:
        return "Yesterday"
    if days < 7:
        return f"{days}d ago"
    return f"{days // 7}w ago"

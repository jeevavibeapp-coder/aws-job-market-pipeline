from __future__ import annotations
import re
from difflib import SequenceMatcher
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.job import Job


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def is_duplicate(job_a, job_b, title_threshold: float = 0.85, desc_threshold: float = 0.75) -> bool:
    company_a = getattr(job_a, "_company_name", "").lower()
    company_b = getattr(job_b, "_company_name", "").lower()
    if company_a and company_b and company_a != company_b:
        return False

    title_sim = _similarity(_normalize(job_a.title), _normalize(job_b.title))
    if title_sim < title_threshold:
        return False

    desc_a = (job_a.description or "")[:500]
    desc_b = (job_b.description or "")[:500]
    desc_sim = _similarity(_normalize(desc_a), _normalize(desc_b))

    return desc_sim >= desc_threshold


def deduplicate(jobs: list, source_priority: dict) -> list:
    """Keep highest-priority source when duplicates found."""
    kept: list = []
    for job in jobs:
        is_dup = False
        for i, existing in enumerate(kept):
            if is_duplicate(job, existing):
                job_prio = source_priority.get(job.source, 99)
                existing_prio = source_priority.get(existing.source, 99)
                if job_prio < existing_prio:
                    kept[i] = job
                is_dup = True
                break
        if not is_dup:
            kept.append(job)
    return kept

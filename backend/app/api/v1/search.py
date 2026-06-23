import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from datetime import datetime, timedelta, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.job import Job
from app.models.resume_profile import ResumeProfile
from app.schemas.search import SearchRequest, NaturalSearchRequest, SearchResult
from app.services.ai_filter import AIJobFilter

router = APIRouter()
ai_filter = AIJobFilter()


@router.post("", response_model=SearchResult)
async def search_jobs(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start = time.monotonic()

    profile_result = await db.execute(
        select(ResumeProfile).where(ResumeProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=request.posted_within_hours)
    query = select(Job).where(
        Job.is_active == True,
        Job.is_duplicate == False,
        or_(Job.posted_at >= cutoff, Job.posted_at.is_(None)),
    )
    if request.sources:
        query = query.where(Job.source.in_(request.sources))
    if request.remote_type:
        query = query.where(Job.remote_type.in_(request.remote_type))

    result = await db.execute(query.limit(500))
    candidate_jobs = result.scalars().all()

    scored_jobs = await ai_filter.filter_and_score(
        jobs=candidate_jobs,
        profile=profile,
        search=request,
    )

    elapsed_ms = int((time.monotonic() - start) * 1000)
    return SearchResult(
        total=len(scored_jobs),
        results=scored_jobs[: request.max_results],
        search_params=request,
        processing_time_ms=elapsed_ms,
    )


@router.post("/natural", response_model=SearchResult)
async def natural_language_search(
    request: NaturalSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    structured = await ai_filter.parse_natural_language(request.query)
    structured.max_results = request.max_results

    from fastapi import Request
    from app.schemas.search import SearchResult

    profile_result = await db.execute(
        select(ResumeProfile).where(ResumeProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=structured.posted_within_hours)
    q = select(Job).where(
        Job.is_active == True,
        Job.is_duplicate == False,
        or_(Job.posted_at >= cutoff, Job.posted_at.is_(None)),
    ).limit(500)
    result = await db.execute(q)
    jobs = result.scalars().all()

    scored = await ai_filter.filter_and_score(jobs=jobs, profile=profile, search=structured)
    return SearchResult(
        total=len(scored),
        results=scored[: structured.max_results],
        search_params=structured,
        processing_time_ms=0,
    )

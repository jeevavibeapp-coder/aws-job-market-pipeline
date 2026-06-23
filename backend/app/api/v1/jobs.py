from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from datetime import datetime, timedelta, timezone
from typing import Annotated
import uuid

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.job import Job, JobScore
from app.schemas.job import JobListItem, JobDetail, JobFilters

router = APIRouter()


@router.get("", response_model=list[JobListItem])
async def list_jobs(
    source: Annotated[list[str] | None, Query()] = None,
    remote_type: Annotated[list[str] | None, Query()] = None,
    location: str | None = None,
    posted_within_hours: int = 24,
    min_score: float | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=posted_within_hours)
    query = select(Job).where(Job.is_active == True, Job.is_duplicate == False)

    if posted_within_hours:
        query = query.where(or_(Job.posted_at >= cutoff, Job.posted_at.is_(None)))
    if source:
        query = query.where(Job.source.in_(source))
    if remote_type:
        query = query.where(Job.remote_type.in_(remote_type))
    if location:
        query = query.where(Job.location.ilike(f"%{location}%"))

    query = query.order_by(Job.posted_at.desc().nullslast()).limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/stats")
async def job_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    total_today = await db.scalar(
        select(func.count()).select_from(Job)
        .where(Job.is_active == True, Job.posted_at >= today_cutoff)
    )
    total_direct = await db.scalar(
        select(func.count()).select_from(Job)
        .where(Job.is_active == True, Job.source == "company_site")
    )
    return {"new_jobs_today": total_today or 0, "direct_apply_jobs": total_direct or 0}


@router.get("/{job_id}", response_model=JobDetail)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")
    return job

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import uuid
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.application import Application, ApplicationStatus
from app.schemas.application import ApplicationCreate, ApplicationUpdate, ApplicationResponse, ApplicationStats

router = APIRouter()


@router.get("", response_model=list[ApplicationResponse])
async def list_applications(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Application).where(Application.user_id == current_user.id)
    if status:
        query = query.where(Application.status == status)
    query = query.order_by(Application.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=ApplicationResponse, status_code=201)
async def create_application(
    payload: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = await db.execute(
        select(Application).where(
            Application.user_id == current_user.id,
            Application.job_id == payload.job_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already tracking this job")

    app = Application(
        user_id=current_user.id,
        job_id=payload.job_id,
        status=payload.status,
        notes=payload.notes,
        applied_at=datetime.now(timezone.utc) if payload.status == "applied" else None,
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return app


@router.put("/{app_id}", response_model=ApplicationResponse)
async def update_application(
    app_id: uuid.UUID,
    payload: ApplicationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Application).where(
            Application.id == app_id, Application.user_id == current_user.id
        )
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if payload.status:
        app.status = payload.status
        if payload.status == "applied" and not app.applied_at:
            app.applied_at = datetime.now(timezone.utc)
    if payload.notes is not None:
        app.notes = payload.notes
    if payload.applied_at:
        app.applied_at = payload.applied_at

    await db.commit()
    await db.refresh(app)
    return app


@router.delete("/{app_id}", status_code=204)
async def delete_application(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Application).where(
            Application.id == app_id, Application.user_id == current_user.id
        )
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    await db.delete(app)
    await db.commit()


@router.get("/stats", response_model=ApplicationStats)
async def application_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = await db.execute(
        select(Application.status, func.count()).where(
            Application.user_id == current_user.id
        ).group_by(Application.status)
    )
    counts = {row[0]: row[1] for row in rows}
    total = sum(counts.values())
    return ApplicationStats(
        total=total,
        saved=counts.get(ApplicationStatus.saved, 0),
        applied=counts.get(ApplicationStatus.applied, 0),
        interview_scheduled=counts.get(ApplicationStatus.interview_scheduled, 0),
        offer_received=counts.get(ApplicationStatus.offer_received, 0),
        rejected=counts.get(ApplicationStatus.rejected, 0),
        withdrawn=counts.get(ApplicationStatus.withdrawn, 0),
    )

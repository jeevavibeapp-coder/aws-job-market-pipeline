from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.application import Bookmark
from app.schemas.job import JobListItem

router = APIRouter()


@router.get("", response_model=list[JobListItem])
async def list_bookmarks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Bookmark).where(Bookmark.user_id == current_user.id).order_by(Bookmark.created_at.desc())
    )
    bookmarks = result.scalars().all()
    return [b.job for b in bookmarks]


@router.post("/{job_id}", status_code=201)
async def save_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = await db.execute(
        select(Bookmark).where(
            Bookmark.user_id == current_user.id, Bookmark.job_id == job_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already bookmarked")
    db.add(Bookmark(user_id=current_user.id, job_id=job_id))
    await db.commit()
    return {"saved": True}


@router.delete("/{job_id}", status_code=204)
async def unsave_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Bookmark).where(
            Bookmark.user_id == current_user.id, Bookmark.job_id == job_id
        )
    )
    bm = result.scalar_one_or_none()
    if not bm:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    await db.delete(bm)
    await db.commit()

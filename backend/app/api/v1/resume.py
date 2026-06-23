from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.resume_profile import ResumeProfile
from app.services.resume_parser import ResumeParser

router = APIRouter()
resume_parser = ResumeParser()


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files supported")

    content = await file.read()
    parsed = await resume_parser.parse(content=content, filename=file.filename or "resume")

    result = await db.execute(
        select(ResumeProfile).where(ResumeProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if profile:
        profile.raw_text = parsed["raw_text"]
        profile.parsed_skills = parsed["skills"]
        profile.experience_years = parsed["experience_years"]
        profile.education = parsed["education"]
        profile.certifications = parsed["certifications"]
        profile.projects = parsed["projects"]
    else:
        profile = ResumeProfile(
            user_id=current_user.id,
            raw_text=parsed["raw_text"],
            parsed_skills=parsed["skills"],
            experience_years=parsed["experience_years"],
            education=parsed["education"],
            certifications=parsed["certifications"],
            projects=parsed["projects"],
        )
        db.add(profile)

    await db.commit()
    await db.refresh(profile)
    return {"message": "Resume parsed successfully", "skills_found": len(parsed["skills"]), "experience_years": parsed["experience_years"]}


@router.get("")
async def get_resume_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ResumeProfile).where(ResumeProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="No resume uploaded yet")
    return profile


@router.put("/profile")
async def update_profile(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ResumeProfile).where(ResumeProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = ResumeProfile(user_id=current_user.id)
        db.add(profile)

    allowed = ["target_roles", "preferred_locations", "remote_preference", "min_salary", "parsed_skills", "experience_years"]
    for key in allowed:
        if key in data:
            setattr(profile, key, data[key])

    await db.commit()
    await db.refresh(profile)
    return profile

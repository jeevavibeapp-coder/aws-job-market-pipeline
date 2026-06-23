from pydantic import BaseModel
import uuid
from datetime import datetime
from app.schemas.job import JobListItem


class ApplicationCreate(BaseModel):
    job_id: uuid.UUID
    status: str = "saved"
    notes: str | None = None


class ApplicationUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
    applied_at: datetime | None = None


class ApplicationResponse(BaseModel):
    id: uuid.UUID
    job: JobListItem
    status: str
    applied_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApplicationStats(BaseModel):
    total: int
    saved: int
    applied: int
    interview_scheduled: int
    offer_received: int
    rejected: int
    withdrawn: int

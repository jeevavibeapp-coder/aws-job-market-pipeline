from fastapi import APIRouter
from app.api.v1 import auth, jobs, search, applications, bookmarks, resume

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
api_router.include_router(bookmarks.router, prefix="/bookmarks", tags=["bookmarks"])
api_router.include_router(resume.router, prefix="/resume", tags=["resume"])

from fastapi import APIRouter

from app.api.v1 import documents, evidence, interviews, jobs, me, profile, resumes

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(me.router)
api_router.include_router(profile.router)
api_router.include_router(evidence.router)
api_router.include_router(resumes.router)
api_router.include_router(interviews.router)
api_router.include_router(jobs.router)
api_router.include_router(documents.router)

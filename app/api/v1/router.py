from fastapi import APIRouter
from app.api.v1.endpoints import contracts, extract, jobs

api_router = APIRouter()
api_router.include_router(extract.router, prefix="/extract", tags=["Extraction"])
api_router.include_router(contracts.router, prefix="/contracts", tags=["Contracts"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])

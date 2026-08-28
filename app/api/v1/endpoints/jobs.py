from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.contract import ErrorResponse
from app.schemas.job import JobListResponse, JobResponse
from app.services.job_queue import job_queue

router = APIRouter()


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
    summary="Get background extraction job status",
    description="Retrieve current status, progress, and extracted contract payload for an asynchronous extraction job.",
    responses={
        200: {"model": JobResponse, "description": "Job status retrieved successfully."},
        404: {"model": ErrorResponse, "description": "Job ID not found."},
    },
)
async def get_job_status(
    job_id: str = Path(..., description="UUID of the background extraction job"),
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    job = await job_queue.get_job_by_id(db=db, job_id=job_id)
    return JobResponse.model_validate(job)


@router.get(
    "",
    response_model=JobListResponse,
    status_code=status.HTTP_200_OK,
    summary="List background extraction jobs",
    description="List submitted asynchronous extraction jobs ordered by submission date.",
    responses={
        200: {"model": JobListResponse, "description": "Jobs retrieved successfully."},
    },
)
async def list_jobs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    items, total = await job_queue.list_jobs(db=db, skip=skip, limit=limit)
    return JobListResponse(
        total=total,
        items=[JobResponse.model_validate(j) for j in items],
    )

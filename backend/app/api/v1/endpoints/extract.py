from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limiter import rate_limiter
from app.schemas.contract import ContractResponse, ErrorResponse
from app.schemas.extraction import ExtractRequest
from app.schemas.job import JobResponse
from app.services.contract_service import ContractService
from app.services.job_queue import job_queue

router = APIRouter()


@router.post(
    "",
    response_model=ContractResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Synchronous Legal Document Metadata Extraction",
    description="Synchronously extracts structured metadata from raw lease agreement text, performs deterministic validation, and persists valid records to database.",
    dependencies=[Depends(rate_limiter)],
    responses={
        201: {"model": ContractResponse, "description": "Contract successfully extracted, validated, and stored."},
        400: {"model": ErrorResponse, "description": "Invalid input payload or empty document."},
        422: {"model": ErrorResponse, "description": "Business validation rule violation (e.g., negative rent, expiration prior to commencement)."},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded or LLM quota exhaustion."},
        502: {"model": ErrorResponse, "description": "LLM output schema decoding failure or provider error."},
        504: {"model": ErrorResponse, "description": "LLM API timeout."},
    },
)
async def extract_contract(
    payload: ExtractRequest,
    db: AsyncSession = Depends(get_db),
) -> ContractResponse:
    """Extract and validate legal contract metadata synchronously."""
    contract = await ContractService.process_and_store_contract(
        db=db,
        raw_text=payload.text,
    )
    return ContractResponse.model_validate(contract)


@router.post(
    "/async",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Asynchronous Background Legal Document Extraction",
    description="Enqueues contract extraction for asynchronous background execution. Returns a Job ID for polling via GET /api/v1/jobs/{job_id}.",
    dependencies=[Depends(rate_limiter)],
    responses={
        202: {"model": JobResponse, "description": "Extraction job accepted and queued for background processing."},
        400: {"model": ErrorResponse, "description": "Invalid input payload."},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded."},
    },
)
async def extract_contract_async(
    payload: ExtractRequest,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Enqueue legal contract extraction job for asynchronous background execution."""
    job = await job_queue.submit_job(
        db=db,
        raw_text=payload.text,
    )
    return JobResponse.model_validate(job)

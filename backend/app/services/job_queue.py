import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.exceptions import AppException, JobNotFoundError
from app.models.job import ExtractionJob, JobStatus
from app.services.contract_service import ContractService

logger = logging.getLogger(__name__)


class JobQueueManager:
    """Asynchronous background worker queue for processing legal document extraction jobs."""

    def __init__(self) -> None:
        self._queue: Optional[asyncio.Queue[Tuple[str, str, Optional[str], Optional[str]]]] = None
        self._worker_tasks: List[asyncio.Task] = []
        self._running: bool = False

    def _get_queue(self) -> asyncio.Queue:
        if self._queue is None:
            self._queue = asyncio.Queue()
        return self._queue

    async def _cleanup_stale_jobs(self) -> None:
        """Mark any PENDING or PROCESSING jobs as FAILED on startup since their in-memory state is lost."""
        async with AsyncSessionLocal() as session:
            stmt = select(ExtractionJob).where(
                ExtractionJob.status.in_([JobStatus.PENDING.value, JobStatus.PROCESSING.value])
            )
            result = await session.execute(stmt)
            stale_jobs = result.scalars().all()
            
            if stale_jobs:
                logger.info("Found %d stale jobs from previous run. Marking as FAILED.", len(stale_jobs))
                for job in stale_jobs:
                    job.status = JobStatus.FAILED.value
                    job.error_code = "INTERRUPTED_ERROR"
                    job.error_message = "Job was interrupted due to server restart and could not be recovered."
                    job.completed_at = datetime.now(timezone.utc)
                await session.commit()

    async def start(self) -> None:
        """Start background worker tasks and cleanup stale jobs."""
        if self._running:
            return
        self._running = True
        self._queue = asyncio.Queue()
        
        await self._cleanup_stale_jobs()
        
        concurrency = settings.QUEUE_MAX_CONCURRENCY
        logger.info("Starting %d background extraction queue workers...", concurrency)
        for i in range(concurrency):
            task = asyncio.create_task(self._worker_loop(i, self._queue))
            self._worker_tasks.append(task)

    async def stop(self) -> None:
        """Gracefully stop and drain workers on shutdown."""
        self._running = False
        logger.info("Stopping background queue workers...")
        for task in self._worker_tasks:
            task.cancel()
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()
        self._queue = None

    async def submit_job(
        self,
        db: AsyncSession,
        raw_text: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> ExtractionJob:
        """Create job record and enqueue for background execution."""
        job_id = str(uuid.uuid4())
        job = ExtractionJob(
            id=job_id,
            status=JobStatus.PENDING.value,
            provider=provider or settings.LLM_PROVIDER,
            model=model or (settings.GEMINI_MODEL if (provider or settings.LLM_PROVIDER) == "gemini" else settings.OPENAI_MODEL),
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        queue = self._get_queue()
        await queue.put((job_id, raw_text, provider, model))
        logger.info("Enqueued extraction job ID=%s", job_id)
        return job

    async def get_job_by_id(self, db: AsyncSession, job_id: str) -> ExtractionJob:
        """Retrieve job record by ID."""
        stmt = select(ExtractionJob).where(ExtractionJob.id == job_id)
        result = await db.execute(stmt)
        job = result.scalar_one_or_none()
        if not job:
            raise JobNotFoundError(job_id=job_id)
        return job

    async def list_jobs(self, db: AsyncSession, skip: int = 0, limit: int = 50) -> Tuple[List[ExtractionJob], int]:
        """List jobs ordered by submission timestamp descending."""
        count_stmt = select(func.count()).select_from(ExtractionJob)
        total = (await db.execute(count_stmt)).scalar() or 0

        items_stmt = (
            select(ExtractionJob)
            .order_by(ExtractionJob.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(items_stmt)
        return list(result.scalars().all()), total

    async def _worker_loop(
        self,
        worker_id: int,
        queue: asyncio.Queue[Tuple[str, str, Optional[str], Optional[str]]],
    ) -> None:
        logger.info("Worker-%d started listening for jobs.", worker_id)
        while self._running:
            try:
                job_id, raw_text, provider, model = await queue.get()
            except asyncio.CancelledError:
                break

            try:
                await self._process_job(job_id, raw_text, provider, model)
            except Exception as e:
                logger.exception("Unexpected error in worker-%d processing job %s: %s", worker_id, job_id, e)
            finally:
                queue.task_done()

    async def _process_job(
        self,
        job_id: str,
        raw_text: str,
        provider: Optional[str],
        model: Optional[str],
    ) -> None:
        async with AsyncSessionLocal() as session:
            # 1. Mark PROCESSING
            stmt = select(ExtractionJob).where(ExtractionJob.id == job_id)
            job = (await session.execute(stmt)).scalar_one_or_none()
            if not job:
                return

            job.status = JobStatus.PROCESSING.value
            await session.commit()

            try:
                contract = await ContractService.process_and_store_contract(
                    db=session,
                    raw_text=raw_text,
                    provider=provider,
                    model=model,
                )
                job.status = JobStatus.COMPLETED.value
                job.contract_id = contract.id
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()
                logger.info("Job %s completed successfully. Created Contract %d", job_id, contract.id)

            except AppException as exc:
                logger.warning("Job %s failed with application error [%s]: %s", job_id, exc.error_code, exc.message)
                job.status = JobStatus.FAILED.value
                job.error_code = exc.error_code
                job.error_message = exc.message
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()

            except Exception as exc:
                logger.exception("Job %s failed with unhandled exception: %s", job_id, exc)
                job.status = JobStatus.FAILED.value
                job.error_code = "INTERNAL_ERROR"
                job.error_message = f"An unexpected error occurred during processing: {str(exc)}"
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()


job_queue = JobQueueManager()

"""
CLARIUS Backend - Jobs Worker Pool

This module implements the asyncio background runner that polls the persistent queue
and executes tasks asynchronously (ADR-008).
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from app.infrastructure.jobs.models import JobStatus
from app.infrastructure.jobs.queue import job_queue
from app.infrastructure.jobs.registry import get_job_handler

logger = logging.getLogger("clarius.jobs.workers")

class JobWorkerPool:
    """Async background worker running sequential jobs in FastAPI sidecar."""
    
    def __init__(self, poll_interval: float = 1.0):
        self.poll_interval = poll_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        """Start the worker pool task."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Background job worker pool started.")

    async def stop(self) -> None:
        """Stop worker pool and wait for current job."""
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Background job worker pool stopped.")

    async def _run_loop(self) -> None:
        while self._running:
            try:
                job = job_queue.get_next_pending_job()
                if job:
                    await self._process_job(job)
                else:
                    await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in job worker loop: {str(e)}", exc_info=True)
                await asyncio.sleep(self.poll_interval)

    async def _process_job(self, job) -> None:
        logger.info(f"Starting job {job.id} of type '{job.type}'")
        handler = get_job_handler(job.type)
        
        if not handler:
            error_msg = f"No handler registered for job type '{job.type}'"
            logger.error(error_msg)
            job_queue.update_job_status(job.id, JobStatus.FAILED, error=error_msg)
            return

        job_queue.update_job_status(job.id, JobStatus.RUNNING, message="Processing started...")
        
        try:
            # Execute actual registered handler (which is an async function)
            await handler(job.id, job.payload)
            job_queue.update_job_status(job.id, JobStatus.SUCCESS, progress=1.0, message="Completed successfully.")
            logger.info(f"Job {job.id} completed successfully.")
        except Exception as e:
            logger.error(f"Error executing job {job.id}: {str(e)}", exc_info=True)
            
            # Check retries
            if job.retry_count < job.max_retries:
                job_queue.increment_retry(job.id)
                # Set status back to PENDING to retry on next cycle
                job_queue.update_job_status(
                    job_id=job.id,
                    status=JobStatus.PENDING,
                    message=f"Attempt failed, retrying... Error: {str(e)}"
                )
            else:
                job_queue.update_job_status(
                    job_id=job.id,
                    status=JobStatus.FAILED,
                    error=str(e),
                    message="Job failed after max retries."
                )


# Global worker pool instance
worker_pool = JobWorkerPool()

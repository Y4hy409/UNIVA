"""
CLARIUS Backend - Jobs API Endpoints

This module exposes routes to check job status and cancel pending jobs (ADR-008).
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

from app.infrastructure.jobs.queue import job_queue
from app.infrastructure.jobs.models import JobStatus

router = APIRouter(prefix="/jobs", tags=["jobs"])

class JobStatusResponse(BaseModel):
    id: str
    type: str
    status: JobStatus
    progress: float
    progress_message: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Retrieve detailed status and progress of a background job."""
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found."
        )
    return JobStatusResponse(
        id=job.id,
        type=job.type,
        status=job.status,
        progress=job.progress,
        progress_message=job.progress_message,
        error=job.error,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at
    )


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a pending background job."""
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found."
        )
        
    if job.status == JobStatus.PENDING:
        job_queue.update_job_status(job_id, JobStatus.CANCELLED, message="Cancelled by user.")
        return {"message": f"Job {job_id} cancelled successfully."}
    elif job.status == JobStatus.RUNNING:
        # In a single-threaded in-process queue, cancelling a running job is best-effort.
        # We update the status to CANCELLED, and active handlers can check this.
        job_queue.update_job_status(job_id, JobStatus.CANCELLED, message="Cancelled by user.")
        return {"message": f"Job {job_id} marked for cancellation."}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job in state: {job.status.value}"
        )

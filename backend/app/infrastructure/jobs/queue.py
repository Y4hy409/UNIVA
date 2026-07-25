"""
CLARIUS Backend - Jobs Queue Persistence

This module manages persisting and querying background jobs using SQLite (ADR-008).
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.infrastructure.jobs.models import Job, JobStatus

JOBS_DB_PATH = Path("data/jobs.db")

class JobQueue:
    """SQLite-backed job queue for persistent state tracking."""
    
    def __init__(self, db_path: Path = JOBS_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    progress REAL NOT NULL,
                    progress_message TEXT,
                    error TEXT,
                    retry_count INTEGER NOT NULL,
                    max_retries INTEGER NOT NULL,
                    created_by TEXT,
                    correlation_id TEXT
                );
            """)
            conn.commit()

    def enqueue(self, job_type: str, payload: Dict[str, Any], priority: int = 5, created_by: Optional[str] = None) -> Job:
        """Create a new pending job and write it to SQLite."""
        job = Job(
            id=str(uuid.uuid4()),
            type=job_type,
            payload=payload,
            status=JobStatus.PENDING,
            priority=priority,
            created_at=datetime.utcnow(),
            max_retries=2,
            created_by=created_by
        )
        
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO jobs (id, type, payload, status, priority, created_at, progress, retry_count, max_retries, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id, job.type, json.dumps(job.payload), job.status.value,
                    job.priority, job.created_at, job.progress, job.retry_count,
                    job.max_retries, job.created_by
                )
            )
            conn.commit()
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """Fetch job details by ID."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if not row:
                return None
            return self._row_to_job(row)

    def get_next_pending_job(self) -> Optional[Job]:
        """Retrieve the highest priority pending job."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE status = ? ORDER BY priority DESC, created_at ASC LIMIT 1",
                (JobStatus.PENDING.value,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_job(row)

    def update_job_status(self, job_id: str, status: JobStatus, progress: float = 0.0, 
                          message: Optional[str] = None, error: Optional[str] = None) -> None:
        """Update runtime job metadata."""
        now = datetime.utcnow()
        with self._get_connection() as conn:
            if status == JobStatus.RUNNING:
                conn.execute(
                    "UPDATE jobs SET status = ?, started_at = ?, progress = ?, progress_message = ? WHERE id = ?",
                    (status.value, now, progress, message, job_id)
                )
            elif status in (JobStatus.SUCCESS, JobStatus.FAILED, JobStatus.CANCELLED):
                conn.execute(
                    "UPDATE jobs SET status = ?, completed_at = ?, progress = ?, progress_message = ?, error = ? WHERE id = ?",
                    (status.value, now, progress, message, error, job_id)
                )
            else:
                conn.execute(
                    "UPDATE jobs SET status = ?, progress = ?, progress_message = ? WHERE id = ?",
                    (status.value, progress, message, job_id)
                )
            conn.commit()

    def increment_retry(self, job_id: str) -> None:
        """Increment job retry count."""
        with self._get_connection() as conn:
            conn.execute("UPDATE jobs SET retry_count = retry_count + 1 WHERE id = ?", (job_id,))
            conn.commit()

    def get_running_jobs(self) -> List[Job]:
        """Retrieve all currently running jobs."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM jobs WHERE status = ?", (JobStatus.RUNNING.value,)).fetchall()
            return [self._row_to_job(r) for r in rows]

    def _row_to_job(self, r: sqlite3.Row) -> Job:
        return Job(
            id=r["id"],
            type=r["type"],
            payload=json.loads(r["payload"]),
            status=JobStatus(r["status"]),
            priority=r["priority"],
            created_at=datetime.fromisoformat(r["created_at"]) if isinstance(r["created_at"], str) else r["created_at"],
            started_at=datetime.fromisoformat(r["started_at"]) if r["started_at"] else None,
            completed_at=datetime.fromisoformat(r["completed_at"]) if r["completed_at"] else None,
            progress=r["progress"],
            progress_message=r["progress_message"],
            error=r["error"],
            retry_count=r["retry_count"],
            max_retries=r["max_retries"],
            created_by=r["created_by"],
            correlation_id=r["correlation_id"]
        )


# Global instance
job_queue = JobQueue()

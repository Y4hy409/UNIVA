"""
CLARIUS Backend - Jobs Models

This module defines data structures representing background jobs and statuses (ADR-008).
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    id: str
    type: str                    # "import.csv" | "ocr.process" | ...
    payload: Dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    priority: int = 5            # 0 to 10
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0        # 0.0 to 1.0
    progress_message: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 2
    created_by: Optional[str] = None
    correlation_id: Optional[str] = None

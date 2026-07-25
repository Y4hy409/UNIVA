"""
CLARIUS Backend - Job Handlers Registry

This module maps job type strings to callable executors.
"""

from typing import Dict, Callable, Any, Awaitable, Optional

# Handler structure: async def handler(job_id: str, payload: dict) -> None
JobHandler = Callable[[str, Dict[str, Any]], Awaitable[None]]

_handlers: Dict[str, JobHandler] = {}

def register_job_handler(job_type: str, handler: JobHandler) -> None:
    """Register a handler for a background job type."""
    _handlers[job_type] = handler

def get_job_handler(job_type: str) -> Optional[JobHandler]:
    """Retrieve the registered handler function for a job type."""
    return _handlers.get(job_type)

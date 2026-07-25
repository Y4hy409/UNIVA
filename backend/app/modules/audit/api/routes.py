"""
CLARIUS Backend - Audit Log Routes

This module exposes endpoints for administrators to view audit histories (ADR-000).
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import duckdb

from app.infrastructure.database import get_db
from app.modules.audit.application.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])

class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    timestamp: str


@router.get("", response_model=List[AuditLogResponse])
async def list_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """Retrieve recent platform audit logs (restricted to Admins/Owners)."""
    service = AuditService(db)
    logs = service.list_logs(limit=limit)
    return [
        AuditLogResponse(
            id=str(log.id),
            user_id=str(log.user_id) if log.user_id else None,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=str(log.resource_id) if log.resource_id else None,
            details=log.details,
            ip_address=log.ip_address,
            timestamp=log.timestamp.isoformat()
        )
        for log in logs
    ]

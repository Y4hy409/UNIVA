"""
CLARIUS Backend - Audit Logging Service

This service writes user action logs to DuckDB and subscribes to Domain Event Bus triggers (ADR-000).
"""

import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
import duckdb

from app.domain.entities import AuditLog
from app.infrastructure.database import db_manager
from app.infrastructure.events import event_bus, DomainEvent

class AuditService:
    """Handles logging actions and listing historical audits."""
    
    def __init__(self, db_conn: Optional[duckdb.DuckDBPyConnection] = None):
        self.conn = db_conn or db_manager.get_connection()

    def log_action(self, user_id: Optional[str], action: str, resource_type: str, 
                   resource_id: Optional[str] = None, details: Dict[str, Any] = None, 
                   ip_address: Optional[str] = None) -> AuditLog:
        """Insert an audit log entry into DuckDB."""
        log_entry = AuditLog(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id) if user_id else None,
            action=action,
            resource_type=resource_type,
            resource_id=uuid.UUID(resource_id) if resource_id else None,
            details=details or {},
            ip_address=ip_address,
            timestamp=datetime.utcnow()
        )
        
        self.conn.execute(
            """
            INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, details, ip_address, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                str(log_entry.id), 
                str(log_entry.user_id) if log_entry.user_id else None,
                log_entry.action, 
                log_entry.resource_type, 
                str(log_entry.resource_id) if log_entry.resource_id else None,
                json.dumps(log_entry.details), 
                log_entry.ip_address, 
                log_entry.timestamp
            ]
        )
        return log_entry

    def list_logs(self, limit: int = 100) -> List[AuditLog]:
        """Retrieve recent audit logs."""
        rows = self.conn.execute(
            "SELECT id, user_id, action, resource_type, resource_id, details, ip_address, timestamp FROM audit_logs ORDER BY timestamp DESC LIMIT ?",
            [limit]
        ).fetchall()
        
        logs = []
        for r in rows:
            logs.append(AuditLog(
                id=uuid.UUID(r[0]),
                user_id=uuid.UUID(r[1]) if r[1] else None,
                action=r[2],
                resource_type=r[3],
                resource_id=uuid.UUID(r[4]) if r[4] else None,
                details=json.loads(r[5]) if r[5] else {},
                ip_address=r[6],
                timestamp=r[7]
            ))
        return logs


# Async event handlers to automatically write logs upon event bus signals
async def handle_user_login_event(event: DomainEvent) -> None:
    service = AuditService()
    service.log_action(
        user_id=event.payload.get("user_id"),
        action="login",
        resource_type="user",
        resource_id=event.payload.get("user_id"),
        details={"username": event.payload.get("username")},
        ip_address=event.payload.get("ip_address")
    )


async def handle_document_upload_event(event: DomainEvent) -> None:
    service = AuditService()
    service.log_action(
        user_id=event.payload.get("user_id"),
        action="upload",
        resource_type="document",
        resource_id=event.payload.get("doc_id"),
        details={"title": event.payload.get("title")}
    )


def register_audit_event_subscribers() -> None:
    """Subscribe handlers to the global event bus."""
    event_bus.subscribe("user.login", handle_user_login_event)
    event_bus.subscribe("document.uploaded", handle_document_upload_event)

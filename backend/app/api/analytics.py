"""
CLARIUS Backend - Analytics Query API

This module exposes routes to execute natural language queries against DuckDB (ADR-000).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import duckdb

from app.infrastructure.database import get_db
from app.infrastructure.licensing import capability_service
from app.ai.agents.core.sql_agent import SQLAgent
from app.api.dependencies import RoleChecker
from app.domain.entities import UserRole

router = APIRouter(prefix="/analytics", tags=["analytics"])

class QueryRequest(BaseModel):
    query_text: str


class QueryResponse(BaseModel):
    success: bool
    sql: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


@router.post("/query", response_model=QueryResponse)
async def execute_natural_language_query(
    req: QueryRequest,
    db: duckdb.DuckDBPyConnection = Depends(get_db),
    _user = Depends(RoleChecker([UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER, UserRole.ANALYST]))
):
    """Convert natural language questions to SQL and retrieve database records."""
    if not capability_service.has_capability("clarius.nl_query"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="A valid CLARIUS license is required to execute natural language queries."
        )

    agent = SQLAgent(db_conn=db)
    result = agent.process_natural_language_query(req.query_text)
    
    if not result.get("success", False):
        return QueryResponse(
            success=False,
            error=result.get("error", "An error occurred during query generation.")
        )
        
    return QueryResponse(
        success=True,
        sql=result.get("sql"),
        data=result.get("data")
    )

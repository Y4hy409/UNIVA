"""
CLARIUS Backend - Data Sources API Routes

This module exposes routes to register, check, and trigger imports of data sources (ADR-005).
"""

import json
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.infrastructure.jobs.queue import job_queue
from app.infrastructure.database import get_db, db_manager
from app.infrastructure.file_security import FileSecurity
from app.infrastructure.licensing import capability_service
from app.api.dependencies import RoleChecker
from app.domain.entities import UserRole

router = APIRouter(prefix="/data-sources", tags=["data-sources"])


class ImportTriggerResponse(BaseModel):
    job_id: str
    status_url: str


@router.post("/import", response_model=ImportTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_import(
    file: UploadFile = File(...),
    target_table: str = Form(...),
    mappings: str = Form(...), # JSON string containing mapping dictionary
    _user = Depends(RoleChecker([UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER]))
):
    """Upload data file and trigger a background database ingestion job."""
    if not capability_service.has_capability("clarius.dashboards") and not capability_service.has_capability("clarius.analytics"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="A valid CLARIUS license with analytics and mapping capabilities is required."
        )

    # Enforce file sandbox, size, and extension validation
    file_path = FileSecurity.validate_and_sandbox(file, ["csv", "xlsx", "xls"])
    file_ext = file_path.name.split('.')[-1].lower()
    
    if file_ext == 'csv':
        job_type = "import.csv"
    elif file_ext in ('xlsx', 'xls'):
        job_type = "import.excel"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format: .{file_ext}. Only CSV and Excel (.xlsx, .xls) are supported."
        )

    # Parse mappings JSON string
    try:
        parsed_mappings = json.loads(mappings)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid mappings JSON configuration format."
        )

    # Save uploaded file contents safely
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save source file: {str(e)}"
        )

    # Format mappings payload
    formatted_mappings = []
    for k, v in parsed_mappings.items():
        data_type = "string"
        if any(term in k.lower() for term in ["quantity", "stock", "level", "point"]):
            data_type = "integer"
        elif any(term in k.lower() for term in ["amount", "cost", "price", "unit"]):
            data_type = "float"
        elif "date" in k.lower():
            data_type = "date"
        
        formatted_mappings.append({
            "source_column": v,
            "target_field": k,
            "data_type": data_type
        })

    # Queue background task
    job = job_queue.enqueue(
        job_type=job_type,
        payload={
            "file_path": str(file_path),
            "target_table": target_table,
            "mappings": formatted_mappings
        },
        priority=10
    )

    return ImportTriggerResponse(
        job_id=job.id,
        status_url=f"/jobs/{job.id}"
    )


@router.get("/preview/{table_name}")
async def preview_table(
    table_name: str,
    _user = Depends(RoleChecker([UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER, UserRole.ANALYST, UserRole.STAFF]))
):
    """Fetch the first 5 records of a given database table for previewing."""
    import re
    if not re.match(r"^[a-zA-Z0-9_]+$", table_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid table name format."
        )

    try:
        conn = db_manager.get_connection()
        cursor = conn.execute(f"DESCRIBE {table_name}")
        cols_info = cursor.fetchall()
        columns = [col[0] for col in cols_info]

        cursor = conn.execute(f"SELECT * FROM {table_name} LIMIT 5")
        records = cursor.fetchall()

        data = []
        for row in records:
            row_dict = {}
            for i, col in enumerate(columns):
                row_dict[col] = str(row[i]) if row[i] is not None else ""
            data.append(row_dict)

        return {
            "columns": columns,
            "data": data
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch table preview: {str(e)}"
        )

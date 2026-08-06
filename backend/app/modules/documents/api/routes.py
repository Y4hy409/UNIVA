"""
CLARIUS Backend - Document Management Routes

This module implements API routes for uploading documents and executing semantic searches (ADR-005).
"""

import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.infrastructure.jobs.queue import job_queue
from app.infrastructure.file_security import FileSecurity
from app.infrastructure.licensing import capability_service
from app.infrastructure.database import db_manager
from app.infrastructure.repositories import DuckDBDocumentRepository
from app.modules.documents.application.document_service import DocumentService
from app.api.dependencies import RoleChecker
from app.domain.entities import UserRole

router = APIRouter(prefix="/documents", tags=["documents"])

# Dependency Providers
def get_document_repository() -> DuckDBDocumentRepository:
    return DuckDBDocumentRepository(db_manager)

def get_document_service(repo: DuckDBDocumentRepository = Depends(get_document_repository)) -> DocumentService:
    return DocumentService(repo)


class UploadTriggerResponse(BaseModel):
    job_id: str
    status_url: str


class SearchQueryRequest(BaseModel):
    query_text: str
    limit: int = 3


class SearchQueryResult(BaseModel):
    content: str
    metadata: Dict[str, Any]
    score: float


# Handler to process document uploads in background worker
async def process_document_job_handler(job_id: str, payload: Dict[str, Any]) -> None:
    """Background task executing the OCR and RAG ingestion pipeline."""
    file_path = Path(payload["file_path"])
    doc_type = payload["doc_type"]
    title = payload.get("title")
    
    repo = DuckDBDocumentRepository(db_manager)
    service = DocumentService(repo)
    await service.ingest_document(file_path, doc_type, title)


@router.post("/upload", response_model=UploadTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form("policy"),
    title: Optional[str] = Form(None),
    _user = Depends(RoleChecker([UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER, UserRole.ANALYST]))
):
    """Upload a file to process OCR and index text chunks for RAG in the background."""
    if not capability_service.has_capability("clarius.ocr") and not capability_service.has_capability("clarius.document_intelligence"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="A valid CLARIUS license with document intelligence capabilities is required."
        )

    # Enforce file sandbox, size, and extension validation
    file_path = FileSecurity.validate_and_sandbox(file, ["txt", "pdf", "docx"])
    
    # Save file contents to disk safely
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {str(e)}"
        )
        
    # Queue background task
    job = job_queue.enqueue(
        job_type="document.process",
        payload={
            "file_path": str(file_path),
            "doc_type": doc_type,
            "title": title or file.filename
        },
        priority=5
    )
    
    return UploadTriggerResponse(
        job_id=job.id,
        status_url=f"/jobs/{job.id}"
    )


@router.post("/search", response_model=List[SearchQueryResult])
async def search_documents(
    req: SearchQueryRequest,
    service: DocumentService = Depends(get_document_service),
    _user = Depends(RoleChecker([UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER, UserRole.ANALYST, UserRole.STAFF]))
):
    """Execute a semantic similarity search across indexed document chunks."""
    try:
        results = service.search_similar_chunks(req.query_text, limit=req.limit)
        return [
            SearchQueryResult(
                content=res["content"],
                metadata=res["metadata"],
                score=res["score"]
            )
            for res in results
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search failed: {str(e)}"
        )


@router.get("/query")
async def query_documents(
    q: str,
    limit: int = 3,
    service: DocumentService = Depends(get_document_service),
    _user = Depends(RoleChecker([UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER, UserRole.ANALYST, UserRole.STAFF]))
):
    """Execute semantic similarity query across indexed document chunks (GET)."""
    try:
        results = service.search_similar_chunks(q, limit=limit)
        formatted = []
        for r in results:
            title = r.get("metadata", {}).get("title", "Policy Document")
            formatted.append({
                "title": title,
                "content": r.get("content", ""),
                "distance": r.get("score", 0.0),
                "metadata": r.get("metadata", {})
            })
        return {"results": formatted}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic query failed: {str(e)}"
        )



@router.get("")
async def list_documents(
    _user = Depends(RoleChecker([UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER, UserRole.ANALYST, UserRole.STAFF]))
):
    """Retrieve all indexed documents."""
    import json
    try:
        conn = db_manager.get_connection()
        rows = conn.execute("SELECT id, title, doc_type, metadata, created_at FROM documents").fetchall()
        result = []
        for r in rows:
            try:
                meta = json.loads(r[3]) if r[3] else {}
            except Exception:
                meta = {}
            result.append({
                "id": r[0],
                "title": r[1],
                "doc_type": r[2],
                "metadata": meta,
                "created_at": r[4]
            })
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}"
        )


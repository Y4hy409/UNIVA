"""
CLARIUS Backend - Startup & Health Routes

This module implements API endpoints queried by the Tauri frontend during the
staged boot sequence (ADR-001) to verify system dependencies.
"""

from fastapi import APIRouter, Depends
from urllib.request import urlopen, Request
from urllib.error import URLError
import time

from app.core.config import settings
from app.infrastructure.licensing import capability_service, LicenseStatus
from app.infrastructure.database import db_manager
from app.infrastructure.knowledge import knowledge_manager

router = APIRouter()


def check_ollama_status() -> str:
    """Check if the local Ollama LLM host is reachable."""
    url = f"{settings.OLLAMA_HOST}/api/tags"
    try:
        req = Request(url, method="GET")
        with urlopen(req, timeout=2.0) as response:
            if response.status == 200:
                return "connected"
    except URLError:
        pass
    except Exception:
        pass
    return "disconnected"


@router.get("/health")
async def health():
    """Simple API health check endpoint."""
    return {"status": "healthy", "timestamp": time.time()}


@router.get("/startup/status")
async def startup_status():
    """
    Get detailed status of the initialization sequence:
    - Licensing
    - DuckDB connection
    - ChromaDB (Knowledge layer)
    - Ollama LLM service
    """
    # 1. License Check
    capability_service.reload_license()
    license_status = capability_service.get_license_status()
    
    # 2. DuckDB Check
    try:
        conn = db_manager.get_connection()
        conn.execute("SELECT 1")
        duckdb_status = "connected"
    except Exception:
        duckdb_status = "error"

    # 3. ChromaDB Check
    chroma_status = "connected" if knowledge_manager.heartbeat() else "disconnected"

    # 4. Ollama Check
    ollama_status = check_ollama_status()

    # Determine overall status
    is_ready = (
        license_status in (LicenseStatus.VALID, LicenseStatus.EXPIRING_SOON, LicenseStatus.GRACE_PERIOD)
        and duckdb_status == "connected"
        and chroma_status == "connected"
        and ollama_status == "connected"
    )

    return {
        "ready": is_ready,
        "stages": {
            "licensing": {
                "status": "ok" if license_status in (LicenseStatus.VALID, LicenseStatus.EXPIRING_SOON, LicenseStatus.GRACE_PERIOD) else "failed",
                "details": license_status.value
            },
            "database": {
                "status": "ok" if duckdb_status == "connected" else "failed",
                "details": duckdb_status
            },
            "knowledge": {
                "status": "ok" if chroma_status == "connected" else "failed",
                "details": chroma_status
            },
            "ollama": {
                "status": "ok" if ollama_status == "connected" else "failed",
                "details": ollama_status
            }
        }
    }

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


@router.get("/licensing/properties")
async def get_licensing_properties():
    """Retrieve actual license metadata and properties dynamically."""
    limits = capability_service.get_limits()
    edition = capability_service.license_data.get("edition", "clarius")
    
    # Format edition name nicely
    edition_map = {
        "clarius": "CLARIUS Offline Basic",
        "clarius_copilot": "CLARIUS Copilot Pro",
        "univa": "CLARIUS UNIVA Enterprise"
    }
    edition_name = edition_map.get(edition.lower(), f"CLARIUS {edition.title()}")

    return {
        "edition": edition_name,
        "max_users": limits.max_users,
        "max_branches": limits.max_branches
    }


@router.get("/analytics/insights")
async def get_insights():
    """Retrieve dynamic insights and anomalies based on actual database contents."""
    insights = []
    
    # Check if table exists first using a quick metadata check or try/except
    try:
        conn = db_manager.get_connection()
        
        # 1. Check Inventory Shortage Risk
        shortages = conn.execute(
            "SELECT Product, Region, Current_Stock, Reorder_Level FROM inventory WHERE Current_Stock < Reorder_Level"
        ).fetchall()
        
        if shortages:
            items_desc = ", ".join([f"{row[0]} ({row[1]})" for row in shortages[:3]])
            msg = f"{len(shortages)} inventory items have fallen below safety reorder points: {items_desc}."
            insights.append({
                "title": "Inventory Shortage Risk",
                "priority": "Critical Priority",
                "message": msg,
                "type": "error"
            })
    except Exception:
        pass
        
    try:
        conn = db_manager.get_connection()
        
        # 2. Check Sales performance / Top performing region
        sales_summary = conn.execute(
            "SELECT Region, SUM(Total_Sales) as total FROM sales GROUP BY Region ORDER BY total DESC LIMIT 1"
        ).fetchone()
        if sales_summary:
            insights.append({
                "title": "Sales Trend Opportunity",
                "priority": "Opportunity",
                "message": f"Region '{sales_summary[0]}' performed the best with total sales of ₹{sales_summary[1]:,.2f}.",
                "type": "success"
            })
    except Exception:
        pass

    try:
        conn = db_manager.get_connection()
        total_items = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        if total_items > 0:
            insights.append({
                "title": "Database Overview",
                "priority": "Active Tracking",
                "message": f"Currently monitoring {total_items} unique SKU items across all active business regions.",
                "type": "info"
            })
    except Exception:
        pass

    # Fallback to defaults if no CSV files uploaded yet or queries returned empty
    if not insights:
        insights = [
            {
                "title": "System Active",
                "priority": "Active",
                "message": "Upload CSV data sources (Inventory/Sales) to generate dynamic automated alerts and shortage risks.",
                "type": "info"
            }
        ]

    return {"insights": insights}

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
    """Check if the local Ollama LLM host is reachable (100% offline)."""
    import httpx
    hosts_to_try = [
        settings.OLLAMA_HOST,
        "http://127.0.0.1:11434",
        "http://localhost:11434"
    ]
    for host in hosts_to_try:
        try:
            r = httpx.get(f"{host}/api/tags", timeout=1.0)
            if r.status_code == 200:
                return "connected"
        except Exception:
            continue
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

    # 3. ChromaDB Check (Local Persistent Client)
    try:
        chroma_status = "connected" if knowledge_manager.heartbeat() else "degraded"
    except Exception:
        chroma_status = "degraded"

    # 4. Ollama Check (Local inference host)
    ollama_status = check_ollama_status()

    # Determine overall status - allow boot if core database is up
    is_ready = (
        duckdb_status == "connected"
        and (chroma_status in ("connected", "degraded"))
    )

    subsystems_dict = {
        "duckdb": {
            "status": "ok" if duckdb_status == "connected" else "failed",
            "details": "Local DuckDB columnar engine connected" if duckdb_status == "connected" else "Database connection error"
        },
        "chromadb": {
            "status": "ok" if chroma_status == "connected" else "degraded",
            "details": "Local ChromaDB vector store ready" if chroma_status == "connected" else "Local vector fallback active"
        },
        "licensing": {
            "status": "ok" if license_status in (LicenseStatus.VALID, LicenseStatus.EXPIRING_SOON, LicenseStatus.GRACE_PERIOD) else "degraded",
            "details": license_status.value
        },
        "ollama": {
            "status": "ok" if ollama_status == "connected" else "degraded",
            "details": "Local Ollama LLM service online" if ollama_status == "connected" else "Local Ollama offline or starting"
        }
    }

    return {
        "ready": is_ready,
        "subsystems": subsystems_dict,
        "stages": {
            "licensing": subsystems_dict["licensing"],
            "database": subsystems_dict["duckdb"],
            "knowledge": subsystems_dict["chromadb"],
            "ollama": subsystems_dict["ollama"]
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
    """Retrieve dynamic insights, top performers, and analytical highlights based on active DuckDB tables."""
    insights = []
    
    try:
        conn = db_manager.get_connection()
        system_tables = {
            "users", "organizations", "data_sources", "queries", "dashboards", 
            "reports", "documents", "audit_logs", "roles", "permissions", 
            "user_roles", "role_permissions", "role_hierarchy", "access_scopes", 
            "user_access_scopes", "branches", "departments", "jobs",
            "conversations", "conversation_messages", "dataset_versions",
            "document_versions", "sync_history"
        }
        all_tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
        user_tables = [t for t in all_tables if t.lower() not in system_tables]

        for tname in user_tables:
            try:
                row_cnt = conn.execute(f"SELECT COUNT(*) FROM {tname}").fetchone()[0]
                if row_cnt == 0:
                    continue

                cols_info = conn.execute(f"DESCRIBE {tname}").fetchall()
                col_names = [c[0] for c in cols_info]
                
                # Find monetary / numeric columns
                monetary_cols = [c for c in col_names if any(kw in c.lower() for kw in ["amount", "price", "sales", "revenue", "cost", "inr", "charge", "val", "fee", "total"])]
                text_cols = [c for c in col_names if any(kw in c.lower() for kw in ["store", "region", "category", "model", "name", "item", "product", "branch", "customer"])]
                status_cols = [c for c in col_names if any(kw in c.lower() for kw in ["status", "payment", "state"])]

                # 1. Top Performer Insight
                if monetary_cols and text_cols:
                    m_col = monetary_cols[0]
                    t_col = text_cols[0]
                    clean_m = f"COALESCE(TRY_CAST(REGEXP_REPLACE(CAST({m_col} AS VARCHAR), '[^0-9.]', '', 'g') AS DOUBLE), 0)"
                    
                    top_res = conn.execute(f"""
                        SELECT {t_col}, SUM({clean_m}) as total_val
                        FROM {tname}
                        WHERE {t_col} IS NOT NULL AND {clean_m} > 0
                        GROUP BY {t_col}
                        ORDER BY total_val DESC
                        LIMIT 1
                    """).fetchone()

                    if top_res and top_res[0] and top_res[1]:
                        top_entity = str(top_res[0]).strip()
                        top_amount = float(top_res[1])
                        is_inr = any(kw in m_col.lower() or kw in tname.lower() for kw in ["inr", "rs", "rupee", "₹", "india"])
                        sym = "₹" if is_inr else "$"
                        
                        insights.append({
                            "title": f"Top Performer: {top_entity}",
                            "priority": "Revenue Opportunity",
                            "message": f"In dataset '{tname.replace('_', ' ').title()}', '{top_entity}' leads with total {m_col.replace('_', ' ').title()} of {sym}{top_amount:,.2f}.",
                            "type": "success"
                        })

                # 2. Status Distribution Insight
                if status_cols:
                    s_col = status_cols[0]
                    stat_res = conn.execute(f"""
                        SELECT {s_col}, COUNT(*) 
                        FROM {tname} 
                        WHERE {s_col} IS NOT NULL 
                        GROUP BY {s_col} 
                        ORDER BY COUNT(*) DESC
                    """).fetchall()

                    if stat_res:
                        stat_summary = ", ".join([f"{r[1]} {r[0]}" for r in stat_res[:3]])
                        insights.append({
                            "title": f"Status Analysis: {tname.replace('_', ' ').title()}",
                            "priority": "Operational Status",
                            "message": f"Dataset '{tname.replace('_', ' ').title()}' status breakdown: {stat_summary}.",
                            "type": "info"
                        })

                # 3. Overall Dataset Tracking Insight
                insights.append({
                    "title": f"Dataset Active: {tname.replace('_', ' ').title()}",
                    "priority": "Real-time Monitoring",
                    "message": f"Currently tracking {row_cnt:,} records across {len(col_names)} attributes in DuckDB table '{tname}'.",
                    "type": "info"
                })

            except Exception as fe:
                logger.warning(f"Dynamic insight computation notice for table {tname}: {str(fe)}")

    except Exception as e:
        logger.error(f"Failed to compute dynamic analytics insights: {str(e)}")

    if not insights:
        insights = [
            {
                "title": "System Ready",
                "priority": "Active Tracking",
                "message": "Upload CSV/Excel data sources to generate automated business intelligence, revenue alerts, and status breakdowns.",
                "type": "info"
            }
        ]

    return {"insights": insights}

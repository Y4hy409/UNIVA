"""
CLARIUS Backend - Main Application Entrypoint

This module bootstraps the FastAPI application, sets up middleware (CORS, safety),
defines lifespan initialization events (DuckDB table generation, ChromaDB verification),
and registers the routing modules.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.infrastructure.database import db_manager
from app.infrastructure.knowledge import knowledge_manager
from app.api import startup, auth, analytics, sse_streaming, upgrade as upgrade_api, admin
from app.infrastructure.jobs import api as jobs_api
from app.modules.data_sources.api import routes as data_sources_api
from app.modules.documents.api import routes as documents_api
from app.modules.dashboards.api import routes as dashboards_api
from app.modules.audit.api import routes as audit_api
from app.modules.audit.application.audit_service import register_audit_event_subscribers

from app.infrastructure.jobs.workers import worker_pool
from app.infrastructure.jobs.registry import register_job_handler
from app.modules.data_sources.application.importer import import_csv_handler, import_excel_handler
from app.modules.documents.api.routes import process_document_job_handler

from app.modules.catalog.api import routes as catalog_api

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Boot sequence - Initialize DuckDB CDM schemas
    db_manager.initialize_schema()
    
    # 2. Try initializing ChromaDB (fail-safe)
    try:
        knowledge_manager.get_client()
    except Exception:
        # ChromaDB package or persistence issues won't crash the server bootstrap
        pass
        
    # 3. Register background job handlers
    register_job_handler("import.csv", import_csv_handler)
    register_job_handler("import.excel", import_excel_handler)
    register_job_handler("document.process", process_document_job_handler)
    
    # 4. Subscribe audit logger handlers to Event Bus
    register_audit_event_subscribers()
    
    # 5. Start background job worker pool
    worker_pool.start()
    
    yield
    
    # 4. Shutdown background workers
    await worker_pool.stop()
    
    # 5. Shutdown database connections
    db_manager.close()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan
)

# CORS middleware for local frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register endpoints
app.include_router(startup.router)
app.include_router(auth.router)
app.include_router(jobs_api.router)
app.include_router(data_sources_api.router)
app.include_router(analytics.router)
app.include_router(documents_api.router)
app.include_router(catalog_api.router)
app.include_router(sse_streaming.router)
app.include_router(dashboards_api.router)
app.include_router(audit_api.router)
app.include_router(upgrade_api.router)
app.include_router(admin.router)
app.include_router(admin.upgrade_router)

@app.get("/")
async def root():
    """Simple root message."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online"
    }

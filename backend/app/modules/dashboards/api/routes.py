"""
CLARIUS Backend - Dashboards API Routes

This module exposes CRUD routes for dashboards and KPI widgets (ADR-000).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import duckdb

from app.infrastructure.database import get_db
from app.modules.dashboards.application.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboards", tags=["dashboards"])

class WidgetConfig(BaseModel):
    title: str
    type: str
    chart_options: Optional[Dict[str, Any]] = None


class DashboardCreateRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    owner_id: str
    widgets: List[WidgetConfig]
    layout: Dict[str, Any]


class DashboardResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    owner_id: str
    widgets: List[Dict[str, Any]]
    layout: Dict[str, Any]
    is_shared: bool
    created_at: str
    updated_at: str


@router.get("", response_model=List[DashboardResponse])
async def list_dashboards(db: duckdb.DuckDBPyConnection = Depends(get_db)):
    """Retrieve all dashboard templates and custom layouts."""
    service = DashboardService(db)
    dashboards = service.list_dashboards()
    
    filtered_dashboards = []
    for d in dashboards:
        table_name = d.name.lower().replace(" ", "_")
        try:
            cursor = db.execute("SELECT count(*) FROM information_schema.tables WHERE table_name = ?", [table_name])
            exists = cursor.fetchone()[0] > 0
            if exists:
                filtered_dashboards.append(d)
        except Exception:
            # If information_schema isn't populated or query fails, skip checking
            pass
            
    return [_to_response(d) for d in filtered_dashboards]


@router.get("/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(dashboard_id: str, db: duckdb.DuckDBPyConnection = Depends(get_db)):
    """Retrieve details of a dashboard by ID."""
    service = DashboardService(db)
    dash = service.get_dashboard(dashboard_id)
    if not dash:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dashboard {dashboard_id} not found."
        )
    return _to_response(dash)


@router.post("", response_model=DashboardResponse, status_code=status.HTTP_201_CREATED)
async def create_dashboard(req: DashboardCreateRequest, db: duckdb.DuckDBPyConnection = Depends(get_db)):
    """Create a new dashboard configuration."""
    service = DashboardService(db)
    widgets_dict = [w.dict() for w in req.widgets]
    dash = service.create_dashboard(
        name=req.name,
        description=req.description,
        owner_id=req.owner_id,
        widgets=widgets_dict,
        layout=req.layout
    )
    return _to_response(dash)


@router.put("/{dashboard_id}", response_model=DashboardResponse)
async def update_dashboard(dashboard_id: str, req: DashboardCreateRequest, db: duckdb.DuckDBPyConnection = Depends(get_db)):
    """Modify widgets or layouts on a dashboard."""
    service = DashboardService(db)
    widgets_dict = [w.dict() for w in req.widgets]
    dash = service.update_dashboard(
        dashboard_id=dashboard_id,
        name=req.name,
        description=req.description,
        widgets=widgets_dict,
        layout=req.layout
    )
    if not dash:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dashboard {dashboard_id} not found."
        )
    return _to_response(dash)


@router.delete("/{dashboard_id}")
async def delete_dashboard(dashboard_id: str, db: duckdb.DuckDBPyConnection = Depends(get_db)):
    """Delete a dashboard configuration."""
    service = DashboardService(db)
    if not service.delete_dashboard(dashboard_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dashboard {dashboard_id} not found."
        )
    return {"message": "Dashboard deleted successfully."}


def _to_response(dash) -> DashboardResponse:
    return DashboardResponse(
        id=str(dash.id),
        name=dash.name,
        description=dash.description,
        owner_id=str(dash.owner_id),
        widgets=dash.widgets,
        layout=dash.layout,
        is_shared=dash.is_shared,
        created_at=dash.created_at.isoformat(),
        updated_at=dash.updated_at.isoformat()
    )

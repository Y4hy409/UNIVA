"""
CLARIUS Backend - Edition Gated Stubs

This module implements capability checking stubs for CLARIUS Copilot and UNIVA
returning upgrade requirements (402 Payment Required) for unlicensed calls (ADR-006).
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any

from app.infrastructure.licensing import capability_service

router = APIRouter(prefix="/editions", tags=["upgrade-gating"])

class GatedResponse(BaseModel):
    status: str
    message: str
    edition_required: str


@router.get("/predictive-analytics", response_model=GatedResponse)
async def get_predictive_analytics():
    """Predictive analytics endpoint gated by 'copilot.predictive_analytics' capability."""
    cap = "copilot.predictive_analytics"
    if not capability_service.has_capability(cap):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "message": "Predictive Analytics is a CLARIUS Copilot feature.",
                "edition_required": "CLARIUS Copilot"
            }
        )
    return GatedResponse(
        status="active",
        message="CLARIUS Copilot active. Running predictive forecasting models...",
        edition_required="CLARIUS Copilot"
    )


@router.get("/workflow-automation", response_model=GatedResponse)
async def get_workflow_automation():
    """Autonomous workflow automation endpoint gated by 'univa.workflow_automation'."""
    cap = "univa.workflow_automation"
    if not capability_service.has_capability(cap):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "message": "Autonomous workflows require UNIVA capability.",
                "edition_required": "UNIVA"
            }
        )
    return GatedResponse(
        status="active",
        message="UNIVA active. Running autonomous scheduling loops...",
        edition_required="UNIVA"
    )

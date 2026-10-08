"""
CLARIUS Backend - Business Memory REST API Router

Provides secure, tenant-isolated endpoints for:
- Cross-functional context retrieval (CLARIUS, Copilot, Dashboards, Reports, Agents)
- Analytical artifact management, inspection, and revalidation
- Business definition registry and user corrections
- Decision and recommendation tracking
- Human-in-the-Loop (HITL) approval workflows
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from pydantic import BaseModel, Field

from app.api.dependencies import RoleChecker
from app.domain.entities import UserRole
from app.domain.memory_models import (
    MemoryCategory,
    ProvenanceSource,
    InformationType,
    MemoryStatus,
    ApprovalStatus,
    BusinessMemoryItem,
    AnalyticalArtifact,
    BusinessDefinition,
    RecommendationRecord,
    HITLApprovalRequest,
    ContextRetrievalResult
)
from app.application.memory.business_memory_service import business_memory_service
from app.application.memory.context_retrieval_service import context_retrieval_service
from app.application.memory.hitl_service import hitl_service

logger = logging.getLogger("clarius.api.memory")

router = APIRouter(prefix="/memory", tags=["business-memory"])


class ContextRetrievalRequest(BaseModel):
    query: str
    intent: Optional[str] = None
    target_function: str = Field(default="clarius", description="clarius, copilot, dashboard, report, agent_finance, agent_inventory, etc.")
    workspace_id: Optional[str] = "default_workspace"
    datasets: Optional[List[str]] = None
    entities: Optional[List[str]] = None
    time_range: Optional[Dict[str, Any]] = None
    limit: int = 10


class CreateDefinitionRequest(BaseModel):
    term: str
    definition: str
    domain: Optional[str] = "general"
    calculation_sql: Optional[str] = None
    target_table: Optional[str] = None
    target_column: Optional[str] = None
    workspace_id: Optional[str] = "default_workspace"
    is_approved: bool = True


class UserCorrectionRequest(BaseModel):
    original_statement: str
    corrected_statement: str
    domain: Optional[str] = "general"
    conversation_id: Optional[str] = None
    workspace_id: Optional[str] = "default_workspace"
    promote_to_definition: bool = False


class HITLDecisionRequest(BaseModel):
    action: str = Field(..., description="'approve', 'reject', or 'clarify'")
    clarification_response: Optional[str] = None
    notes: Optional[str] = None


class MemoryFeedbackRequest(BaseModel):
    memory_id: str
    rating: int = Field(..., ge=1, le=5)
    feedback_text: Optional[str] = None


@router.post("/context", response_model=Dict[str, Any])
async def retrieve_cross_functional_context(
    req: ContextRetrievalRequest,
    user=Depends(RoleChecker([UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER, UserRole.ANALYST, UserRole.STAFF]))
):
    """
    Retrieve relevance-scored, verified business context across functions (CLARIUS, Copilot, Dashboard, Report, Agents).
    Applies strict tenant isolation and role validation.
    """
    user_id = getattr(user, "id", getattr(user, "username", "anonymous_user"))
    workspace_id = getattr(user, "workspace_id", req.workspace_id or "default_workspace")
    role = getattr(user, "role", "ANALYST")
    if hasattr(role, "value"):
        role = role.value

    result: ContextRetrievalResult = context_retrieval_service.retrieve_context(
        user_id=user_id,
        workspace_id=workspace_id,
        user_role=role,
        current_query=req.query,
        current_intent=req.intent,
        target_function=req.target_function,
        datasets=req.datasets,
        entities=req.entities,
        time_range=req.time_range,
        limit=req.limit
    )

    return result.to_dict()


@router.get("/artifacts", response_model=List[Dict[str, Any]])
async def list_analytical_artifacts(
    dataset_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(RoleChecker([UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER, UserRole.ANALYST, UserRole.STAFF]))
):
    """List reusable analytical artifacts for dashboards, reports, and copilot."""
    workspace_id = getattr(user, "workspace_id", "default_workspace")
    user_id = getattr(user, "id", getattr(user, "username", "anonymous_user"))

    artifacts = business_memory_service.get_analytical_artifacts(
        workspace_id=workspace_id,
        user_id=user_id,
        dataset_name=dataset_name,
        status=status,
        limit=limit
    )
    return [a.to_dict() for a in artifacts]


@router.get("/artifacts/{artifact_id}", response_model=Dict[str, Any])
async def get_analytical_artifact(
    artifact_id: str,
    user=Depends(RoleChecker([UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER, UserRole.ANALYST, UserRole.STAFF]))
):
    """Retrieve details and lineage for a specific analytical artifact."""
    workspace_id = getattr(user, "workspace_id", "default_workspace")
    artifact = business_memory_service.get_artifact(artifact_id, workspace_id)
    if not artifact:
        raise HTTPException(status_code=404, detail=f"Analytical artifact '{artifact_id}' not found.")
    return artifact.to_dict()


@router.post("/artifacts/{artifact_id}/revalidate", response_model=Dict[str, Any])
async def revalidate_analytical_artifact(
    artifact_id: str,
    user=Depends(RoleChecker([UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER, UserRole.ANALYST]))
):
    """
    Re-run the analytical query against the latest dataset version if the artifact became stale or requires revalidation.
    """
    workspace_id = getattr(user, "workspace_id", "default_workspace")
    revalidated = business_memory_service.revalidate_artifact(artifact_id, workspace_id)
    if not revalidated:
        raise HTTPException(status_code=400, detail=f"Could not revalidate artifact '{artifact_id}'. Check schema or dataset existence.")
    return {"status": "success", "artifact": revalidated.to_dict()}


@router.get("/definitions", response_model=List[Dict[str, Any]])
async def list_business_definitions(
    domain: Optional[str] = Query(None),
    term: Optional[str] = Query(None),
    user=Depends(RoleChecker([UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER, UserRole.ANALYST, UserRole.STAFF]))
):
    """List approved business terminology and metric definitions."""
    workspace_id = getattr(user, "workspace_id", "default_workspace")
    defs = business_memory_service.get_business_definitions(
        workspace_id=workspace_id,
        domain=domain,
        term=term,
        only_approved=True
    )
    return [d.to_dict() for d in defs]


@router.post("/definitions", response_model=Dict[str, Any])
async def create_business_definition(
    req: CreateDefinitionRequest,
    user=Depends(RoleChecker([UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER]))
):
    """Register an approved business rule or definition."""
    user_id = getattr(user, "id", getattr(user, "username", "anonymous_user"))
    workspace_id = getattr(user, "workspace_id", req.workspace_id or "default_workspace")

    definition = business_memory_service.register_business_definition(
        term=req.term,
        definition=req.definition,
        domain=req.domain or "general",
        calculation_sql=req.calculation_sql,
        target_table=req.target_table,
        target_column=req.target_column,
        user_id=user_id,
        workspace_id=workspace_id,
        is_approved=req.is_approved
    )
    return {"status": "success", "definition": definition.to_dict()}


@router.post("/corrections", response_model=Dict[str, Any])
async def record_user_correction(
    req: UserCorrectionRequest,
    user=Depends(RoleChecker([UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER, UserRole.ANALYST, UserRole.STAFF]))
):
    """Record an explicit user correction to steer future analysis."""
    user_id = getattr(user, "id", getattr(user, "username", "anonymous_user"))
    workspace_id = getattr(user, "workspace_id", req.workspace_id or "default_workspace")

    mem_item = business_memory_service.record_user_correction(
        user_id=user_id,
        workspace_id=workspace_id,
        original_statement=req.original_statement,
        corrected_statement=req.corrected_statement,
        domain=req.domain or "general",
        conversation_id=req.conversation_id,
        promote_to_definition=req.promote_to_definition
    )
    return {"status": "success", "memory_item": mem_item.to_dict()}


@router.get("/recommendations", response_model=List[Dict[str, Any]])
async def list_recommendations(
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(RoleChecker([UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER, UserRole.ANALYST, UserRole.STAFF]))
):
    """List recommendations with clear separation from verified facts."""
    workspace_id = getattr(user, "workspace_id", "default_workspace")
    recs = business_memory_service.get_recommendations(workspace_id=workspace_id, status=status, limit=limit)
    return [r.to_dict() for r in recs]


@router.post("/recommendations/{recommendation_id}/approve", response_model=Dict[str, Any])
async def decide_recommendation(
    recommendation_id: str,
    action: str = Query(..., regex="^(approve|reject)$"),
    user=Depends(RoleChecker([UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER]))
):
    """Approve or reject a business recommendation."""
    workspace_id = getattr(user, "workspace_id", "default_workspace")
    user_id = getattr(user, "id", getattr(user, "username", "anonymous_user"))

    approved = action.lower() == "approve"
    rec = business_memory_service.approve_recommendation(
        recommendation_id=recommendation_id,
        approved_by=user_id,
        approved=approved,
        workspace_id=workspace_id
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found.")
    return {"status": "success", "recommendation": rec.to_dict()}


@router.get("/approvals", response_model=List[Dict[str, Any]])
async def list_pending_approvals(
    user=Depends(RoleChecker([UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER]))
):
    """List pending HITL approval and clarification requests."""
    workspace_id = getattr(user, "workspace_id", "default_workspace")
    requests = hitl_service.get_pending_requests(workspace_id=workspace_id)
    return [r.to_dict() for r in requests]


@router.post("/approvals/{request_id}/respond", response_model=Dict[str, Any])
async def respond_to_hitl_request(
    request_id: str,
    req: HITLDecisionRequest,
    user=Depends(RoleChecker([UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER]))
):
    """Submit human decision / clarification on an approval request."""
    user_id = getattr(user, "id", getattr(user, "username", "anonymous_user"))
    workspace_id = getattr(user, "workspace_id", "default_workspace")

    updated = hitl_service.submit_decision(
        request_id=request_id,
        action=req.action,
        decided_by=user_id,
        clarification_response=req.clarification_response,
        notes=req.notes,
        workspace_id=workspace_id
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Approval request not found.")
    return {"status": "success", "request": updated.to_dict()}

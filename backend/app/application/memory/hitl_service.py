"""
CLARIUS / UNIVA Backend - Human-in-the-Loop (HITL) Service

Evaluates operational risk, resolves memory conflicts, gates consequential actions,
and coordinates user clarification workflows.
"""

import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

import duckdb
from app.infrastructure.database import db_manager
from app.infrastructure.memory_repository import DuckDBBusinessMemoryRepository
from app.domain.memory_models import (
    HITLApprovalRequest,
    ApprovalStatus,
    ContextRetrievalResult,
)

logger = logging.getLogger("clarius.memory.hitl")


class HITLService:
    """Enterprise Human-in-the-Loop policy evaluator and request manager."""

    CONSEQUENTIAL_KEYWORDS = {
        "delete", "drop", "purge", "truncate", "update", "modify", "override",
        "send email", "notify customer", "execute payment", "cancel order",
        "external action", "reorder stock", "approve budget"
    }

    def __init__(self, repo: Optional[DuckDBBusinessMemoryRepository] = None, db_conn: Optional[duckdb.DuckDBPyConnection] = None):
        self.conn = db_conn or db_manager.get_connection()
        self.repo = repo or DuckDBBusinessMemoryRepository(self.conn)

    def evaluate_request(
        self,
        query: str,
        context_result: ContextRetrievalResult,
        target_function: str = "CLARIUS",
        user_id: str = "default_user",
        workspace_id: str = "default_workspace"
    ) -> Dict[str, Any]:
        """
        Evaluate if a user query or agent action requires human approval/clarification.
        """
        q_lower = query.strip().lower()

        # 1. Check if context retrieval detected conflicting definitions or ambiguous temporal periods
        if context_result.hitl_required:
            req = self.create_approval_request(
                request_type="AMBIGUITY_CLARIFICATION",
                description=context_result.hitl_reason or "Clarification required",
                context_data={
                    "query": query,
                    "options": context_result.hitl_options,
                    "target_function": target_function
                },
                user_id=user_id,
                workspace_id=workspace_id
            )
            return {
                "requires_approval": True,
                "request_id": req.id,
                "reason": context_result.hitl_reason,
                "options": context_result.hitl_options,
                "prompt_message": f"I found multiple possibilities: {context_result.hitl_reason} Please select an option."
            }

        # 2. Check for consequential agent actions or data mutations
        if any(kw in q_lower for kw in self.CONSEQUENTIAL_KEYWORDS):
            req = self.create_approval_request(
                request_type="CONSEQUENTIAL_ACTION",
                description=f"Action '{query[:80]}' requires explicit authorization.",
                context_data={"query": query, "target_function": target_function},
                user_id=user_id,
                workspace_id=workspace_id
            )
            return {
                "requires_approval": True,
                "request_id": req.id,
                "reason": "Consequential action requested.",
                "options": ["Approve", "Cancel"],
                "prompt_message": f"This action ({query[:60]}) involves consequential system modifications. Please confirm to proceed."
            }

        return {
            "requires_approval": False,
            "request_id": None,
            "reason": "Normal analytical query",
            "options": [],
            "prompt_message": ""
        }

    def create_approval_request(
        self,
        request_type: str,
        description: str,
        context_data: Dict[str, Any],
        user_id: str = "default_user",
        workspace_id: str = "default_workspace",
        target_function: Optional[str] = None
    ) -> HITLApprovalRequest:
        """Log a new pending HITL request."""
        if target_function:
            context_data["target_function"] = target_function

        req = HITLApprovalRequest(
            id=f"hitl_{uuid.uuid4().hex[:12]}",
            request_type=request_type,
            description=description,
            context_data=context_data,
            status=ApprovalStatus.PENDING,
            user_id=user_id,
            workspace_id=workspace_id,
            created_at=datetime.utcnow()
        )
        return self.repo.save_approval_request(req)

    def resolve_request(
        self,
        request_id: str,
        status: ApprovalStatus,
        resolution_notes: Optional[str] = None
    ) -> bool:
        """Resolve a pending HITL request."""
        return self.repo.resolve_approval_request(request_id, status)

    def resolve_approval_request(
        self,
        request_id: str,
        status: ApprovalStatus,
        response_text: Optional[str] = None
    ) -> HITLApprovalRequest:
        """Resolve and return the updated approval request."""
        self.repo.resolve_approval_request(request_id, status)
        reqs = self.repo.get_approval_requests(limit=50)
        for r in reqs:
            if r.id == request_id:
                if response_text:
                    r.response_text = response_text
                return r
        return HITLApprovalRequest(
            id=request_id,
            request_type="ACTION",
            description="",
            context_data={},
            status=status,
            user_id="default_user",
            workspace_id="default_workspace",
            created_at=datetime.utcnow()
        )

    def get_pending_requests(self, workspace_id: str = "default_workspace") -> List[HITLApprovalRequest]:
        """Fetch all pending approval requests for a workspace."""
        return self.repo.get_approval_requests(workspace_id=workspace_id, status=ApprovalStatus.PENDING)

    def submit_decision(
        self,
        request_id: str,
        action: str,
        decided_by: str,
        clarification_response: Optional[str] = None,
        notes: Optional[str] = None,
        workspace_id: str = "default_workspace"
    ) -> Optional[HITLApprovalRequest]:
        """Submit decision for an approval request."""
        act_l = action.lower()
        new_status = ApprovalStatus.APPROVED if act_l == "approve" else (ApprovalStatus.REJECTED if act_l == "reject" else ApprovalStatus.PENDING)
        return self.resolve_approval_request(request_id, new_status, response_text=clarification_response or notes)


# Global singleton
hitl_service = HITLService()

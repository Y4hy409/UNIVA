"""
CLARIUS / UNIVA Backend - Business Memory Domain Models

Defines domain entities, enums, categories, provenance types, and lifecycle states
for the unified Cross-Functional Business Memory Layer.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


class MemoryCategory(str, Enum):
    CONVERSATIONAL_CONTEXT = "CONVERSATIONAL_CONTEXT"
    ANALYTICAL_MEMORY = "ANALYTICAL_MEMORY"
    BUSINESS_KNOWLEDGE = "BUSINESS_KNOWLEDGE"
    DATASET_MEMORY = "DATASET_MEMORY"
    ANALYTICAL_ARTIFACT = "ANALYTICAL_ARTIFACT"
    DECISION_MEMORY = "DECISION_MEMORY"
    USER_PREFERENCE = "USER_PREFERENCE"
    RECOMMENDATION = "RECOMMENDATION"


class ProvenanceSource(str, Enum):
    DATABASE = "DATABASE"
    CSV = "CSV"
    EXCEL = "EXCEL"
    ERP = "ERP"
    API = "API"
    DOCUMENT = "DOCUMENT"
    RAG = "RAG"
    USER_EXPLICIT = "USER_EXPLICIT"
    USER_CORRECTION = "USER_CORRECTION"
    ANALYTICAL_RESULT = "ANALYTICAL_RESULT"
    SYSTEM_DERIVED = "SYSTEM_DERIVED"
    AGENT_DERIVED = "AGENT_DERIVED"
    MODEL_INFERENCE = "MODEL_INFERENCE"


class InformationType(str, Enum):
    FACT = "FACT"
    DERIVED_RESULT = "DERIVED_RESULT"
    INTERPRETATION = "INTERPRETATION"
    RECOMMENDATION = "RECOMMENDATION"
    USER_PROVIDED_CONTEXT = "USER_PROVIDED_CONTEXT"
    MODEL_INFERENCE = "MODEL_INFERENCE"


class MemoryStatus(str, Enum):
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    REQUIRES_REVALIDATION = "REQUIRES_REVALIDATION"
    INVALIDATED = "INVALIDATED"
    ARCHIVED = "ARCHIVED"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    AUTO_APPROVED = "AUTO_APPROVED"


@dataclass
class BusinessMemoryItem:
    """Core structured memory record with strict provenance and lifecycle validity."""
    id: str
    category: MemoryCategory
    user_id: str
    workspace_id: str
    title: str
    content: str
    structured_data: Dict[str, Any] = field(default_factory=dict)
    provenance_source: ProvenanceSource = ProvenanceSource.SYSTEM_DERIVED
    info_type: InformationType = InformationType.DERIVED_RESULT
    status: MemoryStatus = MemoryStatus.ACTIVE
    confidence: float = 1.0
    source_dataset: Optional[str] = None
    source_version: Optional[int] = None
    entity_tags: List[str] = field(default_factory=list)
    metric_tags: List[str] = field(default_factory=list)
    time_range: Optional[Dict[str, Any]] = None
    is_verified: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AnalyticalArtifact:
    """Reusable analytical work containing executable SQL, filters, measures, and dataset lineage."""
    id: str
    memory_id: str
    name: str
    query_text: str
    generated_sql: str
    filters: Dict[str, Any] = field(default_factory=dict)
    dimensions: List[str] = field(default_factory=list)
    measures: List[str] = field(default_factory=list)
    dataset_name: str = ""
    dataset_version: int = 1
    result_metadata: Dict[str, Any] = field(default_factory=dict)
    chart_config: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    status: MemoryStatus = MemoryStatus.ACTIVE
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BusinessDefinition:
    """Explicitly confirmed and approved business definitions, terminology, and KPI formulas."""
    id: str
    term: str
    definition: str
    formula: Optional[str] = None
    workspace_id: str = "default_workspace"
    is_approved: bool = True
    approved_by: str = "system"
    status: MemoryStatus = MemoryStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RecommendationRecord:
    """Isolated recommendation carrying supporting facts, reasoning, and approval lifecycle."""
    id: str
    title: str
    recommendation_text: str
    supporting_facts: List[str] = field(default_factory=list)
    analytical_artifact_ids: List[str] = field(default_factory=list)
    reasoning: str = ""
    confidence: float = 0.85
    generated_by: str = "CLARIUS Copilot"
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    approved_by: Optional[str] = None
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class HITLApprovalRequest:
    """Human-in-the-Loop request for ambiguous queries, conflicting memories, or consequential actions."""
    id: str
    request_type: str  # "AMBIGUITY_CLARIFICATION", "CONFLICT_RESOLUTION", "CONSEQUENTIAL_ACTION", "DATA_MUTATION"
    description: str
    context_data: Dict[str, Any] = field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    user_id: str = "default_user"
    workspace_id: str = "default_workspace"
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None


@dataclass
class ContextRetrievalResult:
    """Structured context package returned by ContextRetrievalService across target functions."""
    memories: List[BusinessMemoryItem] = field(default_factory=list)
    analytical_artifacts: List[AnalyticalArtifact] = field(default_factory=list)
    dataset_context: Dict[str, Any] = field(default_factory=dict)
    business_definitions: List[BusinessDefinition] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    decisions: List[BusinessMemoryItem] = field(default_factory=list)
    recommendations: List[RecommendationRecord] = field(default_factory=list)
    overall_confidence: float = 1.0
    validity_status: MemoryStatus = MemoryStatus.ACTIVE
    hitl_required: bool = False
    hitl_reason: Optional[str] = None
    hitl_options: List[str] = field(default_factory=list)

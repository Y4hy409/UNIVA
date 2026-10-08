"""
CLARIUS / UNIVA Backend - Context Retrieval Service

Multi-signal relevance retrieval and confidence scoring engine.
Presents structured, authorized, and validated business memory to target functions
(CLARIUS, Copilot, Dashboards, Reports, RAG, Specialized Agents).
"""

import re
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime

import duckdb
from app.infrastructure.database import db_manager
from app.infrastructure.memory_repository import DuckDBBusinessMemoryRepository
from app.domain.memory_models import (
    BusinessMemoryItem,
    AnalyticalArtifact,
    BusinessDefinition,
    RecommendationRecord,
    ContextRetrievalResult,
    MemoryCategory,
    ProvenanceSource,
    InformationType,
    MemoryStatus,
    ApprovalStatus,
)

logger = logging.getLogger("clarius.memory.context_retrieval")


class ContextRetrievalService:
    """Enterprise multi-signal relevance retrieval service."""

    def __init__(self, repo: Optional[DuckDBBusinessMemoryRepository] = None, db_conn: Optional[duckdb.DuckDBPyConnection] = None):
        self.conn = db_conn or db_manager.get_connection()
        self.repo = repo or DuckDBBusinessMemoryRepository(self.conn)

    def retrieve_context(
        self,
        query: str,
        user_id: str = "default_user",
        workspace_id: str = "default_workspace",
        intent: Optional[str] = None,
        target_function: str = "CLARIUS",  # "CLARIUS", "COPILOT", "DASHBOARDS", "REPORTS", "RAG", "ANALYTICS", "AGENT"
        datasets: Optional[List[str]] = None,
        entities: Optional[List[str]] = None,
        time_range: Optional[Dict[str, Any]] = None,
        agent_domain: Optional[str] = None
    ) -> ContextRetrievalResult:
        """
        Main retrieval entry point.
        Executes multi-signal scoring, entity matching, provenance weighting,
        conflict detection, and returns a structured ContextRetrievalResult.
        """
        clean_q = query.strip().lower()
        q_tokens = set(re.findall(r"\w+", clean_q))

        # 1. Extract query signals
        extracted_entities = set(entities or []) | self._extract_entities(clean_q)
        extracted_metrics = self._extract_metrics(clean_q)

        # 2. Fetch memory candidates from repository with tenant/user isolation
        all_memories = self.repo.query_memories(
            user_id=user_id,
            workspace_id=workspace_id,
            limit=50
        )
        all_artifacts = self.repo.query_artifacts(
            user_id=user_id,
            workspace_id=workspace_id,
            limit=30
        )
        all_definitions = self.repo.get_definitions(workspace_id=workspace_id)

        # 3. Domain filtering for specialized agents (RBAC / Agent scope isolation)
        if target_function == "AGENT" and agent_domain:
            all_memories = self._filter_agent_domain(all_memories, agent_domain)
            all_artifacts = self._filter_agent_domain(all_artifacts, agent_domain)

        # 4. Multi-Signal Scoring for Memories
        scored_memories: List[Tuple[float, BusinessMemoryItem]] = []
        for mem in all_memories:
            score = self._compute_memory_score(mem, q_tokens, extracted_entities, extracted_metrics, datasets, target_function)
            if score >= 0.35:
                scored_memories.append((score, mem))

        scored_memories.sort(key=lambda x: x[0], reverse=True)
        top_memories = [m for s, m in scored_memories[:8]]

        # 5. Multi-Signal Scoring for Analytical Artifacts
        scored_artifacts: List[Tuple[float, AnalyticalArtifact]] = []
        for art in all_artifacts:
            score = self._compute_artifact_score(art, q_tokens, extracted_entities, extracted_metrics, datasets, target_function)
            if score >= 0.35:
                scored_artifacts.append((score, art))

        scored_artifacts.sort(key=lambda x: x[0], reverse=True)
        top_artifacts = [a for s, a in scored_artifacts[:5]]

        # 6. Match Business Definitions
        matched_definitions: List[BusinessDefinition] = []
        for bdef in all_definitions:
            if bdef.term.lower() in clean_q or any(token in bdef.term.lower() for token in q_tokens):
                matched_definitions.append(bdef)

        # 7. Match Decisions & Preferences
        decisions = [m for m in top_memories if m.category == MemoryCategory.DECISION_MEMORY]
        user_preferences = {}
        for m in top_memories:
            if m.category == MemoryCategory.USER_PREFERENCE:
                user_preferences.update(m.structured_data)

        # 8. Fetch Recommendations (if Copilot or Recommendation requested)
        recommendations = []
        if target_function in {"COPILOT", "RECOMMENDATIONS", "CLARIUS"}:
            recommendations = self.repo.get_recommendations(user_id=user_id, workspace_id=workspace_id, limit=5)

        # 9. Conflict Detection & HITL Evaluation
        hitl_required = False
        hitl_reason = None
        hitl_options = []

        # Conflict check A: Multiple conflicting active business definitions for the same term
        def_map: Dict[str, List[BusinessDefinition]] = {}
        for d in matched_definitions:
            def_map.setdefault(d.term.lower(), []).append(d)
        for term, def_list in def_map.items():
            if len(def_list) > 1 and len(set(d.definition.lower() for d in def_list)) > 1:
                hitl_required = True
                hitl_reason = f"Conflicting definitions found for '{term}'."
                hitl_options = [f"{d.term}: {d.definition}" for d in def_list]

        # Conflict check B: Ambiguous query with multiple candidate artifacts from different time periods (e.g., 2024 vs 2025)
        if len(top_artifacts) >= 2 and ("compare" not in clean_q and "versus" not in clean_q):
            art1_years = set(re.findall(r"\b20\d\d\b", top_artifacts[0].query_text))
            art2_years = set(re.findall(r"\b20\d\d\b", top_artifacts[1].query_text))
            if art1_years and art2_years and art1_years != art2_years and not (art1_years & set(re.findall(r"\b20\d\d\b", clean_q))):
                if any(w in clean_q for w in ["plot", "show", "chart", "the sales", "that analysis"]):
                    hitl_required = True
                    hitl_reason = f"Multiple analyses found for different periods ({', '.join(art1_years | art2_years)})."
                    hitl_options = [f"{a.name} ({a.query_text})" for a in top_artifacts[:3]]

        # 10. Compute Overall Confidence & Validity
        top_score = scored_memories[0][0] if scored_memories else (scored_artifacts[0][0] if scored_artifacts else 1.0)
        overall_confidence = min(1.0, max(0.2, top_score))

        # Check if top artifact is stale / requires revalidation
        validity_status = MemoryStatus.ACTIVE
        if top_artifacts:
            validity_status = top_artifacts[0].status

        # 11. Fetch Dataset Context
        dataset_ctx = {}
        if top_artifacts:
            dataset_ctx = {
                "primary_dataset": top_artifacts[0].dataset_name,
                "version": top_artifacts[0].dataset_version,
                "status": top_artifacts[0].status.value
            }

        return ContextRetrievalResult(
            memories=top_memories,
            analytical_artifacts=top_artifacts,
            dataset_context=dataset_ctx,
            business_definitions=matched_definitions,
            user_preferences=user_preferences,
            decisions=decisions,
            recommendations=recommendations,
            overall_confidence=overall_confidence,
            validity_status=validity_status,
            hitl_required=hitl_required,
            hitl_reason=hitl_reason,
            hitl_options=hitl_options
        )

    # =========================================================================
    # Scoring Engines
    # =========================================================================

    def _compute_memory_score(
        self,
        mem: BusinessMemoryItem,
        q_tokens: Set[str],
        entities: Set[str],
        metrics: Set[str],
        datasets: Optional[List[str]],
        target_function: str
    ) -> float:
        """Compute multi-signal score for a BusinessMemoryItem."""
        score = 0.0

        # 1. Semantic Token Overlap
        mem_tokens = set(re.findall(r"\w+", (mem.title + " " + mem.content).lower()))
        overlap = len(q_tokens.intersection(mem_tokens))
        if overlap > 0:
            score += min(0.4, overlap * 0.1)

        # 2. Exact Entity Match
        mem_entities = set(e.lower() for e in mem.entity_tags)
        query_entities = set(e.lower() for e in entities)
        if mem_entities.intersection(query_entities):
            score += 0.35

        # 3. Metric Match
        mem_metrics = set(m.lower() for m in mem.metric_tags)
        query_metrics = set(m.lower() for m in metrics)
        if mem_metrics.intersection(query_metrics):
            score += 0.25

        # 4. Dataset Match
        if datasets and mem.source_dataset and mem.source_dataset.lower() in [d.lower() for d in datasets]:
            score += 0.2

        # 5. Provenance & Fact Quality Weighting
        if mem.info_type == InformationType.FACT:
            score += 0.15
        elif mem.info_type == InformationType.DERIVED_RESULT:
            score += 0.1
        elif mem.info_type == InformationType.MODEL_INFERENCE:
            score -= 0.1  # Penalize unverified model inference

        # 6. Status & Recency Weighting
        if mem.status == MemoryStatus.ACTIVE:
            score += 0.1
        elif mem.status in (MemoryStatus.STALE, MemoryStatus.REQUIRES_REVALIDATION):
            score -= 0.05
        elif mem.status in (MemoryStatus.INVALIDATED, MemoryStatus.ARCHIVED):
            score -= 0.5

        # 7. Target Function Relevance Boost
        if target_function == "REPORTS" and mem.category in (MemoryCategory.ANALYTICAL_MEMORY, MemoryCategory.BUSINESS_KNOWLEDGE):
            score += 0.15
        elif target_function == "COPILOT" and mem.category in (MemoryCategory.ANALYTICAL_MEMORY, MemoryCategory.DECISION_MEMORY):
            score += 0.15

        return max(0.0, score)

    def _compute_artifact_score(
        self,
        art: AnalyticalArtifact,
        q_tokens: Set[str],
        entities: Set[str],
        metrics: Set[str],
        datasets: Optional[List[str]],
        target_function: str
    ) -> float:
        """Compute multi-signal score for an AnalyticalArtifact."""
        score = 0.0

        # 1. Text & Query Overlap
        art_tokens = set(re.findall(r"\w+", (art.name + " " + art.query_text + " " + art.summary).lower()))
        overlap = len(q_tokens.intersection(art_tokens))
        if overlap > 0:
            score += min(0.45, overlap * 0.12)

        # 2. Entity match in dimensions / filters
        art_entities = set(e.lower() for e in art.dimensions)
        query_entities = set(e.lower() for e in entities)
        if art_entities.intersection(query_entities):
            score += 0.35

        # 3. Metric match in measures
        art_measures = set(m.lower() for m in art.measures)
        query_metrics = set(m.lower() for m in metrics)
        if art_measures.intersection(query_metrics):
            score += 0.25

        # 4. Dataset match
        if datasets and art.dataset_name and art.dataset_name.lower() in [d.lower() for d in datasets]:
            score += 0.2

        # 5. Direct reference indicators (e.g., "that analysis", "the sales report", "same numbers")
        if any(w in q_tokens for w in ["that", "same", "previous", "above", "analysis", "report"]):
            score += 0.2

        # 6. Status Penalty
        if art.status == MemoryStatus.ACTIVE:
            score += 0.1
        elif art.status == MemoryStatus.REQUIRES_REVALIDATION:
            score += 0.05  # Retain for revalidation
        elif art.status == MemoryStatus.INVALIDATED:
            score -= 0.6

        # 7. Function prioritization
        if target_function in {"DASHBOARDS", "REPORTS", "COPILOT"}:
            score += 0.15

        return max(0.0, score)

    # =========================================================================
    # Helpers & Domain Filtering
    # =========================================================================

    def _filter_agent_domain(self, items: List[Any], agent_domain: str) -> List[Any]:
        """Filter memory items / artifacts based on specialized agent domain (Inventory, Finance, Sales, etc.)."""
        domain_keywords = {
            "inventory": ["stock", "inventory", "reorder", "quantity", "warehouse", "item"],
            "finance": ["revenue", "profit", "cost", "expense", "budget", "invoice", "payment", "ledger"],
            "sales": ["sales", "customer", "order", "region", "store", "product", "client"],
            "procurement": ["vendor", "supplier", "purchase", "procurement", "challan"],
            "maintenance": ["asset", "machine", "maintenance", "repair", "service"]
        }
        target_kws = domain_keywords.get(agent_domain.lower(), [agent_domain.lower()])

        filtered = []
        for item in items:
            text = (getattr(item, "title", "") + " " + getattr(item, "content", "") + " " + getattr(item, "query_text", "")).lower()
            if any(kw in text for kw in target_kws):
                filtered.append(item)
        return filtered if filtered else items[:2]  # Fallback gracefully

    def _extract_entities(self, text: str) -> Set[str]:
        entities = set()
        loc_match = re.findall(r"\b(?:in|for|at|from|to|with)\s+([A-Za-z]+)\b", text, re.IGNORECASE)
        for m in loc_match:
            if m.lower() not in {"the", "a", "an", "all", "our", "my", "each", "total", "last", "this", "that"}:
                entities.add(m.title())
        return entities

    def _extract_metrics(self, text: str) -> Set[str]:
        metrics = set()
        for kw in ["sales", "revenue", "profit", "cost", "quantity", "stock", "margin", "count", "orders", "invoices"]:
            if kw in text:
                metrics.add(kw)
        return metrics


# Global singleton
context_retrieval_service = ContextRetrievalService()

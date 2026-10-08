"""
CLARIUS / UNIVA Backend - Business Memory Domain Service

Central coordinator for memory ingestion, validation, provenance tracking, promotion,
lifecycle state management, and dataset change propagation.
"""

import logging
import uuid
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Tuple

import duckdb
from app.infrastructure.database import db_manager
from app.infrastructure.memory_repository import DuckDBBusinessMemoryRepository
from app.domain.memory_models import (
    BusinessMemoryItem,
    AnalyticalArtifact,
    BusinessDefinition,
    RecommendationRecord,
    HITLApprovalRequest,
    MemoryCategory,
    ProvenanceSource,
    InformationType,
    MemoryStatus,
    ApprovalStatus,
)

logger = logging.getLogger("clarius.memory.service")


class BusinessMemoryService:
    """Core enterprise memory coordinator for UNIVA / CLARIUS."""

    def __init__(self, repo: Optional[DuckDBBusinessMemoryRepository] = None, db_conn: Optional[duckdb.DuckDBPyConnection] = None):
        self.conn = db_conn or db_manager.get_connection()
        self.repo = repo or DuckDBBusinessMemoryRepository(self.conn)

    # =========================================================================
    # 1. Analytical Memory & Artifact Ingestion
    # =========================================================================

    def record_analytical_result(
        self,
        query_text: str,
        sql: str,
        results: List[Dict[str, Any]],
        dataset_name: str,
        dataset_version: int = 1,
        chart_config: Optional[Dict[str, Any]] = None,
        explanation: str = "",
        user_id: str = "default_user",
        workspace_id: str = "default_workspace",
        columns_used: Optional[List[str]] = None,
        entity_tags: Optional[List[str]] = None,
        metric_tags: Optional[List[str]] = None,
        time_range: Optional[Dict[str, Any]] = None
    ) -> Tuple[BusinessMemoryItem, AnalyticalArtifact]:
        """
        Record verified analytical query result, creating a persistent analytical artifact
        and linking dataset version dependencies.
        """
        now = datetime.utcnow()
        mem_id = f"mem_{uuid.uuid4().hex[:12]}"
        art_id = f"art_{uuid.uuid4().hex[:12]}"

        # Auto-extract entities and metrics if not provided
        if not entity_tags:
            entity_tags = self._extract_entities(query_text)
        if not metric_tags:
            metric_tags = self._extract_metrics(query_text, sql)

        # Prepare summary & metadata
        result_count = len(results) if results else 0
        sample_rows = results[:10] if results else []
        col_names = list(results[0].keys()) if results else []

        summary = explanation or f"Analytical query '{query_text}' returned {result_count} records from dataset '{dataset_name}' (v{dataset_version})."

        # 1. Create Business Memory Item
        memory_item = BusinessMemoryItem(
            id=mem_id,
            category=MemoryCategory.ANALYTICAL_MEMORY,
            user_id=user_id,
            workspace_id=workspace_id,
            title=f"Analysis: {query_text[:60]}",
            content=summary,
            structured_data={
                "artifact_id": art_id,
                "sql": sql,
                "result_count": result_count,
                "columns": col_names,
                "sample_rows": sample_rows
            },
            provenance_source=ProvenanceSource.ANALYTICAL_RESULT,
            info_type=InformationType.DERIVED_RESULT,
            status=MemoryStatus.ACTIVE,
            confidence=1.0,
            source_dataset=dataset_name,
            source_version=dataset_version,
            entity_tags=entity_tags,
            metric_tags=metric_tags,
            time_range=time_range,
            is_verified=True,
            created_at=now,
            updated_at=now
        )
        self.repo.save_memory(memory_item)

        # 2. Create Analytical Artifact
        artifact = AnalyticalArtifact(
            id=art_id,
            memory_id=mem_id,
            name=f"Artifact: {query_text[:50]}",
            query_text=query_text,
            generated_sql=sql,
            filters={"entities": entity_tags, "time_range": time_range or {}},
            dimensions=entity_tags,
            measures=metric_tags,
            dataset_name=dataset_name,
            dataset_version=dataset_version,
            result_metadata={"count": result_count, "columns": col_names, "sample": sample_rows},
            chart_config=chart_config or {},
            summary=summary,
            status=MemoryStatus.ACTIVE,
            user_id=user_id,
            workspace_id=workspace_id,
            created_at=now,
            updated_at=now
        )
        self.repo.save_artifact(artifact)

        # 3. Record Dependency Lineage
        used_cols = columns_used or col_names
        self.repo.record_dependency(
            memory_id=mem_id,
            artifact_id=art_id,
            dataset_name=dataset_name,
            dataset_version=dataset_version,
            columns_used=used_cols
        )

        logger.info(f"Recorded analytical memory '{mem_id}' and artifact '{art_id}' for dataset '{dataset_name}:v{dataset_version}'.")
        return memory_item, artifact

    # =========================================================================
    # 2. User Corrections & Knowledge Promotion
    # =========================================================================

    def record_user_correction(
        self,
        correction_text: str,
        prior_context: str,
        user_id: str = "default_user",
        workspace_id: str = "default_workspace",
        is_organization_wide: bool = False
    ) -> BusinessMemoryItem:
        """
        Record a user correction with provenance USER_CORRECTION.
        Temporary query adjustments remain in user/conversation context.
        Only explicitly verified organization-level rules are promoted to durable business definitions.
        """
        now = datetime.utcnow()
        mem_id = f"mem_corr_{uuid.uuid4().hex[:10]}"

        # Distinguish between temporary query preference and organization business definition
        category = MemoryCategory.BUSINESS_KNOWLEDGE if is_organization_wide else MemoryCategory.CONVERSATIONAL_CONTEXT
        info_type = InformationType.FACT if is_organization_wide else InformationType.USER_PROVIDED_CONTEXT

        item = BusinessMemoryItem(
            id=mem_id,
            category=category,
            user_id=user_id if not is_organization_wide else "all",
            workspace_id=workspace_id,
            title=f"User Correction: {correction_text[:50]}",
            content=correction_text,
            structured_data={
                "prior_context": prior_context,
                "is_organization_wide": is_organization_wide
            },
            provenance_source=ProvenanceSource.USER_CORRECTION,
            info_type=info_type,
            status=MemoryStatus.ACTIVE,
            confidence=0.95,
            is_verified=is_organization_wide,
            created_at=now,
            updated_at=now
        )
        self.repo.save_memory(item)

        # If it defines a business formula or term (e.g. "revenue means net invoice amount")
        term_match = re.search(r"(\b[a-zA-Z\s]+\b)\s+(?:means|is defined as|refers to|=)\s+(.+)", correction_text, re.IGNORECASE)
        if term_match and is_organization_wide:
            term = term_match.group(1).strip()
            def_text = term_match.group(2).strip()
            self.define_business_term(term, def_text, workspace_id=workspace_id, approved_by=user_id)

        logger.info(f"Recorded user correction '{mem_id}' (org_wide={is_organization_wide}).")
        return item

    def define_business_term(
        self,
        term: str,
        definition: str,
        formula: Optional[str] = None,
        workspace_id: str = "default_workspace",
        approved_by: str = "system"
    ) -> BusinessDefinition:
        """Explicitly establish or approve a durable organization business definition."""
        bdef = BusinessDefinition(
            id=f"def_{uuid.uuid4().hex[:10]}",
            term=term.strip().lower(),
            definition=definition.strip(),
            formula=formula,
            workspace_id=workspace_id,
            is_approved=True,
            approved_by=approved_by,
            status=MemoryStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        saved = self.repo.save_definition(bdef)

        # Also register in business_memory for hybrid retrieval
        mem_item = BusinessMemoryItem(
            id=f"mem_def_{saved.id}",
            category=MemoryCategory.BUSINESS_KNOWLEDGE,
            user_id="all",
            workspace_id=workspace_id,
            title=f"Definition: {term}",
            content=f"{term}: {definition}" + (f" (Formula: {formula})" if formula else ""),
            structured_data={"term": term, "definition": definition, "formula": formula},
            provenance_source=ProvenanceSource.USER_EXPLICIT,
            info_type=InformationType.FACT,
            status=MemoryStatus.ACTIVE,
            confidence=1.0,
            entity_tags=[term.lower()],
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.repo.save_memory(mem_item)
        logger.info(f"Established verified business definition for '{term}' in workspace '{workspace_id}'.")
        return saved

    # =========================================================================
    # 3. Decisions & Recommendations
    # =========================================================================

    def record_decision(
        self,
        decision_text: str,
        rationale: str = "",
        user_id: str = "default_user",
        workspace_id: str = "default_workspace"
    ) -> BusinessMemoryItem:
        """Store an explicitly confirmed business decision."""
        mem_id = f"mem_dec_{uuid.uuid4().hex[:10]}"
        item = BusinessMemoryItem(
            id=mem_id,
            category=MemoryCategory.DECISION_MEMORY,
            user_id=user_id,
            workspace_id=workspace_id,
            title=f"Decision: {decision_text[:50]}",
            content=decision_text,
            structured_data={"rationale": rationale},
            provenance_source=ProvenanceSource.USER_EXPLICIT,
            info_type=InformationType.FACT,
            status=MemoryStatus.ACTIVE,
            confidence=1.0,
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        return self.repo.save_memory(item)

    def record_recommendation(
        self,
        title: str,
        recommendation_text: str,
        supporting_facts: List[str],
        reasoning: str,
        analytical_artifact_ids: Optional[List[str]] = None,
        confidence: float = 0.85,
        user_id: str = "default_user",
        workspace_id: str = "default_workspace",
        generated_by: str = "CLARIUS Copilot"
    ) -> RecommendationRecord:
        """
        Record recommendation separately from business facts, carrying supporting facts
        and artifact lineage.
        """
        rec = RecommendationRecord(
            id=f"rec_{uuid.uuid4().hex[:12]}",
            title=title,
            recommendation_text=recommendation_text,
            supporting_facts=supporting_facts or [],
            analytical_artifact_ids=analytical_artifact_ids or [],
            reasoning=reasoning,
            confidence=confidence,
            generated_by=generated_by,
            approval_status=ApprovalStatus.PENDING,
            user_id=user_id,
            workspace_id=workspace_id,
            created_at=datetime.utcnow()
        )
        saved = self.repo.save_recommendation(rec)

        # Also store under RECOMMENDATION category in Business Memory
        mem_item = BusinessMemoryItem(
            id=f"mem_{saved.id}",
            category=MemoryCategory.RECOMMENDATION,
            user_id=user_id,
            workspace_id=workspace_id,
            title=f"Recommendation: {title}",
            content=recommendation_text,
            structured_data={
                "recommendation_id": saved.id,
                "supporting_facts": supporting_facts,
                "reasoning": reasoning,
                "artifact_ids": analytical_artifact_ids
            },
            provenance_source=ProvenanceSource.AGENT_DERIVED,
            info_type=InformationType.RECOMMENDATION,
            status=MemoryStatus.ACTIVE,
            confidence=confidence,
            is_verified=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.repo.save_memory(mem_item)
        logger.info(f"Stored recommendation '{saved.id}' with {len(supporting_facts)} supporting facts.")
        return saved

    # =========================================================================
    # 4. Dataset Change Propagation & Invalidation Lifecycle
    # =========================================================================

    def on_dataset_updated(
        self,
        dataset_name: str,
        new_version_number: int,
        schema_changes: Optional[Any] = None,
        workspace_id: Optional[str] = "default_workspace"
    ) -> Dict[str, Any]:
        """
        Called when a dataset is updated, imported, or replaced in dataset_versions.
        Propagates staleness / invalidation to all dependent memories and artifacts.
        """
        dname = dataset_name.strip().lower()
        dep_info = self.repo.get_dependent_records_for_dataset(dname)
        mem_ids = dep_info.get("memory_ids", [])
        art_ids = dep_info.get("artifact_ids", [])

        stale_memories = []
        invalidated_artifacts = []
        stale_artifacts = []

        dropped_cols = set()
        if isinstance(schema_changes, dict):
            dropped_cols = set(schema_changes.get("dropped_columns", []))
        elif isinstance(schema_changes, str) and schema_changes:
            workspace_id = schema_changes

        is_dropped = (new_version_number < 0)

        for aid in art_ids:
            art = self.repo.get_artifact(aid)
            if not art:
                continue

            if is_dropped:
                self.repo.update_artifact_status(aid, MemoryStatus.INVALIDATED)
                invalidated_artifacts.append(aid)
            else:
                artifact_cols = set(art.dimensions + art.measures)
                if dropped_cols and artifact_cols.intersection(dropped_cols):
                    self.repo.update_artifact_status(aid, MemoryStatus.INVALIDATED)
                    invalidated_artifacts.append(aid)
                    logger.warning(f"Artifact '{aid}' invalidated due to dropped columns: {artifact_cols.intersection(dropped_cols)}")
                else:
                    self.repo.update_artifact_status(aid, MemoryStatus.REQUIRES_REVALIDATION)
                    stale_artifacts.append(aid)

        for mid in mem_ids:
            if is_dropped:
                self.repo.update_memory_status(mid, MemoryStatus.INVALIDATED)
            else:
                self.repo.update_memory_status(mid, MemoryStatus.STALE)
            stale_memories.append(mid)

        logger.info(
            f"Dataset '{dataset_name}' updated to v{new_version_number}. "
            f"Marked {len(stale_memories)} memories STALE, {len(stale_artifacts)} artifacts REQUIRES_REVALIDATION, "
            f"{len(invalidated_artifacts)} artifacts INVALIDATED."
        )

        return {
            "dataset_name": dataset_name,
            "new_version": new_version_number,
            "stale_memories_count": len(stale_memories),
            "stale_artifacts_count": len(stale_artifacts),
            "invalidated_artifacts_count": len(invalidated_artifacts)
        }

    def get_artifact(self, artifact_id: str, workspace_id: Optional[str] = None) -> Optional[AnalyticalArtifact]:
        """Fetch analytical artifact by ID."""
        return self.repo.get_artifact(artifact_id)

    def get_analytical_artifacts(
        self,
        workspace_id: str = "default_workspace",
        user_id: Optional[str] = None,
        dataset_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 30
    ) -> List[AnalyticalArtifact]:
        """List analytical artifacts."""
        st = MemoryStatus(status) if status else None
        return self.repo.get_artifacts_by_workspace(workspace_id=workspace_id, user_id=user_id, status=st, limit=limit)

    def get_business_definitions(
        self,
        workspace_id: str = "default_workspace",
        domain: Optional[str] = None,
        term: Optional[str] = None,
        only_approved: bool = True
    ) -> List[BusinessDefinition]:
        """List registered business definitions."""
        return self.repo.get_definitions_by_workspace(workspace_id=workspace_id, term=term, only_approved=only_approved)

    def get_recommendations(
        self,
        workspace_id: str = "default_workspace",
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 30
    ) -> List[RecommendationRecord]:
        """List recommendations."""
        st = ApprovalStatus(status) if status else None
        return self.repo.get_recommendations(user_id=user_id, workspace_id=workspace_id, approval_status=st, limit=limit)

    def approve_recommendation(
        self,
        recommendation_id: str,
        approved_by: str,
        approved: bool = True,
        workspace_id: str = "default_workspace"
    ) -> Optional[RecommendationRecord]:
        """Approve or reject a recommendation."""
        new_status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        success = self.repo.update_recommendation_status(recommendation_id, new_status, approved_by)
        if success:
            recs = self.repo.get_recommendations(workspace_id=workspace_id, limit=50)
            for r in recs:
                if r.id == recommendation_id:
                    return r
        return None

    def revalidate_artifact(self, artifact_id: str, workspace_id: Optional[str] = None) -> Optional[AnalyticalArtifact]:
        """
        Re-run the analytical artifact's query/SQL against the latest dataset version.
        Updates result metadata and promotes back to ACTIVE.
        """
        art = self.repo.get_artifact(artifact_id)
        if not art or art.status == MemoryStatus.INVALIDATED:
            logger.warning(f"Cannot revalidate artifact '{artifact_id}' (status={art.status if art else 'not found'}).")
            return None

        conn = self.conn or db_manager.get_connection()
        try:
            # Re-execute query
            res = conn.execute(art.generated_sql).fetchall()
            cols = [desc[0] for desc in conn.description] if conn.description else []
            rows = [dict(zip(cols, r)) for r in res]

            # Fetch latest dataset version
            v_res = conn.execute("SELECT MAX(version_number) FROM dataset_versions WHERE LOWER(dataset_name) = LOWER(?)", [art.dataset_name]).fetchone()
            latest_v = v_res[0] if (v_res and v_res[0]) else (art.dataset_version + 1)

            art.dataset_version = latest_v
            art.result_metadata = {"count": len(rows), "columns": cols, "sample": rows[:10]}
            art.status = MemoryStatus.ACTIVE
            art.updated_at = datetime.utcnow()
            self.repo.save_artifact(art)

            # Revalidate parent memory item if present
            if art.memory_id:
                mem = self.repo.get_memory(art.memory_id)
                if mem:
                    mem.status = MemoryStatus.ACTIVE
                    mem.source_version = latest_v
                    mem.structured_data["sample_rows"] = rows[:10]
                    mem.structured_data["result_count"] = len(rows)
                    self.repo.save_memory(mem)

            logger.info(f"Successfully revalidated artifact '{artifact_id}' on dataset '{art.dataset_name}:v{latest_v}'.")
            return art
        except Exception as e:
            logger.error(f"Failed to revalidate artifact '{artifact_id}': {str(e)}")
            art.status = MemoryStatus.INVALIDATED
            self.repo.save_artifact(art)
            return art

    # =========================================================================
    # Helpers
    # =========================================================================

    def _extract_entities(self, query: str) -> List[str]:
        """Extract primary entity names, regions, products from query string."""
        entities = []
        loc_match = re.search(r"\b(?:in|for|at|from)\s+([A-Za-z]+)\b", query, re.IGNORECASE)
        if loc_match:
            val = loc_match.group(1).strip()
            if val.lower() not in {"the", "a", "an", "all", "our", "my", "each", "total", "last", "this"}:
                entities.append(val.title())
        return entities

    def _extract_metrics(self, query: str, sql: str) -> List[str]:
        """Extract primary metrics/KPIs mentioned in query or SQL."""
        metrics = []
        metric_keywords = ["sales", "revenue", "profit", "cost", "quantity", "stock", "margin", "count", "orders", "invoices"]
        q_lower = query.lower()
        for kw in metric_keywords:
            if kw in q_lower:
                metrics.append(kw)
        return list(set(metrics))


# Global singleton service
business_memory_service = BusinessMemoryService()

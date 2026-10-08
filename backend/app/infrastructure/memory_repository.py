"""
CLARIUS / UNIVA Backend - Business Memory DuckDB Repository

Handles persistent data access and transactional operations for the Business Memory Layer.
"""

import json
import uuid
import logging
from enum import Enum
from datetime import datetime
from typing import Dict, Any, List, Optional, Set

import duckdb
from app.infrastructure.database import db_manager
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

logger = logging.getLogger("clarius.memory.repository")


class DuckDBBusinessMemoryRepository:
    """DuckDB concrete implementation for Business Memory persistence."""

    def __init__(self, db_conn: Optional[duckdb.DuckDBPyConnection] = None):
        self.conn = db_conn

    def _get_conn(self) -> duckdb.DuckDBPyConnection:
        if self.conn is not None:
            return self.conn
        return db_manager.get_connection()

    # =========================================================================
    # Business Memory Items
    # =========================================================================

    def save_memory(self, item: BusinessMemoryItem) -> BusinessMemoryItem:
        """Insert or update a business memory item."""
        conn = self._get_conn()
        now = datetime.utcnow()
        if not item.id:
            item.id = f"mem_{uuid.uuid4().hex[:12]}"
        item.updated_at = now

        # Convert fields to JSON strings
        struct_json = json.dumps(item.structured_data or {})
        entities_json = json.dumps(item.entity_tags or [])
        metrics_json = json.dumps(item.metric_tags or [])
        time_json = json.dumps(item.time_range or {})

        conn.execute("""
            INSERT OR REPLACE INTO business_memory (
                id, category, user_id, workspace_id, title, content, structured_data,
                provenance_source, info_type, status, confidence, source_dataset,
                source_version, entity_tags, metric_tags, time_range, is_verified,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            item.id,
            item.category.value if isinstance(item.category, Enum) else str(item.category),
            item.user_id,
            item.workspace_id,
            item.title,
            item.content,
            struct_json,
            item.provenance_source.value if isinstance(item.provenance_source, Enum) else str(item.provenance_source),
            item.info_type.value if isinstance(item.info_type, Enum) else str(item.info_type),
            item.status.value if isinstance(item.status, Enum) else str(item.status),
            float(item.confidence),
            item.source_dataset,
            item.source_version,
            entities_json,
            metrics_json,
            time_json,
            bool(item.is_verified),
            item.created_at or now,
            item.updated_at
        ])
        conn.execute("CHECKPOINT;")
        return item

    def get_memory(self, memory_id: str) -> Optional[BusinessMemoryItem]:
        """Fetch memory item by ID."""
        conn = self._get_conn()
        res = conn.execute("""
            SELECT id, category, user_id, workspace_id, title, content, structured_data,
                   provenance_source, info_type, status, confidence, source_dataset,
                   source_version, entity_tags, metric_tags, time_range, is_verified,
                   created_at, updated_at
            FROM business_memory WHERE id = ?
        """, [memory_id]).fetchone()
        if not res:
            return None
        return self._row_to_memory_item(res)

    def query_memories(
        self,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        categories: Optional[List[MemoryCategory]] = None,
        statuses: Optional[List[MemoryStatus]] = None,
        dataset_name: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 50
    ) -> List[BusinessMemoryItem]:
        """Retrieve memories with security isolation and multi-attribute filters."""
        conn = self._get_conn()
        clauses = []
        params = []

        if user_id:
            # Allow workspace shared memories or user-specific memories
            clauses.append("(user_id = ? OR user_id = 'system' OR user_id = 'all')")
            params.append(user_id)

        if workspace_id:
            clauses.append("(workspace_id = ? OR workspace_id = 'default_workspace' OR workspace_id = 'global')")
            params.append(workspace_id)

        if categories:
            cat_vals = [c.value if isinstance(c, Enum) else str(c) for c in categories]
            placeholders = ", ".join(["?"] * len(cat_vals))
            clauses.append(f"category IN ({placeholders})")
            params.extend(cat_vals)

        if statuses:
            stat_vals = [s.value if isinstance(s, Enum) else str(s) for s in statuses]
            placeholders = ", ".join(["?"] * len(stat_vals))
            clauses.append(f"status IN ({placeholders})")
            params.extend(stat_vals)
        else:
            clauses.append("status != 'ARCHIVED'")

        if dataset_name:
            clauses.append("LOWER(source_dataset) = LOWER(?)")
            params.append(dataset_name)

        if search_query:
            pattern = f"%{search_query.strip()}%"
            clauses.append("(LOWER(title) LIKE LOWER(?) OR LOWER(content) LIKE LOWER(?) OR LOWER(entity_tags) LIKE LOWER(?))")
            params.extend([pattern, pattern, pattern])

        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        query_sql = f"""
            SELECT id, category, user_id, workspace_id, title, content, structured_data,
                   provenance_source, info_type, status, confidence, source_dataset,
                   source_version, entity_tags, metric_tags, time_range, is_verified,
                   created_at, updated_at
            FROM business_memory
            {where_sql}
            ORDER BY updated_at DESC
            LIMIT ?
        """
        params.append(limit)
        rows = conn.execute(query_sql, params).fetchall()
        return [self._row_to_memory_item(r) for r in rows]

    def get_memories_by_workspace(
        self,
        workspace_id: str,
        category: Optional[MemoryCategory] = None,
        user_id: Optional[str] = None,
        limit: int = 50
    ) -> List[BusinessMemoryItem]:
        """Fetch memories by workspace with optional category filter."""
        cats = [category] if category else None
        return self.query_memories(user_id=user_id, workspace_id=workspace_id, categories=cats, limit=limit)

    def update_memory_status(self, memory_id: str, status: MemoryStatus) -> bool:
        """Update memory lifecycle state."""
        conn = self._get_conn()
        val = status.value if isinstance(status, Enum) else str(status)
        conn.execute("""
            UPDATE business_memory
            SET status = ?, updated_at = ?
            WHERE id = ?
        """, [val, datetime.utcnow(), memory_id])
        conn.execute("CHECKPOINT;")
        return True

    # =========================================================================
    # Analytical Artifacts
    # =========================================================================

    def save_artifact(self, artifact: AnalyticalArtifact) -> AnalyticalArtifact:
        """Insert or update an analytical artifact."""
        conn = self._get_conn()
        now = datetime.utcnow()
        if not artifact.id:
            artifact.id = f"art_{uuid.uuid4().hex[:12]}"
        artifact.updated_at = now

        conn.execute("""
            INSERT OR REPLACE INTO analytical_artifacts (
                id, memory_id, name, query_text, generated_sql, filters, dimensions,
                measures, dataset_name, dataset_version, result_metadata, chart_config,
                summary, status, user_id, workspace_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            artifact.id,
            artifact.memory_id,
            artifact.name,
            artifact.query_text,
            artifact.generated_sql,
            json.dumps(artifact.filters or {}),
            json.dumps(artifact.dimensions or []),
            json.dumps(artifact.measures or []),
            artifact.dataset_name,
            artifact.dataset_version,
            json.dumps(artifact.result_metadata or {}),
            json.dumps(artifact.chart_config or {}),
            artifact.summary,
            artifact.status.value if isinstance(artifact.status, Enum) else str(artifact.status),
            artifact.user_id,
            artifact.workspace_id,
            artifact.created_at or now,
            artifact.updated_at
        ])
        conn.execute("CHECKPOINT;")
        return artifact

    def get_artifact(self, artifact_id: str) -> Optional[AnalyticalArtifact]:
        """Fetch artifact by ID."""
        conn = self._get_conn()
        res = conn.execute("""
            SELECT id, memory_id, name, query_text, generated_sql, filters, dimensions,
                   measures, dataset_name, dataset_version, result_metadata, chart_config,
                   summary, status, user_id, workspace_id, created_at, updated_at
            FROM analytical_artifacts WHERE id = ?
        """, [artifact_id]).fetchone()
        if not res:
            return None
        return self._row_to_artifact(res)

    def query_artifacts(
        self,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        dataset_name: Optional[str] = None,
        statuses: Optional[List[MemoryStatus]] = None,
        search_query: Optional[str] = None,
        limit: int = 30
    ) -> List[AnalyticalArtifact]:
        """Query analytical artifacts with security isolation."""
        conn = self._get_conn()
        clauses = []
        params = []

        if user_id:
            clauses.append("(user_id = ? OR user_id = 'default_user' OR user_id = 'system' OR user_id = 'all')")
            params.append(user_id)

        if workspace_id:
            clauses.append("(workspace_id = ? OR workspace_id = 'default_workspace' OR workspace_id = 'global')")
            params.append(workspace_id)

        if dataset_name:
            clauses.append("LOWER(dataset_name) = LOWER(?)")
            params.append(dataset_name)

        if statuses:
            stat_vals = [s.value if isinstance(s, Enum) else str(s) for s in statuses]
            placeholders = ", ".join(["?"] * len(stat_vals))
            clauses.append(f"status IN ({placeholders})")
            params.extend(stat_vals)

        if search_query:
            pattern = f"%{search_query.strip()}%"
            clauses.append("(LOWER(name) LIKE LOWER(?) OR LOWER(query_text) LIKE LOWER(?) OR LOWER(summary) LIKE LOWER(?))")
            params.extend([pattern, pattern, pattern])

        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        query_sql = f"""
            SELECT id, memory_id, name, query_text, generated_sql, filters, dimensions,
                   measures, dataset_name, dataset_version, result_metadata, chart_config,
                   summary, status, user_id, workspace_id, created_at, updated_at
            FROM analytical_artifacts
            {where_sql}
            ORDER BY updated_at DESC
            LIMIT ?
        """
        params.append(limit)
        rows = conn.execute(query_sql, params).fetchall()
        return [self._row_to_artifact(r) for r in rows]

    def update_artifact_status(self, artifact_id: str, status: MemoryStatus) -> bool:
        """Update artifact validity status."""
        conn = self._get_conn()
        val = status.value if isinstance(status, Enum) else str(status)
        conn.execute("""
            UPDATE analytical_artifacts
            SET status = ?, updated_at = ?
            WHERE id = ?
        """, [val, datetime.utcnow(), artifact_id])
        conn.execute("CHECKPOINT;")
        return True

    # =========================================================================
    # Dependencies & Lineage
    # =========================================================================

    def record_dependency(
        self,
        memory_id: Optional[str],
        artifact_id: Optional[str],
        dataset_name: str,
        dataset_version: int,
        columns_used: List[str]
    ) -> str:
        """Record dataset and column lineage for a memory item or artifact."""
        conn = self._get_conn()
        dep_id = f"dep_{uuid.uuid4().hex[:12]}"
        conn.execute("""
            INSERT INTO memory_dependencies (
                id, memory_id, artifact_id, dataset_name, dataset_version, columns_used, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            dep_id,
            memory_id,
            artifact_id,
            dataset_name.lower().strip(),
            dataset_version,
            json.dumps(columns_used or []),
            datetime.utcnow()
        ])
        conn.execute("CHECKPOINT;")
        return dep_id

    def get_dependent_records_for_dataset(self, dataset_name: str) -> Dict[str, Any]:
        """Find memory IDs and artifact IDs that depend on a dataset."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT memory_id, artifact_id, dataset_version, columns_used
            FROM memory_dependencies
            WHERE LOWER(dataset_name) = LOWER(?)
        """, [dataset_name.strip()]).fetchall()

        memory_ids = {r[0] for r in rows if r[0]}
        artifact_ids = {r[1] for r in rows if r[1]}
        return {
            "memory_ids": list(memory_ids),
            "artifact_ids": list(artifact_ids),
            "dependencies": rows
        }

    # =========================================================================
    # Business Definitions
    # =========================================================================

    def save_definition(self, definition: BusinessDefinition) -> BusinessDefinition:
        """Save or update an approved business definition."""
        conn = self._get_conn()
        now = datetime.utcnow()
        if not definition.id:
            definition.id = f"def_{uuid.uuid4().hex[:12]}"
        definition.updated_at = now

        conn.execute("""
            INSERT OR REPLACE INTO business_definitions (
                id, term, definition, formula, workspace_id, is_approved, approved_by, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            definition.id,
            definition.term.strip(),
            definition.definition.strip(),
            definition.formula,
            definition.workspace_id,
            bool(definition.is_approved),
            definition.approved_by,
            definition.status.value if isinstance(definition.status, Enum) else str(definition.status),
            definition.created_at or now,
            definition.updated_at
        ])
        conn.execute("CHECKPOINT;")
        return definition

    def get_definitions(
        self,
        workspace_id: str = "default_workspace",
        term: Optional[str] = None
    ) -> List[BusinessDefinition]:
        """Retrieve confirmed business definitions."""
        conn = self._get_conn()
        clauses = ["(workspace_id = ? OR workspace_id = 'default_workspace' OR workspace_id = 'global')", "status = 'ACTIVE'"]
        params = [workspace_id]

        if term:
            clauses.append("LOWER(term) = LOWER(?)")
            params.append(term.strip())

        where_sql = "WHERE " + " AND ".join(clauses)
        rows = conn.execute(f"""
            SELECT id, term, definition, formula, workspace_id, is_approved, approved_by, status, created_at, updated_at
            FROM business_definitions
            {where_sql}
            ORDER BY term ASC
        """, params).fetchall()

        return [
            BusinessDefinition(
                id=r[0],
                term=r[1],
                definition=r[2],
                formula=r[3],
                workspace_id=r[4],
                is_approved=bool(r[5]),
                approved_by=r[6],
                status=MemoryStatus(r[7]),
                created_at=r[8] if isinstance(r[8], datetime) else datetime.utcnow(),
                updated_at=r[9] if isinstance(r[9], datetime) else datetime.utcnow(),
            )
            for r in rows
        ]

    # =========================================================================
    # Recommendation Records
    # =========================================================================

    def save_recommendation(self, rec: RecommendationRecord) -> RecommendationRecord:
        """Persist a recommendation record."""
        conn = self._get_conn()
        if not rec.id:
            rec.id = f"rec_{uuid.uuid4().hex[:12]}"

        conn.execute("""
            INSERT OR REPLACE INTO recommendation_records (
                id, title, recommendation_text, supporting_facts, analytical_artifact_ids,
                reasoning, confidence, generated_by, approval_status, approved_by,
                user_id, workspace_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            rec.id,
            rec.title,
            rec.recommendation_text,
            json.dumps(rec.supporting_facts or []),
            json.dumps(rec.analytical_artifact_ids or []),
            rec.reasoning,
            float(rec.confidence),
            rec.generated_by,
            rec.approval_status.value if isinstance(rec.approval_status, Enum) else str(rec.approval_status),
            rec.approved_by,
            rec.user_id,
            rec.workspace_id,
            rec.created_at or datetime.utcnow(),
            rec.updated_at or rec.created_at or datetime.utcnow()
        ])
        conn.execute("CHECKPOINT;")
        return rec

    def get_recommendations(
        self,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        approval_status: Optional[ApprovalStatus] = None,
        limit: int = 30
    ) -> List[RecommendationRecord]:
        """Fetch recommendation records."""
        conn = self._get_conn()
        clauses = []
        params = []

        if user_id:
            clauses.append("(user_id = ? OR user_id = 'default_user' OR user_id = 'system')")
            params.append(user_id)

        if workspace_id:
            clauses.append("(workspace_id = ? OR workspace_id = 'default_workspace' OR workspace_id = 'global')")
            params.append(workspace_id)

        if approval_status:
            clauses.append("approval_status = ?")
            params.append(approval_status.value if isinstance(approval_status, Enum) else str(approval_status))

        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        query_sql = f"""
            SELECT id, title, recommendation_text, supporting_facts, analytical_artifact_ids,
                   reasoning, confidence, generated_by, approval_status, approved_by,
                   user_id, workspace_id, created_at
            FROM recommendation_records
            {where_sql}
            ORDER BY created_at DESC
            LIMIT ?
        """
        params.append(limit)
        rows = conn.execute(query_sql, params).fetchall()

        results = []
        for r in rows:
            try:
                supp_facts = json.loads(r[3]) if r[3] else []
            except Exception:
                supp_facts = []
            try:
                art_ids = json.loads(r[4]) if r[4] else []
            except Exception:
                art_ids = []

            results.append(RecommendationRecord(
                id=r[0],
                title=r[1],
                recommendation_text=r[2],
                supporting_facts=supp_facts,
                analytical_artifact_ids=art_ids,
                reasoning=r[5] or "",
                confidence=float(r[6]) if r[6] is not None else 0.85,
                generated_by=r[7] or "CLARIUS Copilot",
                approval_status=ApprovalStatus(r[8]) if r[8] else ApprovalStatus.PENDING,
                approved_by=r[9],
                user_id=r[10],
                workspace_id=r[11],
                created_at=r[12] if isinstance(r[12], datetime) else datetime.utcnow()
            ))
        return results

    def update_recommendation_status(
        self,
        rec_id: str,
        status: ApprovalStatus,
        approved_by: str
    ) -> bool:
        """Update approval state for a recommendation."""
        conn = self._get_conn()
        val = status.value if isinstance(status, Enum) else str(status)
        conn.execute("""
            UPDATE recommendation_records
            SET approval_status = ?, approved_by = ?
            WHERE id = ?
        """, [val, approved_by, rec_id])
        conn.execute("CHECKPOINT;")
        return True

    # =========================================================================
    # HITL Approval Requests
    # =========================================================================

    def save_approval_request(self, req: HITLApprovalRequest) -> HITLApprovalRequest:
        """Create a human-in-the-loop approval request."""
        conn = self._get_conn()
        if not req.id:
            req.id = f"hitl_{uuid.uuid4().hex[:12]}"

        conn.execute("""
            INSERT OR REPLACE INTO approval_requests (
                id, request_type, description, context_data, status, user_id, workspace_id, created_at, resolved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            req.id,
            req.request_type,
            req.description,
            json.dumps(req.context_data or {}),
            req.status.value if isinstance(req.status, Enum) else str(req.status),
            req.user_id,
            req.workspace_id,
            req.created_at or datetime.utcnow(),
            req.resolved_at
        ])
        conn.execute("CHECKPOINT;")
        return req

    def get_approval_requests(
        self,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        status: Optional[ApprovalStatus] = None,
        limit: int = 20
    ) -> List[HITLApprovalRequest]:
        """Fetch pending or historical HITL requests."""
        conn = self._get_conn()
        clauses = []
        params = []

        if user_id:
            clauses.append("(user_id = ? OR user_id = 'default_user' OR user_id = 'system')")
            params.append(user_id)

        if workspace_id:
            clauses.append("(workspace_id = ? OR workspace_id = 'default_workspace' OR workspace_id = 'global')")
            params.append(workspace_id)

        if status:
            clauses.append("status = ?")
            params.append(status.value if isinstance(status, Enum) else str(status))

        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        query_sql = f"""
            SELECT id, request_type, description, context_data, status, user_id, workspace_id, created_at, resolved_at
            FROM approval_requests
            {where_sql}
            ORDER BY created_at DESC
            LIMIT ?
        """
        params.append(limit)
        rows = conn.execute(query_sql, params).fetchall()

        results = []
        for r in rows:
            try:
                cdata = json.loads(r[3]) if r[3] else {}
            except Exception:
                cdata = {}
            results.append(HITLApprovalRequest(
                id=r[0],
                request_type=r[1],
                description=r[2],
                context_data=cdata,
                status=ApprovalStatus(r[4]) if r[4] else ApprovalStatus.PENDING,
                user_id=r[5],
                workspace_id=r[6],
                created_at=r[7] if isinstance(r[7], datetime) else datetime.utcnow(),
                resolved_at=r[8] if isinstance(r[8], datetime) else None
            ))
        return results

    def resolve_approval_request(self, req_id: str, status: ApprovalStatus) -> bool:
        """Resolve a HITL approval request."""
        conn = self._get_conn()
        val = status.value if isinstance(status, Enum) else str(status)
        conn.execute("""
            UPDATE approval_requests
            SET status = ?, resolved_at = ?
            WHERE id = ?
        """, [val, datetime.utcnow(), req_id])
        conn.execute("CHECKPOINT;")
        return True

    # =========================================================================
    # Helpers
    # =========================================================================

    def _row_to_memory_item(self, row: Any) -> BusinessMemoryItem:
        try:
            struct_data = json.loads(row[6]) if row[6] else {}
        except Exception:
            struct_data = {}
        try:
            entities = json.loads(row[13]) if row[13] else []
        except Exception:
            entities = []
        try:
            metrics = json.loads(row[14]) if row[14] else []
        except Exception:
            metrics = []
        try:
            trange = json.loads(row[15]) if row[15] else {}
        except Exception:
            trange = {}

        return BusinessMemoryItem(
            id=row[0],
            category=MemoryCategory(row[1]) if row[1] else MemoryCategory.CONVERSATIONAL_CONTEXT,
            user_id=row[2],
            workspace_id=row[3],
            title=row[4],
            content=row[5],
            structured_data=struct_data,
            provenance_source=ProvenanceSource(row[7]) if row[7] else ProvenanceSource.SYSTEM_DERIVED,
            info_type=InformationType(row[8]) if row[8] else InformationType.DERIVED_RESULT,
            status=MemoryStatus(row[9]) if row[9] else MemoryStatus.ACTIVE,
            confidence=float(row[10]) if row[10] is not None else 1.0,
            source_dataset=row[11],
            source_version=row[12],
            entity_tags=entities,
            metric_tags=metrics,
            time_range=trange,
            is_verified=bool(row[16]),
            created_at=row[17] if isinstance(row[17], datetime) else datetime.utcnow(),
            updated_at=row[18] if isinstance(row[18], datetime) else datetime.utcnow()
        )

    def _row_to_artifact(self, row: Any) -> AnalyticalArtifact:
        try:
            filters = json.loads(row[5]) if row[5] else {}
        except Exception:
            filters = {}
        try:
            dims = json.loads(row[6]) if row[6] else []
        except Exception:
            dims = []
        try:
            measures = json.loads(row[7]) if row[7] else []
        except Exception:
            measures = []
        try:
            res_meta = json.loads(row[10]) if row[10] else {}
        except Exception:
            res_meta = {}
        try:
            cconfig = json.loads(row[11]) if row[11] else {}
        except Exception:
            cconfig = {}

        return AnalyticalArtifact(
            id=row[0],
            memory_id=row[1],
            name=row[2],
            query_text=row[3],
            generated_sql=row[4],
            filters=filters,
            dimensions=dims,
            measures=measures,
            dataset_name=row[8] or "",
            dataset_version=row[9] or 1,
            result_metadata=res_meta,
            chart_config=cconfig,
            summary=row[12] or "",
            status=MemoryStatus(row[13]) if row[13] else MemoryStatus.ACTIVE,
            user_id=row[14] or "default_user",
            workspace_id=row[15] or "default_workspace",
            created_at=row[16] if isinstance(row[16], datetime) else datetime.utcnow(),
            updated_at=row[17] if isinstance(row[17], datetime) else datetime.utcnow()
        )


# Global singleton and aliases
DuckDBMemoryRepository = DuckDBBusinessMemoryRepository
memory_repository = DuckDBBusinessMemoryRepository()

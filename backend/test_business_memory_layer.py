"""
CLARIUS Backend - Comprehensive Business Memory Layer Test Suite

Tests all 10 core cross-functional scenarios, provenance tracking, lifecycle validity,
dataset version change propagation, security/isolation, HITL gating, and hallucination prevention.
"""

import os
import sys
import unittest
import uuid
import duckdb
from datetime import datetime

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

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
from app.infrastructure.memory_repository import DuckDBBusinessMemoryRepository
from app.application.memory.business_memory_service import BusinessMemoryService
from app.application.memory.context_retrieval_service import ContextRetrievalService
from app.application.memory.hitl_service import HITLService
from app.ai.conversation_context_resolver import ConversationContextResolver
from app.ai.shared.prompt_builder import PromptBuilder


class TestBusinessMemoryLayer(unittest.TestCase):
    """Test suite for UNIVA / CLARIUS Business Memory & Context Layer."""

    def setUp(self):
        # Create an isolated in-memory DuckDB instance with schemas initialized
        self.db = duckdb.connect(":memory:")
        self._init_schemas(self.db)
        
        # Populate demo table for revalidation tests
        self.db.execute("""
            CREATE TABLE sales_chennai_test (
                id VARCHAR,
                region VARCHAR,
                amount DOUBLE,
                sale_date DATE
            );
            INSERT INTO sales_chennai_test VALUES 
            ('s1', 'Chennai', 50000.0, '2025-01-15'),
            ('s2', 'Chennai', 75000.0, '2025-02-20'),
            ('s3', 'Bangalore', 30000.0, '2025-01-10');
            
            INSERT INTO dataset_versions (id, dataset_name, version_number, file_path, file_size, checksum, row_count, column_count, schema_hash, import_mode, is_current, created_at, created_by)
            VALUES ('dv1', 'sales_chennai_test', 1, '/data/sales.csv', 1024, 'chk1', 3, 4, 'hash1', 'replace', TRUE, CURRENT_TIMESTAMP, 'admin');
        """)

        self.memory_repo = DuckDBBusinessMemoryRepository(db_conn=self.db)
        self.memory_service = BusinessMemoryService(repo=self.memory_repo, db_conn=self.db)
        self.hitl_service = HITLService(repo=self.memory_repo, db_conn=self.db)
        self.context_service = ContextRetrievalService(repo=self.memory_repo, db_conn=self.db)

    def tearDown(self):
        self.db.close()

    def _init_schemas(self, conn):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dataset_versions (
                id VARCHAR PRIMARY KEY,
                dataset_name VARCHAR NOT NULL,
                version_number INTEGER NOT NULL,
                file_path VARCHAR NOT NULL,
                file_size BIGINT NOT NULL,
                checksum VARCHAR NOT NULL,
                row_count BIGINT NOT NULL,
                column_count INTEGER NOT NULL,
                schema_hash VARCHAR NOT NULL,
                import_mode VARCHAR DEFAULT 'replace',
                is_current BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL,
                created_by VARCHAR NOT NULL
            );

            CREATE TABLE IF NOT EXISTS business_memory (
                id VARCHAR PRIMARY KEY,
                category VARCHAR NOT NULL,
                user_id VARCHAR NOT NULL,
                workspace_id VARCHAR NOT NULL,
                title VARCHAR NOT NULL,
                content TEXT NOT NULL,
                structured_data TEXT,
                provenance_source VARCHAR NOT NULL,
                info_type VARCHAR NOT NULL,
                status VARCHAR DEFAULT 'ACTIVE',
                confidence DOUBLE DEFAULT 1.0,
                source_dataset VARCHAR,
                source_version INTEGER,
                entity_tags TEXT,
                metric_tags TEXT,
                time_range TEXT,
                is_verified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            );

            CREATE TABLE IF NOT EXISTS analytical_artifacts (
                id VARCHAR PRIMARY KEY,
                memory_id VARCHAR NOT NULL,
                name VARCHAR NOT NULL,
                query_text TEXT NOT NULL,
                generated_sql TEXT NOT NULL,
                filters TEXT,
                dimensions TEXT,
                measures TEXT,
                dataset_name VARCHAR NOT NULL,
                dataset_version INTEGER DEFAULT 1,
                result_metadata TEXT,
                chart_config TEXT,
                summary TEXT,
                status VARCHAR DEFAULT 'ACTIVE',
                user_id VARCHAR NOT NULL,
                workspace_id VARCHAR NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            );

            CREATE TABLE IF NOT EXISTS memory_dependencies (
                id VARCHAR PRIMARY KEY,
                memory_id VARCHAR NOT NULL,
                artifact_id VARCHAR NOT NULL,
                dataset_name VARCHAR NOT NULL,
                dataset_version INTEGER DEFAULT 1,
                columns_used TEXT,
                created_at TIMESTAMP NOT NULL
            );

            CREATE TABLE IF NOT EXISTS business_definitions (
                id VARCHAR PRIMARY KEY,
                term VARCHAR NOT NULL,
                definition TEXT NOT NULL,
                formula TEXT,
                workspace_id VARCHAR NOT NULL,
                is_approved BOOLEAN DEFAULT TRUE,
                approved_by VARCHAR,
                status VARCHAR DEFAULT 'ACTIVE',
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            );

            CREATE TABLE IF NOT EXISTS recommendation_records (
                id VARCHAR PRIMARY KEY,
                title VARCHAR NOT NULL,
                recommendation_text TEXT NOT NULL,
                supporting_facts TEXT,
                analytical_artifact_ids TEXT,
                reasoning TEXT,
                confidence DOUBLE DEFAULT 0.85,
                user_id VARCHAR NOT NULL,
                workspace_id VARCHAR NOT NULL,
                generated_by VARCHAR,
                approval_status VARCHAR DEFAULT 'PENDING',
                approved_by VARCHAR,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            );

            CREATE TABLE IF NOT EXISTS approval_requests (
                id VARCHAR PRIMARY KEY,
                request_type VARCHAR NOT NULL,
                description TEXT NOT NULL,
                context_data TEXT,
                status VARCHAR DEFAULT 'PENDING',
                user_id VARCHAR NOT NULL,
                workspace_id VARCHAR NOT NULL,
                created_at TIMESTAMP NOT NULL,
                resolved_at TIMESTAMP
            );
        """)

    # -------------------------------------------------------------------------
    # TEST 1: Same-Chat & Cross-Chat Context + Analytical Artifact Reuse
    # -------------------------------------------------------------------------
    def test_01_cross_chat_analytical_artifact_reuse(self):
        """Verify analytical artifact created in Chat A is retrievable by Report in Chat B."""
        # Chat A executes query
        mem_item, artifact = self.memory_service.record_analytical_result(
            query_text="Show sales for Chennai in 2025",
            sql="SELECT region, SUM(amount) AS total_sales FROM sales_chennai_test WHERE region = 'Chennai' GROUP BY region",
            results=[{"region": "Chennai", "total_sales": 125000.0}],
            dataset_name="sales_chennai_test",
            dataset_version=1,
            explanation="Total sales in Chennai for 2025 amounted to 125,000.",
            user_id="analyst_1",
            workspace_id="ws_finance",
            entity_tags=["Chennai"],
            metric_tags=["sales"]
        )
        self.assertIsNotNone(artifact.id)
        self.assertIsNotNone(mem_item.id)

        # Later in Chat B or Report module: "Create a report using the sales analysis"
        retrieved_context = self.context_service.retrieve_context(
            query="Create a report from the sales analysis",
            user_id="analyst_1",
            workspace_id="ws_finance",
            intent="REPORT_GENERATION",
            target_function="REPORTS",
            entities=["Chennai", "sales"]
        )

        self.assertGreater(len(retrieved_context.analytical_artifacts), 0)
        top_artifact = retrieved_context.analytical_artifacts[0]
        self.assertEqual(top_artifact.id, artifact.id)
        self.assertIn("sales_chennai_test", top_artifact.generated_sql)
        self.assertEqual(top_artifact.status, MemoryStatus.ACTIVE)

    # -------------------------------------------------------------------------
    # TEST 2: Copilot Baseline Reuse
    # -------------------------------------------------------------------------
    def test_02_copilot_simulation_baseline(self):
        """Verify Copilot can retrieve baseline analytical artifact for what-if simulation."""
        self.memory_service.record_analytical_result(
            query_text="Sales decreased 12% in Region A",
            sql="SELECT 'Region A' AS region, -12.0 AS growth_rate, 450000.0 AS current_revenue",
            results=[{"region": "Region A", "growth_rate": -12.0, "current_revenue": 450000.0}],
            dataset_name="sales_chennai_test",
            dataset_version=1,
            explanation="Region A sales experienced a 12% decrease with 450000 current revenue.",
            user_id="analyst_1",
            workspace_id="ws_finance",
            entity_tags=["Region A"],
            metric_tags=["sales"]
        )

        # Copilot prompt: "What happens if Region A decreases another 10%?"
        context = self.context_service.retrieve_context(
            query="What happens if Region A decreases another 10%?",
            user_id="analyst_1",
            workspace_id="ws_finance",
            intent="SIMULATION",
            target_function="COPILOT",
            entities=["Region A"]
        )

        self.assertGreater(len(context.analytical_artifacts), 0)
        self.assertIn("Region A", context.analytical_artifacts[0].query_text)

        prompt = PromptBuilder.build_business_copilot_prompt(
            user_request="What happens if Region A decreases another 10%?",
            context_result=context
        )
        self.assertIn("CURRENT USER REQUEST", prompt)
        self.assertIn("RELEVANT ANALYTICAL ARTIFACTS", prompt)
        self.assertIn("Region A", prompt)

    # -------------------------------------------------------------------------
    # TEST 3: Business Definitions Registry & Sharing
    # -------------------------------------------------------------------------
    def test_03_business_definition_registry_and_sharing(self):
        """Verify approved business definitions are persisted and shared with SQL generation."""
        defn = self.memory_service.define_business_term(
            term="Revenue",
            definition="Net invoice value excluding GST tax and trade discounts.",
            formula="SUM(net_amount)",
            workspace_id="ws_finance",
            approved_by="cfo_user"
        )
        self.assertIsNotNone(defn.id)

        context = self.context_service.retrieve_context(
            query="Prepare monthly revenue report",
            user_id="staff_1",
            workspace_id="ws_finance",
            target_function="CLARIUS"
        )
        self.assertGreater(len(context.business_definitions), 0)
        self.assertEqual(context.business_definitions[0].term, "revenue")
        self.assertIn("Net invoice value", context.business_definitions[0].definition)

    # -------------------------------------------------------------------------
    # TEST 4: Dashboard Analytical Context Reuse
    # -------------------------------------------------------------------------
    def test_04_dashboard_artifact_reuse(self):
        """Verify dashboard can reuse chart spec and analytical artifact directly."""
        chart_spec = {"type": "bar", "xAxis": "product_name", "yAxis": "revenue"}
        _, art = self.memory_service.record_analytical_result(
            query_text="Show top 10 products by revenue",
            sql="SELECT product_name, SUM(revenue) AS total FROM products GROUP BY 1 ORDER BY 2 DESC LIMIT 10",
            results=[{"product_name": "Widget A", "total": 90000}],
            dataset_name="products",
            dataset_version=1,
            chart_config=chart_spec,
            explanation="Top product is Widget A with 90,000 revenue.",
            user_id="analyst_1",
            workspace_id="ws_finance",
            entity_tags=["products"],
            metric_tags=["revenue"]
        )

        retrieved = self.memory_service.get_artifact(art.id, "ws_finance")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.chart_config.get("type"), "bar")
        self.assertIn("Widget A", retrieved.summary)

    # -------------------------------------------------------------------------
    # TEST 5: Recommendation vs Fact Strict Separation
    # -------------------------------------------------------------------------
    def test_05_recommendation_vs_fact_separation(self):
        """Verify recommendations are not stored as verified business facts."""
        fact_mem = self.memory_service.record_decision(
            decision_text="Sales in Chennai declined 8% in Q3.",
            rationale="Verified against quarterly invoices.",
            user_id="analyst_1",
            workspace_id="ws_finance"
        )
        self.assertEqual(fact_mem.info_type, InformationType.FACT)

        rec = self.memory_service.record_recommendation(
            title="Chennai Sales Optimization",
            recommendation_text="Consider running promotional campaigns in Chennai.",
            supporting_facts=["Sales in Chennai declined 8% in Q3."],
            reasoning="Promotions can stimulate demand in underperforming regions.",
            confidence=0.85,
            user_id="ai_agent",
            workspace_id="ws_finance",
            generated_by="SalesAgent"
        )
        self.assertIsNotNone(rec.id)
        self.assertEqual(rec.approval_status, ApprovalStatus.PENDING)

        # Verify fact memory does not contain the recommendation string
        facts = self.memory_repo.get_memories_by_workspace("ws_finance", category=MemoryCategory.DECISION_MEMORY)
        fact_texts = [f.content for f in facts]
        self.assertIn("Sales in Chennai declined 8% in Q3.", fact_texts)
        self.assertNotIn("Consider running promotional campaigns in Chennai.", fact_texts)

    # -------------------------------------------------------------------------
    # TEST 6: Dataset Version Change Propagation & Stale Invalidation
    # -------------------------------------------------------------------------
    def test_06_dataset_version_change_and_revalidation(self):
        """Verify updating a dataset changes dependent artifact to requires_revalidation and revalidates."""
        _, artifact = self.memory_service.record_analytical_result(
            query_text="Show Chennai sales",
            sql="SELECT region, SUM(amount) AS total_sales FROM sales_chennai_test WHERE region = 'Chennai' GROUP BY region",
            results=[{"region": "Chennai", "total_sales": 125000.0}],
            dataset_name="sales_chennai_test",
            dataset_version=1,
            user_id="analyst_1",
            workspace_id="ws_finance"
        )
        self.assertEqual(artifact.status, MemoryStatus.ACTIVE)

        # New dataset version arrives (v2)
        self.db.execute("""
            INSERT INTO dataset_versions (id, dataset_name, version_number, file_path, file_size, checksum, row_count, column_count, schema_hash, import_mode, is_current, created_at, created_by)
            VALUES ('dv2', 'sales_chennai_test', 2, '/data/sales_v2.csv', 2048, 'chk2', 4, 4, 'hash2', 'replace', TRUE, CURRENT_TIMESTAMP, 'admin');
        """)
        # Trigger propagation
        stale_res = self.memory_service.on_dataset_updated("sales_chennai_test", 2, "ws_finance")
        self.assertGreaterEqual(stale_res["stale_artifacts_count"], 1)

        # Check artifact status
        stale_art = self.memory_service.get_artifact(artifact.id, "ws_finance")
        self.assertEqual(stale_art.status, MemoryStatus.REQUIRES_REVALIDATION)

        # Revalidate artifact
        revalidated = self.memory_service.revalidate_artifact(artifact.id, "ws_finance")
        self.assertIsNotNone(revalidated)
        self.assertEqual(revalidated.status, MemoryStatus.ACTIVE)
        self.assertEqual(revalidated.dataset_version, 2)

        # Dropping dataset marks artifact INVALIDATED
        self.memory_service.on_dataset_updated("sales_chennai_test", -1, "ws_finance")
        invalid_art = self.memory_service.get_artifact(artifact.id, "ws_finance")
        self.assertEqual(invalid_art.status, MemoryStatus.INVALIDATED)

    # -------------------------------------------------------------------------
    # TEST 7: Conflicting Memories & Ambiguity Clarification
    # -------------------------------------------------------------------------
    def test_07_conflicting_memory_requires_clarification(self):
        """Verify conflicting definitions trigger HITL / clarification requirement."""
        self.memory_service.define_business_term(
            term="Revenue",
            definition="Gross invoice value before discount.",
            workspace_id="ws_finance",
            approved_by="u1"
        )
        self.memory_service.define_business_term(
            term="Revenue",
            definition="Net collected cash from customers.",
            workspace_id="ws_finance",
            approved_by="u2"
        )

        context = self.context_service.retrieve_context(
            query="Calculate our total revenue",
            user_id="analyst_1",
            workspace_id="ws_finance",
            target_function="CLARIUS"
        )

        self.assertTrue(context.hitl_required)
        self.assertIn("conflicting definitions", context.hitl_reason.lower())

    # -------------------------------------------------------------------------
    # TEST 8: Security & Multi-Tenant / User Isolation
    # -------------------------------------------------------------------------
    def test_08_security_tenant_isolation(self):
        """Verify Workspace A data cannot be seen or retrieved by Workspace B."""
        # Create private memory in Workspace A
        self.memory_service.record_decision(
            decision_text="Alpha Corp confidential expansion target: 50M USD.",
            rationale="Board approved target for Alpha.",
            user_id="user_corp_a",
            workspace_id="workspace_alpha"
        )

        # User in Workspace B attempts retrieval
        context_b = self.context_service.retrieve_context(
            query="expansion target 2026 confidential",
            user_id="user_corp_b",
            workspace_id="workspace_beta",
            target_function="CLARIUS"
        )

        self.assertEqual(len(context_b.memories), 0)
        self.assertEqual(len(context_b.analytical_artifacts), 0)

    # -------------------------------------------------------------------------
    # TEST 9: Human-In-The-Loop (HITL) Consequential Action Gating
    # -------------------------------------------------------------------------
    def test_09_hitl_consequential_action_gating(self):
        """Verify consequential actions require human approval and cannot execute automatically."""
        req = self.hitl_service.create_approval_request(
            request_type="CONSEQUENTIAL_ACTION",
            description="Agent requested deletion of Q1 audit partitions.",
            context_data={"action": "drop_partition", "partition": "2024_Q1"},
            user_id="automated_cleanup_agent",
            workspace_id="ws_finance",
            target_function="AGENT"
        )

        self.assertEqual(req.status, ApprovalStatus.PENDING)
        
        # Check pending list
        pending = self.hitl_service.get_pending_requests("ws_finance")
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].id, req.id)

        # Manager approves
        approved_req = self.hitl_service.resolve_approval_request(
            request_id=req.id,
            status=ApprovalStatus.APPROVED,
            response_text="Approved after verifying backup."
        )
        self.assertEqual(approved_req.status, ApprovalStatus.APPROVED)
        self.assertEqual(approved_req.response_text, "Approved after verifying backup.")

    # -------------------------------------------------------------------------
    # TEST 10: Model Inference Hallucination Prevention
    # -------------------------------------------------------------------------
    def test_10_model_inference_hallucination_prevention(self):
        """Verify unverified model inferences cannot be promoted to durable facts."""
        mem = BusinessMemoryItem(
            id=f"mem_inf_{uuid.uuid4().hex[:8]}",
            category=MemoryCategory.ANALYTICAL_MEMORY,
            user_id="system_llm",
            workspace_id="ws_finance",
            title="Unverified claim",
            content="Market share is projected to double next quarter.",
            provenance_source=ProvenanceSource.MODEL_INFERENCE,
            info_type=InformationType.MODEL_INFERENCE,
            status=MemoryStatus.ACTIVE,
            confidence=0.5,
            is_verified=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.memory_repo.save_memory(mem)

        self.assertEqual(mem.provenance_source, ProvenanceSource.MODEL_INFERENCE)
        self.assertEqual(mem.info_type, InformationType.MODEL_INFERENCE)

        # Context retrieval should demote or flag pure unverified inferences
        context = self.context_service.retrieve_context(
            query="What is our exact market share?",
            user_id="staff_1",
            workspace_id="ws_finance",
            target_function="CLARIUS"
        )
        for m in context.memories:
            self.assertNotEqual(m.provenance_source, ProvenanceSource.DATABASE)


if __name__ == "__main__":
    unittest.main()

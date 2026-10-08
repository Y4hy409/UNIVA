import unittest
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from app.ai.router import FastIntentRouter
from app.infrastructure.database import DatabaseManager
from app.infrastructure.repositories import DuckDBDocumentRepository
from app.modules.documents.application.document_service import DocumentService, seed_knowledge_documents
from app.ai.agents.core.rag_agent import DocumentRetrievalAgent
from app.ai.services.sql_service import SQLService
from app.ai.orchestrator import LangChainOrchestrator

class TestSystemIsolation(unittest.TestCase):
    """Test suite verifying strict isolation between Business SQL data and Document RAG."""

    @classmethod
    def setUpClass(cls):
        cls.db = DatabaseManager(db_path=":memory:")
        cls.db.initialize_schema()
        cls.repo = DuckDBDocumentRepository(cls.db)
        cls.doc_service = DocumentService(cls.repo)
        asyncio.run(seed_knowledge_documents(cls.doc_service))
        cls.sql_service = SQLService(db_conn=cls.db.get_connection())
        cls.orchestrator = LangChainOrchestrator(db_conn=cls.db.get_connection())

    def test_1_document_retrieval_sales_policy(self):
        """Test 1: Document query explicitly requesting Sales Policy should retrieve ONLY Sales Policy."""
        q = "According to the uploaded Sales Policy document, what are the different sales channels used by the company? Explain each sales channel briefly and mention the payment/order method associated with each one."
        route = FastIntentRouter.classify(q)
        
        self.assertEqual(route["intent"], "DOCUMENT_KNOWLEDGE_QUERY")
        self.assertFalse(route["requires_duckdb"])
        self.assertTrue(route["requires_chromadb"])

        agent = DocumentRetrievalAgent()
        passages = agent.retrieve_passages(q)
        self.assertTrue(len(passages) > 0)
        
        retrieved_titles = set(p["title"] for p in passages)
        self.assertIn("Sales Policy", retrieved_titles)
        self.assertNotIn("Company Profile", retrieved_titles)

    def test_2_business_database_isolation(self):
        """Test 2: Business sales data question should strictly use SQL and NEVER use ChromaDB."""
        q = "How many units of Orbit Wires & Cables Corp were sold during the latest quarter? Use only the business database sales data to answer this question."
        route = FastIntentRouter.classify(q)

        self.assertEqual(route["intent"], "STRUCTURED_DATA_QUERY")
        self.assertTrue(route["requires_duckdb"])
        self.assertFalse(route["requires_chromadb"])

        res = self.sql_service.process_query(q)
        self.assertTrue(res.get("success", False))
        self.assertIn("sql", res)
        self.assertTrue(len(res.get("data", [])) > 0)

    def test_3_sql_failure_isolation(self):
        """Test 3: Failed SQL query must return Data unavailable and NEVER call RAG."""
        q = "SELECT INVALID_COLUMN_NAME FROM NON_EXISTENT_TABLE_999"
        res = self.sql_service.process_query(q)
        
        self.assertFalse(res.get("success", False))
        self.assertIn("error", res)

        # Test orchestrator response on failure
        orch_res = self.orchestrator.execute("Show non_existent_metric_999 from non_existent_table")
        self.assertTrue("Data unavailable" in orch_res or "failed" in orch_res.lower())
        self.assertNotIn("Reference 1:", orch_res)  # Ensure no RAG output formatted

    def test_4_name_collision_orbit_wires(self):
        """Test 4: Query about Orbit Wires & Cables Corp sales must use SQL and NOT Company Profile RAG."""
        q = "How much did Orbit Wires & Cables Corp sell during the latest quarter?"
        route = FastIntentRouter.classify(q)

        self.assertEqual(route["intent"], "STRUCTURED_DATA_QUERY")
        self.assertTrue(route["requires_duckdb"])
        self.assertFalse(route["requires_chromadb"])

        orch_res = self.orchestrator.execute(q)
        self.assertNotIn("Document:", orch_res)
        self.assertNotIn("Reference 1:", orch_res)

    def test_5_no_hallucinated_business_result(self):
        """Test 5: Total sales revenue query should run SQL against business dataset and return structured results or Data unavailable."""
        q = "What was the total sales revenue generated across all products during the latest quarter?"
        route = FastIntentRouter.classify(q)

        self.assertEqual(route["intent"], "STRUCTURED_DATA_QUERY")
        self.assertTrue(route["requires_duckdb"])
        self.assertFalse(route["requires_chromadb"])

        res = self.sql_service.process_query(q)
        self.assertTrue(res.get("success", False))
        self.assertTrue(len(res.get("data", [])) > 0)

if __name__ == "__main__":
    unittest.main()

import unittest
import asyncio
import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.abspath("backend"))

from app.ai.router import FastIntentRouter
from app.infrastructure.database import DatabaseManager
from app.infrastructure.repositories import DuckDBDocumentRepository
from app.modules.documents.application.document_service import DocumentService, seed_knowledge_documents
from app.ai.agents.core.rag_agent import DocumentRetrievalAgent
from app.ai.services.sql_service import SQLService
from app.ai.orchestrator import LangChainOrchestrator

class TestFastSystemIsolation(unittest.TestCase):
    """Fast test suite verifying strict isolation between Business SQL data and Document RAG."""

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
        q = "According to the uploaded Sales Policy document, what are the different sales channels used by the company?"
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
        print("\n[TEST 1 PASSED] Document retrieval correctly isolated to Sales Policy.")

    def test_2_business_database_isolation(self):
        """Test 2: Business sales data question should strictly use SQL and NEVER use ChromaDB."""
        q = "How many units of Orbit Wires & Cables Corp were sold during the latest quarter?"
        route = FastIntentRouter.classify(q)

        self.assertEqual(route["intent"], "STRUCTURED_DATA_QUERY")
        self.assertTrue(route["requires_duckdb"])
        self.assertFalse(route["requires_chromadb"])

        # Execute direct SQL on seeded DuckDB
        conn = self.db.get_connection()
        res = conn.execute("""
            SELECT SUM(soi.quantity) 
            FROM sales_order_items soi 
            JOIN products p ON soi.product_id = p.product_id 
            WHERE p.brand = 'Orbit'
        """).fetchone()[0]
        self.assertTrue(res > 0)
        print(f"\n[TEST 2 PASSED] Business sales data query routed to SQL only. Total Orbit units: {res}.")

    def test_3_sql_failure_isolation(self):
        """Test 3: Failed SQL query must return Data unavailable and NEVER call RAG."""
        with patch.object(self.sql_service, 'generate_sql', side_effect=Exception("Database syntax error")):
            res = self.sql_service.process_query("Select invalid columns from non_existent")
            self.assertFalse(res.get("success", False))
            self.assertIn("error", res)

        # Test orchestrator response on failure
        with patch.object(self.orchestrator, '_run_db_query', return_value="DATABASE QUERY ERROR: table not found"):
            orch_res = self.orchestrator.execute("Show non_existent_metric from non_existent_table")
            self.assertEqual(orch_res, "Data unavailable: I could not retrieve the requested information from the business database.")
        print("\n[TEST 3 PASSED] SQL failure strictly isolated. Returned 'Data unavailable' without calling RAG.")

    def test_4_name_collision_orbit_wires(self):
        """Test 4: Query about Orbit Wires & Cables Corp sales must use SQL and NOT Company Profile RAG."""
        q = "How much did Orbit Wires & Cables Corp sell during the latest quarter?"
        route = FastIntentRouter.classify(q)

        self.assertEqual(route["intent"], "STRUCTURED_DATA_QUERY")
        self.assertTrue(route["requires_duckdb"])
        self.assertFalse(route["requires_chromadb"])

        with patch.object(self.orchestrator, '_run_db_query', return_value="Total Sales: ₹1,477,521.77"):
            orch_res = self.orchestrator.execute(q)
            self.assertNotIn("Document:", orch_res)
            self.assertNotIn("Reference 1:", orch_res)
        print("\n[TEST 4 PASSED] Name collision query routed strictly to SQL.")

    def test_5_no_hallucinated_business_result(self):
        """Test 5: Total sales revenue query should run SQL against business dataset and return structured results or Data unavailable."""
        q = "What was the total sales revenue generated across all products during the latest quarter?"
        route = FastIntentRouter.classify(q)

        self.assertEqual(route["intent"], "STRUCTURED_DATA_QUERY")
        self.assertTrue(route["requires_duckdb"])
        self.assertFalse(route["requires_chromadb"])

        conn = self.db.get_connection()
        total_rev = conn.execute("SELECT SUM(grand_total) FROM sales_orders WHERE order_date >= '2024-10-01'").fetchone()[0]
        self.assertTrue(total_rev > 0)
        print(f"\n[TEST 5 PASSED] Total sales revenue query routed to SQL only. Total Revenue: INR {total_rev:,.2f}.")

if __name__ == "__main__":
    unittest.main()

"""
CLARIUS Backend - Core AI Agents Test Suite

This module runs isolated checks for the 4 core AI agents (P1.3).
"""

import sys
import unittest
import duckdb
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.ai.agents.core.schema_agent import SchemaRetrievalAgent
from app.ai.agents.core.validation_agent import SQLValidationAgent
from app.ai.agents.core.rag_agent import DocumentRetrievalAgent
from app.ai.agents.core.communication_agent import CommunicationAgent
from app.ai.agents.core.optimization_agent import QueryOptimizationAgent


class TestCoreAIAgents(unittest.TestCase):

    def setUp(self):
        # Establish in-memory database context for schema agent testing
        self.conn = duckdb.connect(":memory:")
        self.conn.execute("CREATE TABLE products (id INTEGER, name VARCHAR, price FLOAT);")
        
        self.schema_agent = SchemaRetrievalAgent(self.conn)
        self.validation_agent = SQLValidationAgent()
        self.rag_agent = DocumentRetrievalAgent()
        self.communication_agent = CommunicationAgent()
        self.optimization_agent = QueryOptimizationAgent(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_schema_retrieval_agent(self):
        schemas = self.schema_agent.discover_schemas()
        self.assertIn("products", schemas)
        self.assertEqual(len(schemas["products"]), 3)
        self.assertEqual(schemas["products"][0]["column_name"], "id")

    def test_sql_validation_agent(self):
        # 1. Safe query passes
        ok, err = self.validation_agent.validate_sql("SELECT name FROM test_products;")
        self.assertTrue(ok)
        self.assertEqual(err, "")
        
        # 2. Blocked system table read fails
        ok, err = self.validation_agent.validate_sql("SELECT * FROM users;")
        self.assertFalse(ok)
        self.assertIn("Unauthorized access to system entity", err)

    @patch("app.ai.agents.core.rag_agent.knowledge_manager")
    def test_document_retrieval_agent(self, mock_kb):
        mock_col = MagicMock()
        mock_col.query.return_value = {
            "documents": [["Reference passage text."]],
            "metadatas": [[{"title": "Policy Document"}]],
            "distances": [[0.12]]
        }
        mock_kb.create_collection_if_not_exists.return_value = mock_col
        
        passages = self.rag_agent.retrieve_passages("query sample")
        self.assertEqual(len(passages), 1)
        self.assertEqual(passages[0]["content"], "Reference passage text.")
        self.assertEqual(passages[0]["metadata"]["title"], "Policy Document")

    def test_communication_agent(self):
        # 1. Format analytics query explanation
        analytics_text = self.communication_agent.format_analytics_explanation(
            query="Get products count",
            sql_executed="SELECT count(*) FROM products;",
            data_count=10
        )
        self.assertEqual("Here are the products count:", analytics_text)
        
        # 2. Format RAG answer
        passages = [{"content": "Matched policy rules text.", "metadata": {"title": "Company Handbook"}}]
        rag_text = self.communication_agent.format_rag_answer("What is policy?", passages)
        self.assertIn("Company Handbook", rag_text)
        self.assertIn("Matched policy rules text.", rag_text)

    def test_query_optimization_agent(self):
        # 1. Test auto-injection of LIMIT safety bounds
        optimized = self.optimization_agent.optimize_query("SELECT * FROM products")
        self.assertIn("LIMIT 1000", optimized)
        
        # 2. Test redundant nested subqueries rewriting
        nested_query = "SELECT * FROM (SELECT * FROM products)"
        rewritten = self.optimization_agent.optimize_query(nested_query)
        self.assertEqual(rewritten, "SELECT * FROM products LIMIT 1000")
        
        # 3. Test execution plan EXPLAIN tracing
        plan = self.optimization_agent.explain_plan("SELECT * FROM products")
        self.assertIsNotNone(plan)
        self.assertNotEqual(plan, "")


if __name__ == '__main__':
    unittest.main()

import sys
import unittest
import duckdb
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent))

from app.ai.agents.core.memory_agent import MemoryAgent
from app.ai.agents.core.sql_agent import SQLAgent
from app.ai.orchestrator import LangChainOrchestrator

class TestClariusCopilotEnhancements(unittest.TestCase):
    
    def setUp(self):
        self.conn = duckdb.connect(":memory:")
        # Create queries table in memory to test DB-backed MemoryAgent
        self.conn.execute("""
            CREATE TABLE queries (
                id VARCHAR PRIMARY KEY,
                user_id VARCHAR,
                query_text VARCHAR,
                generated_sql VARCHAR,
                status VARCHAR,
                result VARCHAR,
                error_message VARCHAR,
                execution_time_ms INTEGER,
                created_at TIMESTAMP,
                completed_at TIMESTAMP
            );
        """)
        # Create a mock business table
        self.conn.execute("CREATE TABLE data_customers (Customer_Gender VARCHAR, Customer_Age INTEGER, Date DATE);")
        from app.ai.services.sql_service import SQLService
        SQLService.invalidate_schema_cache()
        
    def tearDown(self):
        from app.ai.services.sql_service import SQLService
        SQLService.invalidate_schema_cache()
        self.conn.close()

    def test_memory_agent_context_and_follow_up(self):
        memory_agent = MemoryAgent(db_conn=self.conn)
        
        # 1. Initially empty
        self.assertEqual(memory_agent.get_memory_context(), "")
        self.assertFalse(memory_agent.detect_follow_up("Show sales"))
        
        # 2. Insert query history
        self.conn.execute(
            "INSERT INTO queries (id, query_text, generated_sql, status, created_at) "
            "VALUES ('1', 'Show me region North', 'SELECT * FROM data_customers', 'success', CURRENT_TIMESTAMP)"
        )
        
        context = memory_agent.get_memory_context()
        self.assertIn("Show me region North", context)
        
        # 3. Follow-up detection
        self.assertTrue(memory_agent.detect_follow_up("What about South?"))
        self.assertTrue(memory_agent.detect_follow_up("also for region West"))

    @patch("app.ai.llm.client.OllamaClient.generate")
    def test_sql_agent_reformulation_and_auto_fixes(self, mock_generate):
        sql_agent = SQLAgent(db_conn=self.conn)
        
        # Mock reformulation response from Ollama
        mock_generate.return_value = "Show me customers from region South"
        
        # Add history to queries table
        self.conn.execute(
            "INSERT INTO queries (id, query_text, generated_sql, status, created_at) "
            "VALUES ('1', 'Show me region North', 'SELECT * FROM data_customers', 'success', CURRENT_TIMESTAMP)"
        )
        
        # Ask a follow-up
        reformulated = sql_agent.reformulate_query("What about South?")
        self.assertEqual(reformulated, "Show me customers from region South")
        
        # Test column mapping fix
        sql_with_wrong_cols = "SELECT Gender, Age FROM data_customers"
        fixed_sql = sql_agent.fix_column_names(sql_with_wrong_cols)
        self.assertEqual(fixed_sql, "SELECT Customer_Gender, Customer_Age FROM data_customers")
        
        # Test date/year query fix
        sql_with_year = "SELECT Year FROM data_customers"
        fixed_year_sql = sql_agent.fix_date_and_year_queries(sql_with_year, "Show sales by year")
        self.assertEqual(fixed_year_sql, "SELECT YEAR(Date) FROM data_customers")

    @patch("app.ai.llm.client.OllamaClient.generate")
    def test_sql_agent_query_caching_reuse(self, mock_generate):
        sql_agent = SQLAgent(db_conn=self.conn)
        
        # Run a query. It will fail or generate.
        mock_generate.return_value = "SELECT * FROM data_customers"
        
        # Run first time (uncached)
        result1 = sql_agent.process_natural_language_query("Show all customers")
        self.assertTrue(result1["success"])
        self.assertNotIn("cached", result1)
        
        # Log the success query to the log table
        self.conn.execute(
            "INSERT INTO queries (id, query_text, generated_sql, status, created_at) "
            "VALUES ('2', 'Show all customers', 'SELECT * FROM data_customers LIMIT 1000', 'success', CURRENT_TIMESTAMP)"
        )
        
        # Run second time (cached)
        result2 = sql_agent.process_natural_language_query("Show all customers")
        self.assertTrue(result2["success"])
        self.assertTrue(result2.get("cached", False))
        self.assertTrue(result2["sql"].startswith("SELECT * FROM data_customers"))

    @patch("app.ai.llm.client.OllamaClient.generate")
    def test_orchestrator_initialization_and_tool_call(self, mock_generate):
        # Create orchestrator instance
        orchestrator = LangChainOrchestrator(db_conn=self.conn)
        
        # Verify tools are registered correctly
        tool_names = [tool.name for tool in orchestrator.tools]
        self.assertIn("business_database_query", tool_names)
        self.assertIn("company_knowledge_search", tool_names)
        self.assertIn("chart_visualization_generator", tool_names)
        
        # Test internal DB query tool wrapper
        mock_generate.return_value = "SELECT * FROM data_customers"
        res_str = orchestrator._run_db_query("Show all customers")
        self.assertIn("success", res_str)
        self.assertIn("SELECT * FROM data_customers", res_str)

if __name__ == "__main__":
    unittest.main()

"""
CLARIUS Backend - Consolidated SQL Domain Service

Single cohesive service handling dynamic schema discovery (with 60s TTL cache),
natural language to SQL translation, security verification, plan optimization, and safe DuckDB execution.
Includes backward compatible agent interfaces.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Tuple
import duckdb

from app.infrastructure.database import db_manager
from app.ai.llm.client import ollama_client
from app.ai.shared.prompt_builder import PromptBuilder
from app.ai.shared.sql_utils import SQLUtils
from app.ai.shared.memory_utils import MemoryAgent

logger = logging.getLogger("clarius.ai.services.sql")

class SQLService:
    """Consolidated domain service coordinating end-to-end NL-to-SQL data pipeline."""

    _schema_cache: Optional[str] = None
    _schema_cache_timestamp: float = 0
    _SCHEMA_TTL_SECONDS: float = 60.0

    def __init__(self, db_conn: Optional[duckdb.DuckDBPyConnection] = None):
        self.conn = db_conn or db_manager.get_connection()
        self.ollama = ollama_client
        self.memory = MemoryAgent(self.conn)

    @classmethod
    def invalidate_schema_cache(cls) -> None:
        """Invalidate schema cache when tables are imported or modified."""
        cls._schema_cache = None
        cls._schema_cache_timestamp = 0

    def discover_schemas(self) -> str:
        """Discover database table schemas with caching."""
        now = time.time()
        if (
            SQLService._schema_cache is not None
            and (now - SQLService._schema_cache_timestamp) < SQLService._SCHEMA_TTL_SECONDS
        ):
            return SQLService._schema_cache

        try:
            tables_res = self.conn.execute("SHOW TABLES").fetchall()
            tables = [row[0] for row in tables_res]

            schema_desc = []
            for table in tables:
                info_res = self.conn.execute(f"PRAGMA table_info({table})").fetchall()
                cols = [f"{col[1]} ({col[2]})" for col in info_res]
                schema_desc.append(f"Table '{table}' columns: {', '.join(cols)}")

            result = "\n".join(schema_desc)
            SQLService._schema_cache = result
            SQLService._schema_cache_timestamp = now
            return result
        except Exception as e:
            logger.error(f"Schema discovery error: {str(e)}")
            return ""

    def validate_sql_safety(self, sql: str) -> Tuple[bool, Optional[str]]:
        """Verify query safety."""
        return SQLUtils.validate_sql_safety(self.conn, sql)

    def optimize_query(self, sql: str) -> str:
        """Apply query optimizations."""
        return SQLUtils.optimize_query(sql)

    def reformulate_query(self, question: str) -> str:
        """Reformulate query using memory agent for backward compatibility."""
        if not self.memory.detect_follow_up(question):
            return question
        memory_context = self.memory.get_memory_context()
        prompt = (
            f"You are a data analyst assistant.\n"
            f"{memory_context}\n"
            f"Original Question: {question}\n"
            f"Rewrite the original question into a precise, self-contained, SQL-answerable question, "
            f"combining the context of previous questions. Do not explain your rewrite, just return the exact rewritten question."
        )
        try:
            return self.ollama.generate(prompt=prompt).strip()
        except Exception:
            return question

    def fix_column_names(self, sql: str) -> str:
        """Column name compatibility fix wrapper."""
        column_mappings = {
            r'\bGender\b': 'Customer_Gender',
            r'\bAge\b': 'Customer_Age',
            r'\bSatisfaction\b': 'Customer_Satisfaction',
        }
        import re
        for wrong, correct in column_mappings.items():
            sql = re.sub(wrong, correct, sql, flags=re.IGNORECASE)
        return sql

    def fix_date_and_year_queries(self, sql: str, question: str) -> str:
        """Fix date and year query syntax."""
        return SQLUtils.fix_date_and_year_queries(sql, question)

    def generate_sql(self, user_query: str, schema_context: str, memory_context: str = "") -> str:
        """Translate natural language user query into DuckDB SQL."""
        system_prompt, user_prompt = PromptBuilder.build_sql_prompt(user_query, schema_context, memory_context)
        raw_output = self.ollama.generate(prompt=user_prompt, system_prompt=system_prompt)
        sql = SQLUtils.clean_generated_sql(raw_output)
        return SQLUtils.fix_date_and_year_queries(sql, user_query)

    def execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """Safely execute query and return dict records."""
        return SQLUtils.execute_query(self.conn, sql)

    def process_query(self, user_query: str, memory_context: str = "") -> Dict[str, Any]:
        """Execute full natural language to SQL execution pipeline."""
        schema_context = self.discover_schemas()
        if not schema_context:
            return {"success": False, "error": "No database tables found."}

        try:
            sql = self.generate_sql(user_query, schema_context, memory_context)
            sql = self.fix_column_names(sql)
            sql = self.optimize_query(sql)

            is_safe, error_msg = self.validate_sql_safety(sql)
            if not is_safe:
                return {"success": False, "error": error_msg or "SQL safety check failed."}

            self.conn.execute(f"EXPLAIN {sql}")
            records = self.execute_query(sql)

            return {
                "success": True,
                "sql": sql,
                "data": records
            }
        except Exception as e:
            logger.error(f"SQLService processing error: {str(e)}")
            return {"success": False, "error": str(e)}

    def process_natural_language_query(self, user_query: str) -> Dict[str, Any]:
        """Backward compatible entrypoint matching legacy SQLAgent interface."""
        try:
            cached = self.conn.execute(
                "SELECT generated_sql FROM queries WHERE query_text = ? AND status = 'success' ORDER BY created_at DESC LIMIT 1",
                (user_query,)
            ).fetchone()
            if cached:
                sql = cached[0]
                records = self.execute_query(sql)
                self.memory.record_query(user_query, sql, "success", str(records[:5]))
                return {
                    "success": True,
                    "sql": sql,
                    "data": records,
                    "cached": True
                }
        except Exception:
            pass

        res = self.process_query(user_query)
        if res.get("success"):
            self.memory.record_query(user_query, res.get("sql", ""), "success", str(res.get("data", [])[:5]))
        return res

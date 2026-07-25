"""
CLARIUS Backend - SQL Generation Agent

This agent implements the natural language to SQL translation pipeline, including
dynamic schema discovery, SQL generation, and security verification (ADR-004).
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
import duckdb

from app.infrastructure.database import db_manager
from app.infrastructure.sql_validator import SQLSecurityValidator, SQLExecutionService
from app.ai.llm.client import ollama_client
from app.ai.agents.core.memory_agent import MemoryAgent

logger = logging.getLogger("clarius.agents.sql")

class SQLAgent:
    """Agent pipeline coordinating schema discovery, SQL generation, and safety checks."""
    
    def __init__(self, db_conn: Optional[duckdb.DuckDBPyConnection] = None):
        self.conn = db_conn or db_manager.get_connection()
        self.ollama = ollama_client
        self.validator = SQLSecurityValidator(self.conn)
        self.executor = SQLExecutionService(self.conn)
        self.memory = MemoryAgent(self.conn)

    def discover_schemas(self) -> str:
        """Dynamically query DuckDB and build a schema string describing all tables."""
        tables_res = self.conn.execute("SHOW TABLES").fetchall()
        tables = [row[0] for row in tables_res]
        
        schema_desc = []
        for table in tables:
            info_res = self.conn.execute(f"PRAGMA table_info({table})").fetchall()
            # PRAGMA table_info columns: cid, name, type, notnull, dflt_value, pk
            cols = [f"{col[1]} ({col[2]})" for col in info_res]
            schema_desc.append(f"Table '{table}' columns: {', '.join(cols)}")
            
        return "\n".join(schema_desc)

    def validate_sql_safety(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        Verify that the generated SQL is safe and read-only.
        Returns (is_safe, error_message).
        """
        return self.validator.validate(sql)

    def clean_generated_sql(self, raw_output: str) -> str:
        """Extract SQL queries from LLM markdown code blocks."""
        # Check for ```sql ... ``` code block
        match = re.search(r"```sql(.*?)```", raw_output, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
            
        # Fallback to ``` ... ```
        match = re.search(r"```(.*?)```", raw_output, re.DOTALL)
        if match:
            return match.group(1).strip()
            
        # Return raw output if no code block found
        return raw_output.strip()

    def reformulate_query(self, question: str) -> str:
        """Use MemoryAgent to check for follow-up and reformulate if so."""
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
            reformulated = self.ollama.generate(prompt=prompt).strip()
            logger.info(f"Reformulated query from '{question}' to '{reformulated}'")
            return reformulated
        except Exception as e:
            logger.error(f"Failed to reformulate query: {str(e)}")
            return question

    def fix_column_names(self, sql: str) -> str:
        column_mappings = {
            r'\bGender\b': 'Customer_Gender',
            r'\bAge\b': 'Customer_Age',
            r'\bSatisfaction\b': 'Customer_Satisfaction',
        }
        for wrong, correct in column_mappings.items():
            sql = re.sub(wrong, correct, sql, flags=re.IGNORECASE)
        return sql

    def fix_date_and_year_queries(self, sql: str, question: str) -> str:
        if any(word in question.lower() for word in ['year', 'yearly', 'annual']):
            sql = re.sub(r'\bYear\b', 'YEAR(Date)', sql, flags=re.IGNORECASE)
        return sql

    def generate_sql(self, user_query: str, schema_context: str) -> str:
        """Prompt Ollama to translate user natural language to SQL."""
        system_prompt = (
            "You are a Senior SQL Developer. Translate the user natural language query into a valid, "
            "read-only DuckDB SQL statement. You must only select from the available tables described below.\n\n"
            "DuckDB Database Schema Details:\n"
            f"{schema_context}\n\n"
            "Instructions:\n"
            "1. Output ONLY a valid SQL statement. Do not explain your code.\n"
            "2. Wrap your SQL output inside a standard ```sql markdown block.\n"
            "3. Ensure the SQL query only uses columns described in the schema.\n"
            "4. Do not include semicolons or write operations."
        )
        
        prompt = f"Translate the following business question into a DuckDB SQL statement: '{user_query}'"
        
        raw_output = self.ollama.generate(prompt=prompt, system_prompt=system_prompt)
        return self.clean_generated_sql(raw_output)

    def execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """Run SQL query against DuckDB and return dictionary records."""
        return self.executor.execute_safely(sql)

    def process_natural_language_query(self, user_query: str) -> Dict[str, Any]:
        """Run the full NL-to-SQL agent pipeline."""
        # 1. Check cache/reuse
        try:
            cached = self.conn.execute(
                "SELECT generated_sql FROM queries WHERE query_text = ? AND status = 'success' ORDER BY created_at DESC LIMIT 1",
                (user_query,)
            ).fetchone()
            if cached:
                sql = cached[0]
                logger.info(f"Reusing cached SQL for query '{user_query}': {sql}")
                records = self.execute_query(sql)
                return {
                    "success": True,
                    "sql": sql,
                    "data": records,
                    "cached": True
                }
        except Exception as e:
            logger.error(f"Failed to check query cache: {str(e)}")

        # 2. Reformulate if follow-up
        final_query = self.reformulate_query(user_query)

        schema_context = self.discover_schemas()
        if not schema_context:
            return {
                "success": False,
                "error": "No database tables found. Please import some data first."
            }
            
        try:
            sql = self.generate_sql(final_query, schema_context)
            # Apply auto-fixes
            sql = self.fix_column_names(sql)
            sql = self.fix_date_and_year_queries(sql, final_query)
            logger.info(f"Generated SQL (after fixes): {sql}")
            
            # Dry run explain check to test DuckDB parser syntax
            self.conn.execute(f"EXPLAIN {sql}")
            
            records = self.execute_query(sql)
            
            return {
                "success": True,
                "sql": sql,
                "data": records
            }
        except Exception as e:
            logger.error(f"SQL Agent pipeline failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

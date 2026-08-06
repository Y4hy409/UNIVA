"""
CLARIUS Backend - Centralized SQL Utilities

Provides reusable functions for SQL code block extraction, safety validation,
syntax fixes, execution plan optimization, and safe DuckDB execution.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
import duckdb
from app.infrastructure.sql_validator import SQLSecurityValidator, SQLExecutionService

logger = logging.getLogger("clarius.ai.shared.sql_utils")

class SQLUtils:
    """Consolidated helper functions for SQL processing and security checks."""

    @staticmethod
    def clean_generated_sql(raw_output: str) -> str:
        """Extract SQL query from markdown code blocks or raw text."""
        match = re.search(r"```sql(.*?)```", raw_output, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        match = re.search(r"```(.*?)```", raw_output, re.DOTALL)
        if match:
            return match.group(1).strip()

        return raw_output.strip()

    @staticmethod
    def fix_date_and_year_queries(sql: str, question: str) -> str:
        """Ensure date/year extractions use valid DuckDB syntax."""
        if any(word in question.lower() for word in ['year', 'yearly', 'annual']):
            sql = re.sub(r'\bYear\b', 'YEAR(Date)', sql, flags=re.IGNORECASE)
        return sql

    @staticmethod
    def validate_sql_safety(db_conn: Optional[duckdb.DuckDBPyConnection], sql: str) -> Tuple[bool, Optional[str]]:
        """Verify query is safe and read-only."""
        validator = SQLSecurityValidator(db_conn)
        return validator.validate(sql)

    @staticmethod
    def optimize_query(sql: str) -> str:
        """Apply light optimization rules to SQL queries."""
        optimized = sql.strip()

        # Add safeguard limit to unconstrained SELECT queries
        if "select" in optimized.lower() and "limit" not in optimized.lower():
            if optimized.endswith(";"):
                optimized = optimized[:-1].strip() + " LIMIT 1000;"
            else:
                optimized += " LIMIT 1000"

        # Remove redundant subqueries
        subquery_pattern = r"(?i)SELECT\s+\*\s+FROM\s*\(\s*SELECT\s+\*\s+FROM\s+([a-zA-Z0-9_\.]+)\s*\)"
        optimized = re.sub(subquery_pattern, r"SELECT * FROM \1", optimized)

        return optimized

    @staticmethod
    def execute_query(db_conn: duckdb.DuckDBPyConnection, sql: str) -> List[Dict[str, Any]]:
        """Safely execute query and return dict records."""
        executor = SQLExecutionService(db_conn)
        return executor.execute_safely(sql)

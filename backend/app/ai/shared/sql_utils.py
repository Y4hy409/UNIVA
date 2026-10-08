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
        q_lower = question.lower()
        if any(word in q_lower for word in ['year', 'yearly', 'annual']):
            sql = re.sub(r'\bYear\b', 'YEAR(Date)', sql, flags=re.IGNORECASE)

        # Relative date anchoring for 'latest quarter' / 'current quarter' / 'last quarter'
        if any(kw in q_lower for kw in ['latest quarter', 'current quarter', 'last quarter', 'this quarter', 'latest qtr']):
            sql = re.sub(
                r"(?i)date_trunc\s*\(\s*'quarter'\s*,\s*CURRENT_DATE\s*\)",
                "date_trunc('quarter', (SELECT MAX(order_date) FROM sales_order_items))",
                sql
            )

        # Fix DuckDB Binder Error: STRFTIME(CAST(col AS VARCHAR), '%Y-%m') -> STRFTIME(TRY_CAST(col AS TIMESTAMP), '%Y-%m')
        sql = re.sub(
            r"(?i)STRFTIME\s*\(\s*CAST\s*\(\s*([a-zA-Z0-9_\.]+)\s+AS\s+VARCHAR\s*\)\s*,\s*('[^']+')\s*\)",
            r"STRFTIME(TRY_CAST(\1 AS TIMESTAMP), \2)",
            sql
        )
        # Fix STRFTIME('%Y-%m', CAST(col AS VARCHAR))
        sql = re.sub(
            r"(?i)STRFTIME\s*\(\s*('[^']+')\s*,\s*CAST\s*\(\s*([a-zA-Z0-9_\.]+)\s+AS\s+VARCHAR\s*\)\s*\)",
            r"STRFTIME(TRY_CAST(\2 AS TIMESTAMP), \1)",
            sql
        )
        # Fix raw uncasted column in STRFTIME: STRFTIME(date, '%Y-%m') -> STRFTIME(TRY_CAST(date AS TIMESTAMP), '%Y-%m')
        sql = re.sub(
            r"(?i)\bSTRFTIME\s*\(\s*([a-zA-Z0-9_]+)\s*,\s*('[^']+')\s*\)",
            r"STRFTIME(TRY_CAST(\1 AS TIMESTAMP), \2)",
            sql
        )
        # Fix DuckDB Parser Error: DATE(col, 'modifier') 2-parameter calls -> DuckDB date_trunc / TRY_CAST
        sql = re.sub(
            r"(?i)\bDATE\s*\(\s*([a-zA-Z0-9_\.]+)\s*,\s*'[^\']*(?:month)[^\']*'\s*\)",
            r"date_trunc('month', TRY_CAST(\1 AS DATE))",
            sql
        )
        sql = re.sub(
            r"(?i)\bDATE\s*\(\s*([a-zA-Z0-9_\.]+)\s*,\s*'[^\']*(?:quarter)[^\']*'\s*\)",
            r"date_trunc('quarter', TRY_CAST(\1 AS DATE))",
            sql
        )
        sql = re.sub(
            r"(?i)\bDATE\s*\(\s*([a-zA-Z0-9_\.]+)\s*,\s*'[^\']*(?:year)[^\']*'\s*\)",
            r"date_trunc('year', TRY_CAST(\1 AS DATE))",
            sql
        )
        sql = re.sub(
            r"(?i)\bDATE\s*\(\s*([a-zA-Z0-9_\.]+)\s*,\s*'[^']+'\s*\)",
            r"TRY_CAST(\1 AS DATE)",
            sql
        )
        return sql

    @staticmethod
    def validate_sql_safety(db_conn: Optional[duckdb.DuckDBPyConnection], sql: str) -> Tuple[bool, Optional[str]]:
        """Verify query is safe and read-only."""
        validator = SQLSecurityValidator(db_conn)
        return validator.validate(sql)

    @staticmethod
    def validate_semantic_sql(sql: str, user_query: str) -> Tuple[bool, Optional[str]]:
        """Verify query completeness and semantic alignment with user intent pre-execution."""
        from app.infrastructure.sql_validator import SemanticQueryValidator
        return SemanticQueryValidator.validate_semantic_sql(sql, user_query)

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

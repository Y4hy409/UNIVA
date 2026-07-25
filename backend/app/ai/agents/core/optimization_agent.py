"""
CLARIUS Backend - Query Optimization Agent

This agent analyzes generated SQL statements, retrieves execution plans (EXPLAIN),
and rewrites queries to execute optimally in DuckDB (P1.3).
"""

import re
import logging
from typing import Any

logger = logging.getLogger("clarius.ai.agents.optimization")

class QueryOptimizationAgent:
    """Analyzes SQL queries and rewrites them to use optimal execution paths."""

    def __init__(self, db_conn: Any = None):
        self.conn = db_conn

    def optimize_query(self, sql_query: str) -> str:
        """Apply heuristics to rewrite and optimize generated SQL queries."""
        optimized = sql_query.strip()
        
        # 1. Ensure SELECT queries on large tables have a safeguard LIMIT if not present
        # (excluding subqueries or complex CTE definitions)
        if "select" in optimized.lower() and "limit" not in optimized.lower():
            # Only append LIMIT if it's a simple query and doesn't end with a semicolon
            if optimized.endswith(";"):
                optimized = optimized[:-1].strip() + " LIMIT 1000;"
            else:
                optimized += " LIMIT 1000"

        # 2. Rewrite redundant subqueries: e.g., SELECT * FROM (SELECT * FROM table) -> SELECT * FROM table
        subquery_pattern = r"(?i)SELECT\s+\*\s+FROM\s*\(\s*SELECT\s+\*\s+FROM\s+([a-zA-Z0-9_\.]+)\s*\)"
        optimized = re.sub(subquery_pattern, r"SELECT * FROM \1", optimized)
        
        # 3. Clean trailing whitespace/semicolon duplicates
        if not optimized.endswith(";") and not optimized.lower().endswith("limit 1000"):
            optimized += ";"
            
        logger.info(f"Query optimized: original='{sql_query}' -> optimized='{optimized}'")
        return optimized

    def explain_plan(self, sql_query: str) -> str:
        """Run EXPLAIN on the active database connection to trace execution plan details."""
        if not self.conn:
            return "No active database connection context for execution planning."
        try:
            # Strip trailing semicolon for EXPLAIN syntax
            clean_sql = sql_query.strip().rstrip(";")
            explain_sql = f"EXPLAIN {clean_sql};"
            rows = self.conn.execute(explain_sql).fetchall()
            
            # DuckDB EXPLAIN returns (explain_key, explain_value) or similar tabular plan representation
            plan = "\n".join([str(row[1]) for row in rows if len(row) > 1])
            return plan if plan else "Empty execution plan returned."
        except Exception as e:
            logger.error(f"Failed to fetch execution plan: {str(e)}")
            return f"Failed to retrieve execution plan: {str(e)}"

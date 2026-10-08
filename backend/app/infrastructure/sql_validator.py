"""
CLARIUS Backend - SQL Security Validation Engine

This module implements the SQL Security Validator, Policy Enforcement, and Execution Service
to ensure all AI-generated or user-influenced queries are executed safely (P0).
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Optional
import sqlparse
from sqlparse.tokens import Keyword, DML, DDL, Token

logger = logging.getLogger("clarius.security.sql")

class SQLPolicy:
    """Configuration constraints for SQL query safety."""
    
    # List of allowed business table prefixes or exact names
    APPROVED_TABLE_PREFIXES = ["test_", "data_"]
    
    # Explicitly forbidden commands, functions, and keywords
    FORBIDDEN_KEYWORDS = {
        "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", 
        "CREATE", "REPLACE", "GRANT", "REVOKE", "INSTALL", "LOAD", 
        "COPY", "ATTACH", "DETACH", "PRAGMA", "VACUUM", "CHECKPOINT",
        "TRANSACTION", "COMMIT", "ROLLBACK", "EXPLAIN"
    }

    # Dangerous filesystem and file processing functions
    FORBIDDEN_FUNCTIONS = {
        "read_csv", "read_json", "read_parquet", "write_csv", "write_parquet",
        "query_directory", "glob", "read_blob"
    }

    # Resource bounds
    MAX_RESULT_ROWS = 1000
    QUERY_TIMEOUT_SECONDS = 5.0


class SQLSecurityValidator:
    """Validates generated SQL queries structurally using sqlparse token trees."""

    def __init__(self, conn_schema_helper: Optional[Any] = None):
        self.conn = conn_schema_helper

    def get_allowed_tables(self) -> List[str]:
        """Dynamically fetch approved business tables from DuckDB, ignoring system tables."""
        if not self.conn:
            return []
        try:
            res = self.conn.execute("PRAGMA show_tables;").fetchall()
            all_tables = [r[0] for r in res]
            # Exclude system schemas and internal configurations
            excluded = {
                "users", "organizations", "data_sources", "queries", "dashboards",
                "reports", "documents", "audit_logs", "roles", "permissions",
                "user_roles", "role_permissions", "role_hierarchy", "access_scopes",
                "user_access_scopes", "branches", "departments", "jobs",
                "conversations", "conversation_messages", "dataset_versions",
                "document_versions", "sync_history", "sqlite_master", "sqlite_schema",
                "business_memory", "analytical_artifacts", "memory_dependencies",
                "business_definitions", "recommendation_records", "approval_requests"
            }
            return [t for t in all_tables if t.lower() not in excluded and not t.lower().startswith("sqlite_")]
        except Exception as e:
            logger.error(f"Failed to fetch allowed tables list: {str(e)}")
            return []

    def _extract_tables(self, token_group) -> List[str]:
        """Extract table names from FROM and JOIN clauses."""
        tables = []
        is_from_or_join = False
        
        for token in token_group.tokens:
            if token.is_group:
                # Subqueries inside parentheses are groups
                tables.extend(self._extract_tables(token))
                
            val = token.value.strip().upper()
            if val in ("FROM", "JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN", "CROSS JOIN"):
                is_from_or_join = True
                continue
                
            if is_from_or_join:
                if token.is_whitespace or token.value in (",", ";"):
                    continue
                if isinstance(token, sqlparse.sql.IdentifierList):
                    for identifier in token.get_identifiers():
                        real_name = identifier.get_real_name()
                        if real_name:
                            tables.append(real_name)
                    is_from_or_join = False
                elif isinstance(token, sqlparse.sql.Identifier):
                    real_name = token.get_real_name()
                    if real_name:
                        tables.append(real_name)
                    is_from_or_join = False
                elif token.value.startswith("("):
                    is_from_or_join = False
                    
        return tables

    def _extract_ctes(self, token_group) -> List[str]:
        """Extract CTE aliases defined in WITH clauses."""
        ctes = []
        for token in token_group.tokens:
            if token.is_group:
                ctes.extend(self._extract_ctes(token))
            
            if isinstance(token, sqlparse.sql.Identifier):
                token_str = token.value.upper()
                if " AS " in token_str or " AS(" in token_str:
                    real_name = token.get_real_name()
                    if real_name:
                        ctes.append(real_name)
        return ctes

    def validate(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        Structural validation check for query security.
        Returns (is_safe, error_message).
        """
        # 1. Reject empty or spacing queries
        if not sql or not sql.strip():
            return False, "Query statement is empty."

        # 2. Reject comment-only structures or inline comments to prevent comment-based evasions
        parsed_raw = sqlparse.parse(sql)
        if not parsed_raw:
            return False, "Failed to parse query."
            
        for statement in parsed_raw:
            for token in statement.flatten():
                if token.ttype in (Token.Comment, Token.Comment.Single, Token.Comment.Multiline) or "/**/" in token.value:
                    return False, "Security violation: Comments are not allowed in queries."

        # Clean comments using sqlparse for AST checks
        cleaned = sqlparse.format(sql, strip_comments=True).strip()
        if not cleaned:
            return False, "Query consists only of comments."

        # 3. Reject statement chaining (multiple statements)
        parsed = sqlparse.parse(cleaned)
        if len(parsed) != 1:
            return False, "Security violation: Multiple statements detected."

        statement = parsed[0]

        # 4. Must start with SELECT or WITH
        first_token = statement.token_first()
        if not first_token:
            return False, "Failed to identify leading token."
            
        first_word = first_token.value.upper()
        if first_word not in ("SELECT", "WITH"):
            return False, f"Security violation: Statement must begin with SELECT or WITH (got '{first_word}')."

        # 5. Token traversal scan for forbidden terms and functions
        tokens = list(statement.flatten())
        for token in tokens:
            val = token.value.strip().upper()
            
            # Check forbidden keywords
            if val in SQLPolicy.FORBIDDEN_KEYWORDS:
                return False, f"Security violation: Forbidden keyword '{val}' detected."
            
            # Check forbidden function calls
            if token.ttype in (Token.Name, Token.Keyword):
                val_clean = token.value.strip().lower()
                if val_clean in SQLPolicy.FORBIDDEN_FUNCTIONS:
                    return False, f"Security violation: Dangerous function call '{token.value}' is blocked."

        # 6. Verify table names in FROM and JOIN identifiers
        allowed_tables = self.get_allowed_tables()
        extracted_tables = self._extract_tables(statement)
        cte_aliases = self._extract_ctes(statement)
        
        # Filter out CTE aliases from referenced tables validation list
        filtered_tables = [t for t in extracted_tables if t.lower() not in [c.lower() for c in cte_aliases]]

        for table_name in filtered_tables:
            table_lower = table_name.lower()
            
            # Block system tables explicitly
            if table_lower in ("users", "dashboards", "audit_logs", "sqlite_master", "sqlite_schema") or table_lower.startswith("sqlite_"):
                return False, f"Security violation: Unauthorized access to system entity '{table_name}'."
                
            if allowed_tables:
                if table_lower not in [t.lower() for t in allowed_tables]:
                    return False, f"Security violation: Query references unauthorized table '{table_name}'."
            else:
                # Fallback matching logic for safety prefixes if no DB context is active
                is_allowed = any(table_lower.startswith(prefix) for prefix in SQLPolicy.APPROVED_TABLE_PREFIXES)
                if not is_allowed:
                    return False, f"Security violation: Table '{table_name}' is not in approved business schema."

        return True, None


class SQLExecutionService:
    """Service executing validated queries with safety bounds and row capping."""

    def __init__(self, db_conn: Any):
        self.conn = db_conn
        self.validator = SQLSecurityValidator(db_conn)

    def execute_safely(self, sql: str) -> List[Dict[str, Any]]:
        """Validate and execute query, applying security constraints."""
        is_safe, error = self.validator.validate(sql)
        if not is_safe:
            logger.warning(f"SQL security violation blocked: {error}")
            raise PermissionError(error)

        try:
            limited_sql = sql
            clean_sql_upper = sql.upper().strip()
            if "LIMIT " not in clean_sql_upper:
                limited_sql = sql.rstrip().rstrip(';') + f" LIMIT {SQLPolicy.MAX_RESULT_ROWS}"

            res = self.conn.execute(limited_sql)
            cols = [desc[0] for desc in res.description]
            rows = res.fetchall()

            return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            logger.error(f"Safe SQL execution failed: {str(e)}")
            raise e


class SemanticQueryValidator:
    """Validates query completeness and semantic alignment with user intent pre-execution."""

    @staticmethod
    def validate_semantic_sql(sql: str, user_query: str) -> Tuple[bool, Optional[str]]:
        """
        Verify that generated SQL is completely formed and does not contain dangling/incomplete clauses.
        Returns (is_valid, error_message).
        """
        if not sql or not sql.strip():
            return False, "Generated SQL statement is empty."

        clean_sql = sql.strip().rstrip(";")
        upper_sql = clean_sql.upper()

        # 1. Check trailing keywords
        for trailing_kw in ["WHERE", "GROUP BY", "ORDER BY", "HAVING", "ON", "JOIN", "LIMIT", "AND", "OR"]:
            if upper_sql.endswith(f" {trailing_kw}") or upper_sql == trailing_kw:
                return False, f"Incomplete SQL: Query statement ends abruptly with '{trailing_kw}' without conditions."

        # 2. Check empty WHERE clause patterns
        invalid_where_patterns = [
            r"\bWHERE\s*$",
            r"\bWHERE\s+(?:LIMIT|GROUP|ORDER|HAVING|UNION|JOIN|;)",
        ]
        for pattern in invalid_where_patterns:
            if re.search(pattern, upper_sql, re.IGNORECASE):
                return False, "Incomplete SQL: WHERE clause is empty or missing predicate condition."

        # 3. Check for specific location/city filter requested by user (e.g. "in Chennai")
        location_match = re.search(r"\bin\s+([A-Za-z]+)", user_query)
        if location_match:
            location_val = location_match.group(1).lower()
            stop_words = {"details", "general", "total", "summary", "revenue", "sales", "inventory", "stock", "monthly", "yearly", "our", "the", "a", "an"}
            if location_val not in stop_words and len(location_val) > 2:
                if "WHERE" not in upper_sql and location_val not in upper_sql.lower():
                    return False, f"Semantic filter missing: Query requests location '{location_val}', but generated SQL lacks a filter predicate."

        return True, None


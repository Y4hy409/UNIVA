"""
CLARIUS Backend - SQL Validation Agent

This agent validates generated SQL statements to prevent execution of
destructive queries or access to restricted system entities (P1.3).
"""

import logging
from typing import Tuple
from app.infrastructure.sql_validator import SQLSecurityValidator

logger = logging.getLogger("clarius.ai.agents.validation")

class SQLValidationAgent:
    """Evaluates safety profiles of translated query scripts."""

    def __init__(self):
        # We pass None since we don't need a live DB connection helper for static AST token checks
        self.validator = SQLSecurityValidator(None)

    def validate_sql(self, sql_query: str) -> Tuple[bool, str]:
        """Validate query and return success state plus error detail."""
        try:
            is_safe, error_msg = self.validator.validate(sql_query)
            return is_safe, error_msg or ""
        except Exception as e:
            logger.error(f"SQL Validation Agent check failed: {str(e)}")
            return False, f"Unexpected error during query validation: {str(e)}"

"""
CLARIUS Backend - Schema Retrieval Agent

This agent retrieves structural metadata, table schemas, and layout configurations (P1.3).
"""

import logging
from typing import Dict, Any, List
import duckdb

logger = logging.getLogger("clarius.ai.agents.schema")

class SchemaRetrievalAgent:
    """Discovers table structure, column mappings, and data formats from the database connection."""

    def __init__(self, db_conn: Any):
        self.conn = db_conn

    def discover_schemas(self) -> Dict[str, List[Dict[str, Any]]]:
        """Query and scan tables schema mapping information."""
        try:
            tables_res = self.conn.execute("SHOW TABLES;").fetchall()
            schema_info = {}
            
            for row in tables_res:
                table_name = row[0]
                # Filter out system tables
                if table_name in ("users", "organizations", "audit_logs", "dashboards", "reports", "documents", "queries"):
                    continue
                    
                info_res = self.conn.execute(f"PRAGMA table_info({table_name});").fetchall()
                schema_info[table_name] = [
                    {"column_name": col[1], "data_type": col[2]}
                    for col in info_res
                ]
                
            logger.info("Database schema context successfully discovered.")
            return schema_info
        except Exception as e:
            logger.error(f"Failed to discover database schemas: {str(e)}")
            return {}

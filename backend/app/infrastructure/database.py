"""
CLARIUS Backend - Database Infrastructure

This module handles connection management for DuckDB, which serves as our
structured transaction and analytics store. It also manages schema migrations
for the Common Data Model (CDM).
"""

import os
from pathlib import Path
from typing import Generator, Optional, Any
import duckdb
from app.core.config import settings

try:
    import psycopg2
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

class DatabaseManager:
    """Manager class for DuckDB/PostgreSQL connection and migrations."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.DUCKDB_PATH
        # Ensure parent folder exists
        if settings.DB_ENGINE != "postgres":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None

    def get_connection(self) -> Any:
        """Get or establish the persistent DuckDB/PostgreSQL connection."""
        if self.conn is None:
            if settings.DB_ENGINE == "postgres":
                if not POSTGRES_AVAILABLE:
                    raise ImportError("psycopg2 is required to connect to PostgreSQL.")
                self.conn = psycopg2.connect(settings.DATABASE_URL)
            else:
                # Connect to file (shared/read-write mode)
                self.conn = duckdb.connect(str(self.db_path))
                # Enable auto-commit configuration if supported or set standard configs
                self.conn.execute("SET preserve_insertion_order=true;")
        return self.conn

    def initialize_schema(self) -> None:
        """Create initial tables for the CLARIUS platform (CDM)."""
        conn = self.get_connection()
        
        # User table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR PRIMARY KEY,
                username VARCHAR UNIQUE,
                email VARCHAR UNIQUE,
                hashed_password VARCHAR,
                role VARCHAR,
                is_active BOOLEAN,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            );
        """)
        
        # Organization / Tenant Configuration
        conn.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                id VARCHAR PRIMARY KEY,
                name VARCHAR,
                license_key VARCHAR,
                edition VARCHAR,
                max_users INTEGER,
                max_branches INTEGER,
                modules VARCHAR[],
                expiry_date TIMESTAMP,
                is_active BOOLEAN,
                created_at TIMESTAMP
            );
        """)

        # Data Sources configuration
        conn.execute("""
            CREATE TABLE IF NOT EXISTS data_sources (
                id VARCHAR PRIMARY KEY,
                name VARCHAR,
                source_type VARCHAR,
                connection_config VARCHAR, -- Encrypted string
                schema_info VARCHAR,      -- JSON-serialized info
                is_connected BOOLEAN,
                last_sync TIMESTAMP,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            );
        """)

        # Natural Language Queries log & results cache
        conn.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                id VARCHAR PRIMARY KEY,
                user_id VARCHAR,
                query_text VARCHAR,
                generated_sql VARCHAR,
                status VARCHAR,
                result VARCHAR,            -- JSON string or error message
                error_message VARCHAR,
                execution_time_ms INTEGER,
                created_at TIMESTAMP,
                completed_at TIMESTAMP
            );
        """)

        # Dashboards
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dashboards (
                id VARCHAR PRIMARY KEY,
                name VARCHAR,
                description VARCHAR,
                owner_id VARCHAR,
                widgets VARCHAR,            -- JSON string representation
                layout VARCHAR,             -- JSON string representation
                is_shared BOOLEAN,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            );
        """)

        # Reports config
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id VARCHAR PRIMARY KEY,
                name VARCHAR,
                description VARCHAR,
                query_id VARCHAR,
                sql_query VARCHAR,
                visualization_type VARCHAR,
                schedule VARCHAR,           -- JSON string representation
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            );
        """)

        # Knowledge base document index (ChromaDB links)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id VARCHAR PRIMARY KEY,
                title VARCHAR,
                content VARCHAR,
                doc_type VARCHAR,
                metadata VARCHAR,           -- JSON string representation
                embedding_id VARCHAR,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            );
        """)

        # Audit logs
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id VARCHAR PRIMARY KEY,
                user_id VARCHAR,
                action VARCHAR,
                resource_type VARCHAR,
                resource_id VARCHAR,
                details VARCHAR,            -- JSON string representation
                ip_address VARCHAR,
                timestamp TIMESTAMP
            );
        """)

    def close(self) -> None:
        """Close current connection."""
        if self.conn:
            self.conn.close()
            self.conn = None


# Single instance for the application lifecycle
db_manager = DatabaseManager()

def get_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """FastAPI Dependency yield database connection."""
    conn = db_manager.get_connection()
    yield conn

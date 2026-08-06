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

        # RBAC Tables
        conn.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id VARCHAR PRIMARY KEY,
                name VARCHAR,
                description VARCHAR
            );
        """)
        # Ensure user profile fields exist on users table
        for col_def in [
            "full_name VARCHAR",
            "phone VARCHAR",
            "department VARCHAR DEFAULT 'Sales Team'",
            "branch VARCHAR DEFAULT 'Anna Nagar Branch'",
            "team VARCHAR DEFAULT 'Sales Team'",
            "status VARCHAR DEFAULT 'Active'",
            "reporting_manager VARCHAR",
            "employee_id VARCHAR",
            "joining_date VARCHAR"
        ]:
            try:
                conn.execute(f"ALTER TABLE users ADD COLUMN {col_def};")
            except Exception:
                pass

        conn.execute("""
            CREATE TABLE IF NOT EXISTS permissions (
                id VARCHAR PRIMARY KEY,
                name VARCHAR,
                description VARCHAR
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_roles (
                user_id VARCHAR,
                role_id VARCHAR,
                PRIMARY KEY (user_id, role_id)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS role_permissions (
                role_id VARCHAR,
                permission_id VARCHAR,
                PRIMARY KEY (role_id, permission_id)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS role_hierarchy (
                parent_role_id VARCHAR,
                child_role_id VARCHAR,
                PRIMARY KEY (parent_role_id, child_role_id)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS access_scopes (
                id VARCHAR PRIMARY KEY,
                scope_type VARCHAR,
                scope_value VARCHAR
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_access_scopes (
                user_id VARCHAR,
                scope_id VARCHAR,
                PRIMARY KEY (user_id, scope_id)
            );
        """)

        # Branch Management Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS branches (
                id VARCHAR PRIMARY KEY,
                code VARCHAR UNIQUE,
                name VARCHAR,
                location VARCHAR,
                manager_id VARCHAR,
                manager_name VARCHAR,
                phone VARCHAR,
                operating_hours VARCHAR,
                description VARCHAR,
                status VARCHAR DEFAULT 'Active',
                created_at TIMESTAMP
            );
        """)

        # Department Management Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id VARCHAR PRIMARY KEY,
                code VARCHAR UNIQUE,
                name VARCHAR,
                branch VARCHAR,
                manager_name VARCHAR,
                description VARCHAR,
                status VARCHAR DEFAULT 'Active',
                created_at TIMESTAMP
            );
        """)

        # Seeding Default Roles
        default_roles = [
            ("owner", "Owner", "Full system owner access"),
            ("admin", "Admin", "System administrator access"),
            ("manager", "Manager", "Branch manager access"),
            ("analyst", "Analyst", "Data analyst access"),
            ("staff", "Staff", "Regular staff access")
        ]
        for rid, name, desc in default_roles:
            conn.execute(
                "INSERT OR IGNORE INTO roles (id, name, description) VALUES (?, ?, ?)",
                [rid, name, desc]
            )

        # Seeding Default Permissions
        default_perms = [
            ("license.manage", "Manage Licensing", "Upload and verify system licenses"),
            ("audit.read", "Read Audit Logs", "View system operation audit logs"),
            ("system.settings.update", "Update Settings", "Update general system settings"),
            ("system.health.read", "Read System Health", "Monitor local health statuses"),
            ("sales.read", "Read Sales Data", "Query sales transactions and details"),
            ("sales.create", "Create Sales Data", "Create or import sales records"),
            ("inventory.read", "Read Inventory Data", "View stock levels and inventory"),
            ("inventory.create", "Create Inventory Data", "Modify or add stock items"),
            ("reports.read", "Read Reports", "Access and download generated reports")
        ]
        for pid, name, desc in default_perms:
            conn.execute(
                "INSERT OR IGNORE INTO permissions (id, name, description) VALUES (?, ?, ?)",
                [pid, name, desc]
            )

        # Seeding Role Permissions (direct mapping, hierarchy will resolve inherited ones)
        role_perm_mappings = {
            "owner": ["license.manage", "audit.read", "system.settings.update", "system.health.read", "sales.read", "sales.create", "inventory.read", "inventory.create", "reports.read"],
            "admin": ["license.manage", "audit.read", "system.settings.update", "system.health.read"],
            "manager": ["sales.read", "sales.create", "inventory.read", "inventory.create", "reports.read"],
            "analyst": ["sales.read", "inventory.read", "reports.read"],
            "staff": ["inventory.read"]
        }
        for role_id, perm_ids in role_perm_mappings.items():
            for perm_id in perm_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
                    [role_id, perm_id]
                )

        # Seeding Role Hierarchy
        # Parent -> Child. Child inherits from Parent (e.g. Manager gets Admin's permissions)
        hierarchy_seeds = [
            ("owner", "admin"),
            ("admin", "manager"),
            ("manager", "analyst"),
            ("analyst", "staff")
        ]
        for parent, child in hierarchy_seeds:
            conn.execute(
                "INSERT OR IGNORE INTO role_hierarchy (parent_role_id, child_role_id) VALUES (?, ?)",
                [parent, child]
            )

        # Database Index Coverage for Optimized Query Performance
        for idx_sql in [
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
            "CREATE INDEX IF NOT EXISTS idx_users_dept ON users(department);",
            "CREATE INDEX IF NOT EXISTS idx_users_branch ON users(branch);",
            "CREATE INDEX IF NOT EXISTS idx_branches_code ON branches(code);",
            "CREATE INDEX IF NOT EXISTS idx_departments_code ON departments(code);"
        ]:
            try:
                conn.execute(idx_sql)
            except Exception:
                pass

        # Migrate existing users to user_roles
        try:
            conn.execute("""
                INSERT OR IGNORE INTO user_roles (user_id, role_id)
                SELECT id, role FROM users WHERE role IS NOT NULL;
            """)
        except Exception:
            pass

        # Seed default admin user if no users exist in database
        try:
            user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            if user_count == 0:
                from app.infrastructure.security import hash_password
                from datetime import datetime
                from uuid import uuid4
                admin_id = str(uuid4())
                hashed_pwd = hash_password("password@123")
                now = datetime.utcnow()
                conn.execute(
                    "INSERT INTO users (id, username, email, hashed_password, role, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    [admin_id, "admin", "admin@clarius.local", hashed_pwd, "admin", True, now, now]
                )
                conn.execute(
                    "INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)",
                    [admin_id, "admin"]
                )
        except Exception:
            pass



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

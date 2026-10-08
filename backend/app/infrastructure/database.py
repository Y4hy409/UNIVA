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
    
    def __init__(self, db_path: Optional[Any] = None):
        self.db_path = db_path or settings.DUCKDB_PATH
        if isinstance(self.db_path, str) and self.db_path != ":memory:":
            self.db_path = Path(self.db_path)
        # Ensure parent folder exists if file path
        if settings.DB_ENGINE != "postgres" and isinstance(self.db_path, Path):
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

        # Dataset Versioning History
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dataset_versions (
                id VARCHAR PRIMARY KEY,
                dataset_name VARCHAR,
                version_number INTEGER,
                file_path VARCHAR,
                file_size BIGINT,
                checksum VARCHAR,
                row_count INTEGER,
                column_count INTEGER,
                schema_hash VARCHAR,
                import_mode VARCHAR,
                is_current BOOLEAN,
                created_at TIMESTAMP,
                created_by VARCHAR
            );
        """)

        # Document Knowledge Versioning History
        conn.execute("""
            CREATE TABLE IF NOT EXISTS document_versions (
                id VARCHAR PRIMARY KEY,
                doc_id VARCHAR,
                version_number INTEGER,
                file_path VARCHAR,
                file_size BIGINT,
                content_hash VARCHAR,
                word_count INTEGER,
                page_count INTEGER,
                is_current BOOLEAN,
                created_at TIMESTAMP,
                created_by VARCHAR
            );
        """)

        # Sync Jobs & Connectors History
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_history (
                id VARCHAR PRIMARY KEY,
                source_id VARCHAR,
                source_name VARCHAR,
                source_type VARCHAR,
                sync_mode VARCHAR,
                status VARCHAR,
                records_processed INTEGER,
                records_inserted INTEGER,
                records_updated INTEGER,
                records_deleted INTEGER,
                duration_ms INTEGER,
                error_message VARCHAR,
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
            "department VARCHAR DEFAULT ''",
            "branch VARCHAR DEFAULT ''",
            "team VARCHAR DEFAULT ''",
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

        # Persistent Conversation History Tables
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id VARCHAR PRIMARY KEY,
                user_id VARCHAR,
                title VARCHAR,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                last_message_at TIMESTAMP,
                pinned BOOLEAN DEFAULT FALSE,
                archived BOOLEAN DEFAULT FALSE,
                message_count INTEGER DEFAULT 0,
                preview VARCHAR
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id VARCHAR PRIMARY KEY,
                conversation_id VARCHAR,
                role VARCHAR,
                content VARCHAR,
                created_at TIMESTAMP,
                intent VARCHAR,
                query_metadata VARCHAR,
                sql_metadata VARCHAR,
                visualization_metadata VARCHAR
            );
        """)

        # Cross-Functional Business Memory Layer Tables
        conn.execute("""
            CREATE TABLE IF NOT EXISTS business_memory (
                id VARCHAR PRIMARY KEY,
                category VARCHAR,
                user_id VARCHAR,
                workspace_id VARCHAR,
                title VARCHAR,
                content VARCHAR,
                structured_data VARCHAR,
                provenance_source VARCHAR,
                info_type VARCHAR,
                status VARCHAR,
                confidence DOUBLE,
                source_dataset VARCHAR,
                source_version INTEGER,
                entity_tags VARCHAR,
                metric_tags VARCHAR,
                time_range VARCHAR,
                is_verified BOOLEAN,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS analytical_artifacts (
                id VARCHAR PRIMARY KEY,
                memory_id VARCHAR,
                name VARCHAR,
                query_text VARCHAR,
                generated_sql VARCHAR,
                filters VARCHAR,
                dimensions VARCHAR,
                measures VARCHAR,
                dataset_name VARCHAR,
                dataset_version INTEGER,
                result_metadata VARCHAR,
                chart_config VARCHAR,
                summary VARCHAR,
                status VARCHAR,
                user_id VARCHAR,
                workspace_id VARCHAR,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_dependencies (
                id VARCHAR PRIMARY KEY,
                memory_id VARCHAR,
                artifact_id VARCHAR,
                dataset_name VARCHAR,
                dataset_version INTEGER,
                columns_used VARCHAR,
                created_at TIMESTAMP
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS business_definitions (
                id VARCHAR PRIMARY KEY,
                term VARCHAR,
                definition VARCHAR,
                formula VARCHAR,
                workspace_id VARCHAR,
                is_approved BOOLEAN,
                approved_by VARCHAR,
                status VARCHAR,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS recommendation_records (
                id VARCHAR PRIMARY KEY,
                title VARCHAR,
                recommendation_text VARCHAR,
                supporting_facts VARCHAR,
                analytical_artifact_ids VARCHAR,
                reasoning VARCHAR,
                confidence DOUBLE,
                generated_by VARCHAR,
                approval_status VARCHAR,
                approved_by VARCHAR,
                user_id VARCHAR,
                workspace_id VARCHAR,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS approval_requests (
                id VARCHAR PRIMARY KEY,
                request_type VARCHAR,
                description VARCHAR,
                context_data VARCHAR,
                status VARCHAR,
                user_id VARCHAR,
                workspace_id VARCHAR,
                created_at TIMESTAMP,
                resolved_at TIMESTAMP
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
            "CREATE INDEX IF NOT EXISTS idx_departments_code ON departments(code);",
            "CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at);",
            "CREATE INDEX IF NOT EXISTS idx_conv_messages_conv ON conversation_messages(conversation_id);"
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

        # Automatically seed tabular business datasets from synthetic_micro_enterprise/data
        try:
            self.seed_business_dataset()
        except Exception as se:
            import logging
            logging.getLogger("clarius.database").warning(f"Business dataset auto-seeding notice: {se}")

    def seed_business_dataset(self) -> None:
        """Automatically import CSV business dataset files from synthetic_micro_enterprise/data into DuckDB."""
        import logging
        logger = logging.getLogger("clarius.database")
        conn = self.get_connection()

        curr = Path(__file__).resolve()
        base_dir = None
        for p in curr.parents:
            if (p / "synthetic_micro_enterprise" / "data").exists():
                base_dir = p / "synthetic_micro_enterprise" / "data"
                break

        if not base_dir or not base_dir.exists():
            return

        existing_tables = {t[0].lower() for t in conn.execute("SHOW TABLES").fetchall()}

        for csv_file in base_dir.glob("*/*.csv"):
            tbl_name = csv_file.stem.lower()
            if tbl_name not in existing_tables:
                try:
                    conn.execute(f"CREATE TABLE {tbl_name} AS SELECT * FROM read_csv_auto('{str(csv_file)}', ignore_errors=true);")
                    row_cnt = conn.execute(f"SELECT COUNT(*) FROM {tbl_name}").fetchone()[0]
                    existing_tables.add(tbl_name)
                    logger.info(f"Seeded business dataset table '{tbl_name}': {row_cnt} rows from {csv_file.name}")
                except Exception as ie:
                    logger.warning(f"Failed to seed business dataset table '{tbl_name}': {ie}")

        try:
            conn.execute("CHECKPOINT;")
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

"""
CLARIUS Backend - Domain Entities

This module contains the core domain entities for the CLARIUS platform.
These entities represent the business objects and are independent of any
database or external system concerns.

Architecture Decision:
- Domain-driven design with clean separation of concerns
- Entities are the core business objects with identity
- Value objects represent descriptive aspects without identity
- All entities use Pydantic for validation and serialization
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4


class UserRole(str, Enum):
    """User roles for RBAC."""
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    STAFF = "staff"


class DataSourceType(str, Enum):
    """Supported data source types."""
    CSV = "csv"
    EXCEL = "excel"
    XML = "xml"
    JSON = "json"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLSERVER = "sqlserver"
    SQLITE = "sqlite"
    REST_API = "rest_api"
    ERPNEXT = "erpnext"
    ODOO = "odoo"
    TALLY = "tally"
    BUSY = "busy"
    MARG = "marg"
    ZOHO = "zoho_books"


class QueryStatus(str, Enum):
    """Status of a natural language query."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class User(BaseModel):
    """User entity representing a platform user."""
    id: UUID = Field(default_factory=uuid4)
    username: str
    email: str
    hashed_password: str
    role: UserRole = UserRole.STAFF
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class Organization(BaseModel):
    """Organization entity representing a company using CLARIUS."""
    id: UUID = Field(default_factory=uuid4)
    name: str
    license_key: str
    edition: str = "CLARIUS"
    max_users: int = 5
    max_branches: int = 1
    modules: List[str] = []
    expiry_date: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DataSource(BaseModel):
    """Data source entity representing a connection to business data."""
    id: UUID = Field(default_factory=uuid4)
    name: str
    source_type: DataSourceType
    connection_config: Dict[str, Any] = {}  # Encrypted in storage
    schema_info: Optional[Dict[str, Any]] = None
    is_connected: bool = False
    last_sync: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class NaturalLanguageQuery(BaseModel):
    """Natural language query entity."""
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    query_text: str
    generated_sql: Optional[str] = None
    status: QueryStatus = QueryStatus.PENDING
    result: Optional[Any] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class Dashboard(BaseModel):
    """Dashboard entity for storing dashboard configurations."""
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    owner_id: UUID
    widgets: List[Dict[str, Any]] = []
    layout: Dict[str, Any] = {}
    is_shared: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Report(BaseModel):
    """Report entity for storing report configurations."""
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    query_id: Optional[UUID] = None
    sql_query: str
    visualization_type: str = "table"
    schedule: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Document(BaseModel):
    """Document entity for knowledge base documents."""
    id: UUID = Field(default_factory=uuid4)
    title: str
    content: str
    doc_type: str  # policy, manual, SOP, report, invoice, etc.
    metadata: Dict[str, Any] = {}
    embedding_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AuditLog(BaseModel):
    """Audit log for tracking user actions."""
    id: UUID = Field(default_factory=uuid4)
    user_id: Optional[UUID] = None
    action: str
    resource_type: str
    resource_id: Optional[UUID] = None
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
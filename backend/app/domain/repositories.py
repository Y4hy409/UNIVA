"""
CLARIUS Backend - Domain Repository Protocols

This module defines repository interfaces and connection provider protocols (P1.1).
"""

from typing import Protocol, Any, List, Optional, Dict
from uuid import UUID
from app.domain.entities import User, UserRole

class IDatabaseConnectionProvider(Protocol):
    """Protocol for database connection management."""
    def get_connection(self) -> Any: ...


class IUserRepository(Protocol):
    """Protocol defining user persistence operations."""
    
    def get_by_username(self, username: str) -> Optional[User]: ...
    def get_by_id(self, user_id: UUID) -> Optional[User]: ...
    def get_all(self) -> List[User]: ...
    def count_users(self) -> int: ...
    def create_user(self, user: User) -> User: ...
    def update_user(self, user: User) -> User: ...


class IDocumentRepository(Protocol):
    """Protocol defining document persistence operations."""
    
    def save_document(
        self,
        doc_id: str,
        title: str,
        content: str,
        doc_type: str,
        metadata_dict: Dict[str, Any],
        embedding_id: str
    ) -> None: ...
    
    def get_document_metadata(self, doc_id: str) -> Optional[Dict[str, Any]]: ...

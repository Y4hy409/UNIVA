"""
CLARIUS Backend - Infrastructure DuckDB Repositories

This module implements the concrete data access repositories for DuckDB (P1.1).
"""

import json
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any, List
import duckdb

from app.domain.entities import User, UserRole
from app.domain.repositories import IDatabaseConnectionProvider, IUserRepository, IDocumentRepository

class DuckDBUserRepository(IUserRepository):
    """DuckDB concrete implementation of IUserRepository."""

    def __init__(self, provider: IDatabaseConnectionProvider):
        self.provider = provider

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        return self.provider.get_connection()

    @staticmethod
    def _parse_role(role_val: Any) -> UserRole:
        if isinstance(role_val, UserRole):
            return role_val
        if isinstance(role_val, str):
            try:
                return UserRole(role_val.lower())
            except ValueError:
                pass
        try:
            return UserRole(role_val)
        except Exception:
            return UserRole.STAFF

    def get_by_username(self, username: str) -> Optional[User]:
        conn = self._get_connection()
        res = conn.execute(
            "SELECT id, username, email, hashed_password, role, is_active, created_at, updated_at FROM users WHERE username = ?",
            [username]
        ).fetchone()
        
        if not res:
            return None
            
        return User(
            id=UUID(res[0]),
            username=res[1],
            email=res[2],
            hashed_password=res[3],
            role=self._parse_role(res[4]),
            is_active=res[5],
            created_at=res[6],
            updated_at=res[7]
        )

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        conn = self._get_connection()
        res = conn.execute(
            "SELECT id, username, email, hashed_password, role, is_active, created_at, updated_at FROM users WHERE id = ?",
            [str(user_id)]
        ).fetchone()
        
        if not res:
            return None
            
        return User(
            id=UUID(res[0]),
            username=res[1],
            email=res[2],
            hashed_password=res[3],
            role=self._parse_role(res[4]),
            is_active=res[5],
            created_at=res[6],
            updated_at=res[7]
        )

    def count_users(self) -> int:
        conn = self._get_connection()
        res = conn.execute("SELECT COUNT(*) FROM users").fetchone()
        return res[0] if res else 0

    def create_user(self, user: User) -> User:
        conn = self._get_connection()
        role_str = user.role.value if hasattr(user.role, 'value') else str(user.role)
        conn.execute(
            "INSERT INTO users (id, username, email, hashed_password, role, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [str(user.id), user.username, user.email, user.hashed_password, role_str, user.is_active, user.created_at, user.updated_at]
        )
        return user

    def update_user(self, user: User) -> User:
        conn = self._get_connection()
        role_str = user.role.value if hasattr(user.role, 'value') else str(user.role)
        conn.execute(
            "UPDATE users SET username = ?, email = ?, hashed_password = ?, role = ?, is_active = ?, updated_at = ? WHERE id = ?",
            [user.username, user.email, user.hashed_password, role_str, user.is_active, user.updated_at, str(user.id)]
        )
        return user

    def get_all(self) -> List[User]:
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT id, username, email, hashed_password, role, is_active, created_at, updated_at FROM users"
        ).fetchall()
        
        users = []
        for res in rows:
            users.append(User(
                id=UUID(res[0]),
                username=res[1],
                email=res[2],
                hashed_password=res[3],
                role=self._parse_role(res[4]),
                is_active=res[5],
                created_at=res[6],
                updated_at=res[7]
            ))
        return users


class DuckDBDocumentRepository(IDocumentRepository):
    """DuckDB concrete implementation of IDocumentRepository."""

    def __init__(self, provider: IDatabaseConnectionProvider):
        self.provider = provider

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        return self.provider.get_connection()

    def save_document(
        self,
        doc_id: str,
        title: str,
        content: str,
        doc_type: str,
        metadata_dict: Dict[str, Any],
        embedding_id: str
    ) -> None:
        conn = self._get_connection()
        now = datetime.utcnow()
        metadata_json = json.dumps(metadata_dict)
        
        conn.execute(
            """
            INSERT INTO documents (id, title, content, doc_type, metadata, embedding_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [doc_id, title, content, doc_type, metadata_json, embedding_id, now, now]
        )

    def get_document_metadata(self, doc_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        res = conn.execute(
            "SELECT id, title, doc_type, metadata, created_at FROM documents WHERE id = ?",
            [doc_id]
        ).fetchone()
        
        if not res:
            return None
            
        try:
            meta = json.loads(res[3])
        except Exception:
            meta = {}
            
        return {
            "id": res[0],
            "title": res[1],
            "doc_type": res[2],
            "metadata": meta,
            "created_at": res[4]
        }

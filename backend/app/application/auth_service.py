"""
CLARIUS Backend - Authentication Service

This service orchestrates security checks, logins, and registrations
mapping domain User concepts to repository persistence boundaries (P1.1).
"""

from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional

from app.domain.entities import User, UserRole
from app.domain.repositories import IUserRepository
from app.infrastructure.security import hash_password, verify_password
from app.infrastructure.licensing import capability_service

class AuthService:
    """Authentication and User Lifecycle orchestrator using repository boundaries."""
    
    def __init__(self, user_repo: IUserRepository):
        self.user_repo = user_repo

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Fetch user by username from user repository."""
        return self.user_repo.get_by_username(username)

    def count_users(self) -> int:
        """Count registered users in system."""
        return self.user_repo.count_users()

    def create_owner(self, username: str, email: str, password: str) -> User:
        """Create the first user (System Owner)."""
        # Ensure database is empty before allowing first Owner signup
        if self.count_users() > 0:
            raise ValueError("An owner has already been configured on this installation.")
            
        user = User(
            id=uuid4(),
            username=username,
            email=email,
            hashed_password=hash_password(password),
            role=UserRole.OWNER,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.user_repo.create_user(user)
        return user

    def register_user(self, username: str, email: str, password: str, role: UserRole) -> User:
        """Register a user checking license limits."""
        # 1. Enforce user limit from offline licensing
        limits = capability_service.get_limits()
        current_count = self.count_users()
        if current_count >= limits.max_users:
            raise PermissionError(f"License limit reached. Maximum users allowed: {limits.max_users}")
            
        # 2. Check if username exists
        if self.get_user_by_username(username):
            raise ValueError("Username already taken")
            
        user = User(
            id=uuid4(),
            username=username,
            email=email,
            hashed_password=hash_password(password),
            role=role,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.user_repo.create_user(user)
        return user

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user using credentials."""
        user = self.get_user_by_username(username)
        if not user or not user.is_active:
            return None
            
        if not verify_password(password, user.hashed_password):
            return None
            
        return user

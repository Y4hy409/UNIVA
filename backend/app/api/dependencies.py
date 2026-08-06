"""
CLARIUS Backend - API Security Dependencies

This module implements JWT bearer token validation and Role-Based Access Control (RBAC) checks (P1.2).
"""

from typing import List
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.domain.entities import User, UserRole
from app.domain.repositories import IUserRepository
from app.infrastructure.security import decode_access_token
from app.infrastructure.database import db_manager
from app.infrastructure.repositories import DuckDBUserRepository

security_scheme = HTTPBearer()

def get_user_repository() -> DuckDBUserRepository:
    return DuckDBUserRepository(db_manager)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    user_repo: IUserRepository = Depends(get_user_repository)
) -> User:
    """Validate bearer token and resolve active database user context."""
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    try:
        user_id = UUID(payload.get("sub"))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed session identity context.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user = user_repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session user is deactivated or missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return user


from app.api.authorization_service import authorization_service

class RoleChecker:
    """FastAPI dependency gate evaluating user role memberships."""
    
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        # Fetch the user's roles from DB
        user_roles = authorization_service.get_user_roles(current_user.id)
        
        # Keep user's default role as fallback
        role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
        user_roles.add(role_val)
        
        allowed_vals = [r.value if hasattr(r, "value") else str(r) for r in self.allowed_roles]
        
        if not any(ur in allowed_vals for ur in user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Insufficient role permissions."
            )
        return current_user


class PermissionChecker:
    """FastAPI dependency gate evaluating user permission context."""
    
    def __init__(self, permission: str):
        self.permission = permission

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if not authorization_service.authorize(current_user.id, self.permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Insufficient permission '{self.permission}'."
            )
        return current_user


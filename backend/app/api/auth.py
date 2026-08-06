"""
CLARIUS Backend - Authentication Routes

This module implements FastAPI routes for the first-time setup wizard (Owner signup)
and user token generation using dependency injection providers (P1.1).
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.application.auth_service import AuthService
from app.infrastructure.security import create_access_token
from app.infrastructure.database import db_manager
from app.infrastructure.repositories import DuckDBUserRepository
from app.api.dependencies import RoleChecker
from app.domain.entities import UserRole

router = APIRouter(prefix="/auth", tags=["authentication"])

# Dependency Injection Providers
def get_user_repository() -> DuckDBUserRepository:
    return DuckDBUserRepository(db_manager)

def get_auth_service(repo: DuckDBUserRepository = Depends(get_user_repository)) -> AuthService:
    return AuthService(repo)


class SetupOwnerRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class UserSetupStatusResponse(BaseModel):
    is_setup: bool


@router.get("/status", response_model=UserSetupStatusResponse)
async def get_setup_status(service: AuthService = Depends(get_auth_service)):
    """Check if the owner has been set up yet (used by setup wizard)."""
    is_setup = service.count_users() > 0
    return UserSetupStatusResponse(is_setup=is_setup)


@router.post("/setup-owner", response_model=TokenResponse)
async def setup_owner(req: SetupOwnerRequest, service: AuthService = Depends(get_auth_service)):
    """Create the first user (System Owner) during startup wizard."""
    try:
        user = service.create_owner(req.username, req.email, req.password)
        role_val = user.role.value if hasattr(user.role, 'value') else str(user.role)
        token = create_access_token(user.id, role_val)
        return TokenResponse(
            access_token=token,
            role=role_val,
            username=user.username
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, service: AuthService = Depends(get_auth_service)):
    """Authenticate user credentials and return a session token."""
    user = service.authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    role_val = user.role.value if hasattr(user.role, 'value') else str(user.role)
    token = create_access_token(user.id, role_val)
    return TokenResponse(
        access_token=token,
        role=role_val,
        username=user.username
    )


@router.post("/reset-db")
async def reset_db(service: AuthService = Depends(get_auth_service)):
    """Developer endpoint to reset users in DuckDB dynamically."""
    try:
        conn = service.user_repo._get_connection()
        conn.execute("DELETE FROM users;")
        return {"status": "success", "message": "All users cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str


class PublicSignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: Optional[str] = "staff"


@router.post("/signup", response_model=TokenResponse)
async def public_signup(req: PublicSignupRequest, service: AuthService = Depends(get_auth_service)):
    """Register a new user account and log in automatically."""
    try:
        requested_role = req.role.lower() if req.role else "staff"
        try:
            role_enum = UserRole(requested_role)
        except Exception:
            role_enum = UserRole.STAFF

        user = service.register_user(req.username, req.email, req.password, role_enum)
        role_val = user.role.value if hasattr(user.role, 'value') else str(user.role)
        token = create_access_token(user.id, role_val)
        return TokenResponse(
            access_token=token,
            role=role_val,
            username=user.username
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )



@router.get("/users")
async def get_users(
    service: AuthService = Depends(get_auth_service),
    _user = Depends(RoleChecker([UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER, UserRole.ANALYST, UserRole.STAFF]))
):
    """List all workspace user profiles."""
    users = service.get_all_users()
    return [
        {
            "username": u.username,
            "role": u.role.value if hasattr(u.role, 'value') else str(u.role)
        } for u in users
    ]


@router.get("/roles")
async def get_roles():
    """Retrieve available system roles dynamically from database."""
    try:
        conn = db_manager.get_connection()
        rows = conn.execute("SELECT id, name, description FROM roles").fetchall()
        if rows:
            return [{"id": r[0], "name": r[1], "description": r[2]} for r in rows]
    except Exception:
        pass
    
    return [
        {"id": "owner", "name": "Owner", "description": "System Owner"},
        {"id": "admin", "name": "Admin", "description": "Administrator"},
        {"id": "manager", "name": "Manager", "description": "Branch Manager"},
        {"id": "analyst", "name": "Analyst", "description": "Data Analyst"},
        {"id": "staff", "name": "Staff", "description": "Staff Member"}
    ]


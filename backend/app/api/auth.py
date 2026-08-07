"""
CLARIUS Backend - Authentication Routes

This module implements FastAPI routes for the first-time setup wizard (Owner signup)
and user token generation using dependency injection providers (P1.1).
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.application.auth_service import AuthService
from app.infrastructure.security import create_access_token, hash_password
from app.infrastructure.database import db_manager
from app.infrastructure.repositories import DuckDBUserRepository
from app.api.dependencies import RoleChecker, get_current_user
from app.domain.entities import UserRole, User

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


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: Optional[str] = None


@router.get("/me")
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Retrieve active authenticated user profile context."""
    conn = db_manager.get_connection()
    row = conn.execute(
        "SELECT email, full_name, phone, department, branch, team, status, employee_id FROM users WHERE id = ?",
        [str(current_user.id)]
    ).fetchone()
    
    email = current_user.email
    full_name = ""
    phone = ""
    department = "Sales Team"
    branch = "Main Branch"
    team = "Core Team"
    status_str = "Active"
    employee_id = ""

    if row:
        email = row[0] or email
        full_name = row[1] or ""
        phone = row[2] or ""
        department = row[3] or department
        branch = row[4] or branch
        team = row[5] or team
        status_str = row[6] or status_str
        employee_id = row[7] or ""

    role_val = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)

    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": email,
        "role": role_val,
        "full_name": full_name,
        "phone": phone,
        "department": department,
        "branch": branch,
        "team": team,
        "status": status_str,
        "employee_id": employee_id
    }


@router.put("/me")
async def update_current_user_profile(
    req: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user)
):
    """Update active user profile context and credentials."""
    conn = db_manager.get_connection()
    updates = []
    params = []

    if req.full_name is not None:
        updates.append("full_name = ?")
        params.append(req.full_name)
    if req.email is not None:
        updates.append("email = ?")
        params.append(req.email)
    if req.phone is not None:
        updates.append("phone = ?")
        params.append(req.phone)
    if req.password:
        updates.append("hashed_password = ?")
        params.append(hash_password(req.password))

    if updates:
        updates.append("updated_at = ?")
        params.append(datetime.utcnow())
        params.append(str(current_user.id))
        conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)

    return {"status": "success", "message": "Profile updated successfully"}


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Invalidate active user session (log out)."""
    return {"status": "success", "message": f"User {current_user.username} logged out successfully."}



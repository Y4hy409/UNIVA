"""
CLARIUS Backend - System Administration and Licensing Router
"""

import os
import json
import shutil
from pathlib import Path
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from app.core.config import settings
from app.infrastructure.database import db_manager
from app.infrastructure.knowledge import knowledge_manager
from app.infrastructure.licensing import capability_service, CapabilityService, LicenseStatus
from app.api.dependencies import PermissionChecker, get_current_user
from app.domain.entities import User
from app.api.authorization_service import authorization_service
from app.modules.audit.application.audit_service import AuditService

router = APIRouter(prefix="/admin", tags=["administration"])

# Paths
SETTINGS_JSON_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "settings.json"

class LicenseUploadPayload(BaseModel):
    license_key: str

class SettingsPayload(BaseModel):
    general: Dict[str, Any] = {}
    ui: Dict[str, Any] = {}
    workspace: Dict[str, Any] = {}


@router.get("/settings", dependencies=[Depends(PermissionChecker("system.settings.update"))])
async def get_settings_config():
    """Read non-sensitive settings from data/settings.json."""
    if not SETTINGS_JSON_PATH.exists():
        # Ensure parent folder exists
        SETTINGS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        default_settings = {
            "general": {"appName": "CLARIUS / UNIVA", "timezone": "UTC"},
            "ui": {"theme": "dark", "sidebarCollapsed": False},
            "workspace": {"folderFlags": {}}
        }
        with open(SETTINGS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(default_settings, f, indent=2)
            
    try:
        with open(SETTINGS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.pop("secrets", None)
        data.pop("license_status", None)
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read settings: {str(e)}"
        )


@router.post("/settings")
async def save_settings_config(payload: SettingsPayload, current_user: User = Depends(get_current_user)):
    """Write non-sensitive settings to data/settings.json."""
    if not authorization_service.authorize(current_user.id, "system.settings.update"):
        raise HTTPException(status_code=403, detail="Insufficient permission")
        
    SETTINGS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    existing = {}
    if SETTINGS_JSON_PATH.exists():
        try:
            with open(SETTINGS_JSON_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass

    existing["general"] = payload.general
    existing["ui"] = payload.ui
    existing["workspace"] = payload.workspace
    existing.pop("secrets", None)
    existing.pop("license_status", None)

    audit = AuditService()
    try:
        with open(SETTINGS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
            
        audit.log_action(
            user_id=str(current_user.id),
            action="UPDATE_SETTINGS",
            resource_type="system_settings",
            details={"result": "SUCCESS", "metadata": {"who": current_user.username}}
        )
        return {"status": "success", "message": "Settings updated successfully"}
    except Exception as e:
        audit.log_action(
            user_id=str(current_user.id),
            action="UPDATE_SETTINGS",
            resource_type="system_settings",
            details={"result": "FAILURE", "error": str(e), "metadata": {"who": current_user.username}}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save settings: {str(e)}"
        )


@router.post("/license/upload")
async def upload_license(payload: LicenseUploadPayload, current_user: User = Depends(get_current_user)):
    """
    Validate license payload before atomically replacing it at config/license.lic.
    """
    if not authorization_service.authorize(current_user.id, "license.manage"):
        raise HTTPException(status_code=403, detail="Insufficient permission")

    temp_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / "uploaded_license.lic"
    audit = AuditService()
    
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(payload.license_key)
            
        temp_service = CapabilityService(temp_file)
        status_val = temp_service.get_license_status()
        
        if status_val not in (LicenseStatus.VALID, LicenseStatus.EXPIRING_SOON, LicenseStatus.GRACE_PERIOD):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid license status: {status_val.value}"
            )
            
        edition = temp_service.license_data.get("edition")
        if not edition or edition.lower() not in ("clarius", "clarius_copilot", "univa"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid product edition in license payload."
            )
            
        deployment = temp_service.license_data.get("deployment", {})
        if not deployment or "fingerprint_strictness" not in deployment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Deployment configuration is missing or malformed."
            )
            
        org = temp_service.license_data.get("organization", {})
        if "max_users" not in org or "max_branches" not in org:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User or branch limits are missing from the license."
            )
            
        try:
            int(org.get("max_users"))
            int(org.get("max_branches"))
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="License limits must be valid integer values."
            )

        dest_file = settings.LICENSE_PATH
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(temp_file, dest_file)
        
        capability_service.reload_license()
        
        audit.log_action(
            user_id=str(current_user.id),
            action="UPLOAD_LICENSE",
            resource_type="license",
            details={
                "edition": edition,
                "max_users": org.get("max_users"),
                "max_branches": org.get("max_branches"),
                "result": "SUCCESS",
                "metadata": {"who": current_user.username}
            }
        )
        
        return {
            "status": "success",
            "message": "License verified and atomically installed.",
            "edition": edition,
            "max_users": org.get("max_users"),
            "max_branches": org.get("max_branches")
        }
    except HTTPException as he:
        audit.log_action(
            user_id=str(current_user.id),
            action="UPLOAD_LICENSE",
            resource_type="license",
            details={"result": "FAILURE", "error": he.detail, "metadata": {"who": current_user.username}}
        )
        raise he
    except Exception as e:
        audit.log_action(
            user_id=str(current_user.id),
            action="UPLOAD_LICENSE",
            resource_type="license",
            details={"result": "FAILURE", "error": str(e), "metadata": {"who": current_user.username}}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"License validation failed: {str(e)}"
        )
    finally:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass


@router.get("/system/health", dependencies=[Depends(PermissionChecker("system.health.read"))])
async def system_health():
    """Expose status check for local AI, DuckDB, ChromaDB, and storage paths."""
    from urllib.request import urlopen, Request
    from urllib.error import URLError
    
    ai_status = "unavailable"
    try:
        url = f"{settings.OLLAMA_HOST}/api/tags"
        req = Request(url, method="GET")
        with urlopen(req, timeout=1.5) as response:
            if response.status == 200:
                ai_status = "healthy"
    except Exception:
        ai_status = "error"
        
    duckdb_status = "unavailable"
    try:
        conn = db_manager.get_connection()
        conn.execute("SELECT 1")
        duckdb_status = "healthy"
    except Exception:
        duckdb_status = "error"
        
    chromadb_status = "unavailable"
    try:
        if knowledge_manager.heartbeat():
            chromadb_status = "healthy"
        else:
            chromadb_status = "warning"
    except Exception:
        chromadb_status = "error"
        
    storage_status = "healthy"
    for path in (settings.DUCKDB_PATH.parent, settings.CHROMADB_PATH.parent):
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception:
                storage_status = "error"
                break
        if not os.access(path, os.W_OK):
            storage_status = "error"
            break
            
    return {
        "status": "healthy" if all(s == "healthy" for s in (ai_status, duckdb_status, chromadb_status, storage_status)) else "warning",
        "components": {
            "local_ai": ai_status,
            "duckdb": duckdb_status,
            "chromadb": chromadb_status,
            "storage_paths": storage_status
        }
    }


# RBAC Management Endpoints
@router.get("/rbac/roles", dependencies=[Depends(PermissionChecker("system.settings.update"))])
async def get_rbac_roles():
    conn = db_manager.get_connection()
    rows = conn.execute("SELECT id, name, description FROM roles").fetchall()
    return [{"id": r[0], "name": r[1], "description": r[2]} for r in rows]


@router.get("/rbac/permissions", dependencies=[Depends(PermissionChecker("system.settings.update"))])
async def get_rbac_permissions():
    conn = db_manager.get_connection()
    rows = conn.execute("SELECT id, name, description FROM permissions").fetchall()
    return [{"id": r[0], "name": r[1], "description": r[2]} for r in rows]


@router.get("/rbac/matrix", dependencies=[Depends(PermissionChecker("system.settings.update"))])
async def get_rbac_matrix():
    conn = db_manager.get_connection()
    roles = conn.execute("SELECT id, name FROM roles").fetchall()
    permissions = conn.execute("SELECT id, name FROM permissions").fetchall()
    mappings = conn.execute("SELECT role_id, permission_id FROM role_permissions").fetchall()
    mapping_set = {(r[0], r[1]) for r in mappings}
    
    matrix = []
    for r in roles:
        role_id, role_name = r[0], r[1]
        role_perms = []
        for p in permissions:
            perm_id = p[0]
            role_perms.append(perm_id in mapping_set)
        matrix.append({
            "role": role_name,
            "role_id": role_id,
            "permissions": role_perms
        })
    return {
        "matrix": matrix,
        "permissions": [{"id": p[0], "name": p[1]} for p in permissions]
    }


class TogglePermissionPayload(BaseModel):
    role_id: str
    permission_id: str
    value: bool

@router.post("/rbac/matrix")
async def toggle_role_permission(payload: TogglePermissionPayload, current_user: User = Depends(get_current_user)):
    if not authorization_service.authorize(current_user.id, "system.settings.update"):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    conn = db_manager.get_connection()
    audit = AuditService()
    try:
        if payload.value:
            conn.execute(
                "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
                [payload.role_id, payload.permission_id]
            )
        else:
            conn.execute(
                "DELETE FROM role_permissions WHERE role_id = ? AND permission_id = ?",
                [payload.role_id, payload.permission_id]
            )
        audit.log_action(
            user_id=str(current_user.id),
            action="UPDATE_ROLE_PERMISSIONS",
            resource_type="role",
            details={
                "role_id": payload.role_id,
                "permission_id": payload.permission_id,
                "assigned": payload.value,
                "result": "SUCCESS",
                "metadata": {"who": current_user.username}
            }
        )
        return {"status": "success"}
    except Exception as e:
        audit.log_action(
            user_id=str(current_user.id),
            action="UPDATE_ROLE_PERMISSIONS",
            resource_type="role",
            details={
                "role_id": payload.role_id,
                "permission_id": payload.permission_id,
                "assigned": payload.value,
                "result": "FAILURE",
                "error": str(e)
            }
        )
        raise HTTPException(status_code=400, detail=str(e))


class UserRolePayload(BaseModel):
    user_id: str
    role_id: str

@router.post("/rbac/user-role")
async def assign_user_role(payload: UserRolePayload, current_user: User = Depends(get_current_user)):
    if not authorization_service.authorize(current_user.id, "system.settings.update"):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    conn = db_manager.get_connection()
    audit = AuditService()
    try:
        conn.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            [payload.role_id, payload.user_id]
        )
        conn.execute(
            "DELETE FROM user_roles WHERE user_id = ?",
            [payload.user_id]
        )
        conn.execute(
            "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
            [payload.user_id, payload.role_id]
        )
        audit.log_action(
            user_id=str(current_user.id),
            action="ASSIGN_USER_ROLE",
            resource_type="user",
            resource_id=payload.user_id,
            details={
                "role_id": payload.role_id,
                "result": "SUCCESS",
                "metadata": {"who": current_user.username}
            }
        )
        return {"status": "success"}
    except Exception as e:
        audit.log_action(
            user_id=str(current_user.id),
            action="ASSIGN_USER_ROLE",
            resource_type="user",
            resource_id=payload.user_id,
            details={
                "role_id": payload.role_id,
                "result": "FAILURE",
                "error": str(e)
            }
        )
        raise HTTPException(status_code=400, detail=str(e))


class RoleHierarchyPayload(BaseModel):
    parent_role_id: str
    child_role_id: str

@router.post("/rbac/hierarchy")
async def add_hierarchy_link(payload: RoleHierarchyPayload, current_user: User = Depends(get_current_user)):
    if not authorization_service.authorize(current_user.id, "system.settings.update"):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    audit = AuditService()
    try:
        authorization_service.add_role_hierarchy(payload.parent_role_id, payload.child_role_id)
        audit.log_action(
            user_id=str(current_user.id),
            action="ADD_ROLE_HIERARCHY",
            resource_type="role_hierarchy",
            details={
                "parent_role_id": payload.parent_role_id,
                "child_role_id": payload.child_role_id,
                "result": "SUCCESS",
                "metadata": {"who": current_user.username}
            }
        )
        return {"status": "success"}
    except Exception as e:
        audit.log_action(
            user_id=str(current_user.id),
            action="ADD_ROLE_HIERARCHY",
            resource_type="role_hierarchy",
            details={
                "parent_role_id": payload.parent_role_id,
                "child_role_id": payload.child_role_id,
                "result": "FAILURE",
                "error": str(e)
            }
        )
        raise HTTPException(status_code=400, detail=str(e))


class UserScopePayload(BaseModel):
    user_id: str
    scope_type: str
    scope_value: str

@router.post("/rbac/user-scope")
async def assign_user_scope(payload: UserScopePayload, current_user: User = Depends(get_current_user)):
    if not authorization_service.authorize(current_user.id, "system.settings.update"):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    conn = db_manager.get_connection()
    audit = AuditService()
    try:
        scope_id = f"{payload.scope_type}_{payload.scope_value}"
        conn.execute(
            "INSERT OR IGNORE INTO access_scopes (id, scope_type, scope_value) VALUES (?, ?, ?)",
            [scope_id, payload.scope_type, payload.scope_value]
        )
        conn.execute(
            "INSERT OR IGNORE INTO user_access_scopes (user_id, scope_id) VALUES (?, ?)",
            [payload.user_id, scope_id]
        )
        audit.log_action(
            user_id=str(current_user.id),
            action="ASSIGN_USER_SCOPE",
            resource_type="user",
            resource_id=payload.user_id,
            details={
                "scope_type": payload.scope_type,
                "scope_value": payload.scope_value,
                "result": "SUCCESS",
                "metadata": {"who": current_user.username}
            }
        )
        return {"status": "success"}
    except Exception as e:
        audit.log_action(
            user_id=str(current_user.id),
            action="ASSIGN_USER_SCOPE",
            resource_type="user",
            resource_id=payload.user_id,
            details={
                "scope_type": payload.scope_type,
                "scope_value": payload.scope_value,
                "result": "FAILURE",
                "error": str(e)
            }
        )
        raise HTTPException(status_code=400, detail=str(e))


class RoleSavePayload(BaseModel):
    id: Optional[str] = None
    name: str
    description: str
    level: int = 10
    status: str = "Active"
    permissions: Dict[str, List[str]] = {}


@router.get("/roles/catalog")
async def get_roles_catalog(current_user: User = Depends(get_current_user)):
    """Fetch all roles with detailed permission mappings, user counts, and levels."""
    conn = db_manager.get_connection()
    try:
        roles_rows = conn.execute("SELECT id, name, description, COALESCE(level, 10), COALESCE(status, 'Active') FROM roles ORDER BY COALESCE(level, 10) DESC").fetchall()
        
        # Get user counts per role
        user_counts_rows = conn.execute("SELECT role, COUNT(*) FROM users GROUP BY role").fetchall()
        user_counts = {r[0]: r[1] for r in user_counts_rows}
        
        # Get permissions mapping per role
        role_perms_rows = conn.execute("""
            SELECT rp.role_id, p.id, p.name 
            FROM role_permissions rp
            JOIN permissions p ON rp.permission_id = p.id
        """).fetchall()
        
        perms_map = {}
        for r_id, p_id, p_name in role_perms_rows:
            if r_id not in perms_map:
                perms_map[r_id] = {}
            mod = "System Control"
            if "." in p_id:
                mod = p_id.split(".")[0].capitalize() + " Management"
            if mod not in perms_map[r_id]:
                perms_map[r_id][mod] = []
            perms_map[r_id][mod].append(p_id)

        result = []
        for r in roles_rows:
            rid, rname, rdesc, rlevel, rstatus = r[0], r[1], r[2], r[3], r[4]
            result.append({
                "id": rid,
                "name": rname,
                "description": rdesc or "",
                "level": rlevel,
                "status": rstatus,
                "permissions": perms_map.get(rid, {}),
                "assigned_users_count": user_counts.get(rid, 0)
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/roles/save")
async def save_role(payload: RoleSavePayload, current_user: User = Depends(get_current_user)):
    """Create or update role definition with level and permission matrix."""
    conn = db_manager.get_connection()
    audit = AuditService()
    try:
        role_id = payload.id or f"role-{int(datetime.utcnow().timestamp())}"
        
        # Upsert role
        conn.execute("""
            INSERT INTO roles (id, name, description, level, status)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                level = EXCLUDED.level,
                status = EXCLUDED.status;
        """, [role_id, payload.name, payload.description, payload.level, payload.status])

        # Update role permissions
        conn.execute("DELETE FROM role_permissions WHERE role_id = ?", [role_id])
        for mod, perms in payload.permissions.items():
            for p_id in perms:
                # Ensure permission exists
                conn.execute(
                    "INSERT OR IGNORE INTO permissions (id, name, description) VALUES (?, ?, ?)",
                    [p_id, p_id, f"Permission {p_id}"]
                )
                conn.execute(
                    "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
                    [role_id, p_id]
                )

        audit.log_action(
            user_id=str(current_user.id),
            action="SAVE_ROLE",
            resource_type="role",
            details={"role_id": role_id, "name": payload.name, "result": "SUCCESS"}
        )
        return {"status": "success", "role_id": role_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/roles/{role_id}")
async def delete_role(role_id: str, current_user: User = Depends(get_current_user)):
    """Delete a custom non-protected role."""
    if role_id in ["owner", "admin"]:
        raise HTTPException(status_code=400, detail="Protected system roles cannot be deleted.")
    conn = db_manager.get_connection()
    try:
        conn.execute("DELETE FROM roles WHERE id = ?", [role_id])
        conn.execute("DELETE FROM role_permissions WHERE role_id = ?", [role_id])
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/organization/hierarchy")
async def get_organization_hierarchy(current_user: User = Depends(get_current_user)):
    """Build parent-child organization hierarchy tree based on real users, roles, and levels."""
    conn = db_manager.get_connection()
    try:
        # Fetch users with their role level, department, and branch
        users_rows = conn.execute("""
            SELECT u.id, u.username, u.email, COALESCE(r.id, u.role) as role_id, COALESCE(r.name, u.role) as role_name, COALESCE(r.level, 10) as level, COALESCE(u.department, 'Sales Team') as department, COALESCE(u.branch, 'Main Branch') as branch
            FROM users u
            LEFT JOIN roles r ON LOWER(u.role) = LOWER(r.id) OR LOWER(u.role) = LOWER(r.name)
            ORDER BY COALESCE(r.level, 10) DESC
        """).fetchall()

        all_nodes = []
        for row in users_rows:
            all_nodes.append({
                "user": {
                    "id": str(row[0]),
                    "name": str(row[1]).capitalize(),
                    "username": str(row[1]),
                    "email": str(row[2]),
                    "department": str(row[6]),
                    "branch": str(row[7])
                },
                "roleId": str(row[3]),
                "role": str(row[4]),
                "level": int(row[5]),
                "children": []
            })

        if not all_nodes:
            return []

        # Group nodes by level descending to form top-down tree
        roots = []
        level_groups = {}
        for node in all_nodes:
            lvl = node["level"]
            if lvl not in level_groups:
                level_groups[lvl] = []
            level_groups[lvl].append(node)

        sorted_levels = sorted(level_groups.keys(), reverse=True)
        if len(sorted_levels) == 1:
            return level_groups[sorted_levels[0]]

        # Build tree linkage where highest level is root
        root_level = sorted_levels[0]
        roots = level_groups[root_level]
        
        # Attach subsequent lower level nodes to upper level nodes
        current_parent_tier = roots
        for next_lvl in sorted_levels[1:]:
            children_tier = level_groups[next_lvl]
            if current_parent_tier:
                # Distribute children across parent nodes
                for idx, child in enumerate(children_tier):
                    parent_idx = idx % len(current_parent_tier)
                    current_parent_tier[parent_idx]["children"].append(child)
                current_parent_tier = children_tier
            else:
                roots.extend(children_tier)

        return roots
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class UserSavePayload(BaseModel):
    id: Optional[str] = None
    username: Optional[str] = None
    full_name: str
    email: str
    phone: Optional[str] = ""
    role: str = "staff"
    branch: str = "Anna Nagar Branch"
    department: str = "Sales Team"
    reporting_manager: Optional[str] = ""
    employee_id: Optional[str] = ""
    joining_date: Optional[str] = ""
    team: Optional[str] = "Sales Team"
    status: str = "Active"
    password: Optional[str] = "password@123"


@router.get("/users/directory")
async def get_users_directory(current_user: User = Depends(get_current_user)):
    """Fetch complete list of workspace user profiles with extended attributes."""
    conn = db_manager.get_connection()
    try:
        rows = conn.execute("""
            SELECT id, username, email, COALESCE(full_name, username) as full_name, COALESCE(phone, '') as phone, role, COALESCE(department, 'Sales Team') as department, COALESCE(branch, 'Anna Nagar Branch') as branch, COALESCE(team, 'Sales Team') as team, COALESCE(status, 'Active') as status, COALESCE(reporting_manager, '') as reporting_manager, COALESCE(employee_id, '') as employee_id, COALESCE(joining_date, '') as joining_date
            FROM users
            ORDER BY created_at DESC
        """).fetchall()

        result = []
        for r in rows:
            result.append({
                "id": str(r[0]),
                "username": str(r[1]),
                "email": str(r[2]),
                "full_name": str(r[3]),
                "phone": str(r[4]),
                "role": str(r[5]),
                "department": str(r[6]),
                "branch": str(r[7]),
                "team": str(r[8]),
                "status": str(r[9]),
                "reporting_manager": str(r[10]),
                "employee_id": str(r[11]),
                "joining_date": str(r[12])
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/save")
async def save_user(payload: UserSavePayload, current_user: User = Depends(get_current_user)):
    """Create or update user profile details."""
    conn = db_manager.get_connection()
    audit = AuditService()
    try:
        from app.infrastructure.security import hash_password
        from datetime import datetime
        from uuid import uuid4

        user_id = payload.id or str(uuid4())
        username = payload.username or payload.email.split('@')[0]
        hashed_pwd = hash_password(payload.password or "password@123")
        now = datetime.utcnow()

        conn.execute("""
            INSERT INTO users (id, username, email, hashed_password, role, full_name, phone, branch, department, team, status, reporting_manager, employee_id, joining_date, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, True, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                username = EXCLUDED.username,
                email = EXCLUDED.email,
                role = EXCLUDED.role,
                full_name = EXCLUDED.full_name,
                phone = EXCLUDED.phone,
                branch = EXCLUDED.branch,
                department = EXCLUDED.department,
                team = EXCLUDED.team,
                status = EXCLUDED.status,
                reporting_manager = EXCLUDED.reporting_manager,
                employee_id = EXCLUDED.employee_id,
                joining_date = EXCLUDED.joining_date,
                updated_at = EXCLUDED.updated_at;
        """, [user_id, username, payload.email, hashed_pwd, payload.role, payload.full_name, payload.phone, payload.branch, payload.department, payload.team, payload.status, payload.reporting_manager, payload.employee_id, payload.joining_date, now, now])

        conn.execute("INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)", [user_id, payload.role])

        audit.log_action(
            user_id=str(current_user.id),
            action="SAVE_USER_PROFILE",
            resource_type="user",
            details={"target_user": username, "role": payload.role, "result": "SUCCESS"}
        )
        return {"status": "success", "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: User = Depends(get_current_user)):
    """Delete a user account profile."""
    conn = db_manager.get_connection()
    try:
        conn.execute("DELETE FROM users WHERE id = ?", [user_id])
        conn.execute("DELETE FROM user_roles WHERE user_id = ?", [user_id])
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/import-erp")
async def import_users_from_erp(current_user: User = Depends(get_current_user)):
    """Automated sync: pull employee and user records from connected ERP tables in DuckDB."""
    conn = db_manager.get_connection()
    audit = AuditService()
    try:
        from app.infrastructure.security import hash_password
        from datetime import datetime
        from uuid import uuid4

        imported_count = 0
        now = datetime.utcnow()

        # Query existing ERP tables in DuckDB
        tables_res = conn.execute("SHOW TABLES").fetchall()
        existing_tables = [t[0].lower() for t in tables_res]

        erp_records = []
        for tbl in existing_tables:
            if any(k in tbl for k in ['employee', 'staff', 'user_import', 'erp_users']):
                try:
                    rows = conn.execute(f"SELECT * FROM {tbl}").fetchall()
                    for r in rows:
                        erp_records.append(r)
                except Exception:
                    pass

        if not erp_records:
            return {"status": "info", "imported_count": 0, "message": "No active ERP employee tables found in DuckDB. Connect an ERP source or import an Excel spreadsheet to sync users."}

        for rec in erp_records:
            fname = str(rec[0]) if len(rec) > 0 else "ERP User"
            email = str(rec[1]) if len(rec) > 1 and "@" in str(rec[1]) else f"{fname.lower().replace(' ', '.')}@erp.local"
            phone = str(rec[2]) if len(rec) > 2 else ""
            rrole = str(rec[3]).lower() if len(rec) > 3 else "staff"
            branch = str(rec[4]) if len(rec) > 4 else "Anna Nagar Branch"
            dept = str(rec[5]) if len(rec) > 5 else "Sales Team"

            uname = email.split('@')[0]
            uid = str(uuid4())
            hpwd = hash_password("password@123")

            conn.execute("""
                INSERT INTO users (id, username, email, hashed_password, role, full_name, phone, branch, department, team, status, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Sales Team', 'Active', True, ?, ?)
                ON CONFLICT (email) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    phone = EXCLUDED.phone,
                    role = EXCLUDED.role,
                    branch = EXCLUDED.branch,
                    department = EXCLUDED.department;
            """, [uid, uname, email, hpwd, rrole, fname, phone, branch, dept, now, now])
            imported_count += 1

        audit.log_action(
            user_id=str(current_user.id),
            action="IMPORT_USERS_FROM_ERP",
            resource_type="users",
            details={"imported_count": imported_count, "result": "SUCCESS"}
        )
        return {"status": "success", "imported_count": imported_count, "message": f"Successfully synced {imported_count} employee profiles from connected ERP tables in DuckDB."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/clean-test-users")
async def clean_test_users(current_user: User = Depends(get_current_user)):
    """Clean test user accounts (e.g. admin_user, manager_user, staff_user) from DuckDB users table."""
    conn = db_manager.get_connection()
    try:
        conn.execute("DELETE FROM users WHERE username IN ('admin_user', 'manager_user', 'staff_user', 'test_user') OR email LIKE '%@test.com'")
        return {"status": "success", "message": "Cleaned test user records from DuckDB database."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/import-excel")
async def import_users_excel(payload: List[UserSavePayload], current_user: User = Depends(get_current_user)):
    """Batch import user rows from spreadsheet JSON data."""
    conn = db_manager.get_connection()
    try:
        from app.infrastructure.security import hash_password
        from datetime import datetime
        from uuid import uuid4

        imported = 0
        now = datetime.utcnow()
        for u in payload:
            uid = str(uuid4())
            uname = u.username or u.email.split('@')[0]
            hpwd = hash_password(u.password or "password@123")
            conn.execute("""
                INSERT INTO users (id, username, email, hashed_password, role, full_name, phone, branch, department, team, status, reporting_manager, employee_id, joining_date, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, True, ?, ?)
                ON CONFLICT (email) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    phone = EXCLUDED.phone,
                    role = EXCLUDED.role,
                    branch = EXCLUDED.branch,
                    department = EXCLUDED.department,
                    team = EXCLUDED.team,
                    status = EXCLUDED.status,
                    reporting_manager = EXCLUDED.reporting_manager,
                    employee_id = EXCLUDED.employee_id,
                    joining_date = EXCLUDED.joining_date;
            """, [uid, uname, u.email, hpwd, u.role, u.full_name, u.phone, u.branch, u.department, u.team, u.status, u.reporting_manager, u.employee_id, u.joining_date, now, now])
            imported += 1

        return {"status": "success", "imported_count": imported}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class BranchSavePayload(BaseModel):
    id: Optional[str] = None
    code: str
    name: str
    location: str
    manager_name: Optional[str] = "Unassigned"
    phone: Optional[str] = ""
    operating_hours: Optional[str] = "09:00 AM - 06:00 PM"
    status: str = "Active"
    description: Optional[str] = ""


@router.get("/branches")
async def get_branches_catalog(current_user: User = Depends(get_current_user)):
    """Fetch complete list of operational branches and summary metrics from DuckDB."""
    conn = db_manager.get_connection()
    try:
        rows = conn.execute("""
            SELECT id, code, name, COALESCE(location, ''), COALESCE(manager_name, 'Unassigned'), COALESCE(phone, ''), COALESCE(operating_hours, '09:00 AM - 06:00 PM'), COALESCE(status, 'Active'), COALESCE(description, '')
            FROM branches
            ORDER BY created_at DESC
        """).fetchall()

        branches = []
        unique_managers = set()
        active_count = 0

        for r in rows:
            mgr = str(r[4])
            stat = str(r[7])
            if mgr and mgr != "Unassigned":
                unique_managers.add(mgr)
            if stat == "Active":
                active_count += 1

            branches.append({
                "id": str(r[0]),
                "code": str(r[1]),
                "name": str(r[2]),
                "location": str(r[3]),
                "manager_name": mgr,
                "phone": str(r[5]),
                "operating_hours": str(r[6]),
                "status": stat,
                "description": str(r[8])
            })

        return {
            "metrics": {
                "total_branches": len(branches),
                "total_managers": len(unique_managers),
                "active_branches": active_count
            },
            "branches": branches
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/branches/save")
async def save_branch(payload: BranchSavePayload, current_user: User = Depends(get_current_user)):
    """Create or update operational branch details."""
    conn = db_manager.get_connection()
    audit = AuditService()
    try:
        from datetime import datetime
        from uuid import uuid4

        branch_id = payload.id or str(uuid4())
        now = datetime.utcnow()

        conn.execute("""
            INSERT INTO branches (id, code, name, location, manager_name, phone, operating_hours, status, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                code = EXCLUDED.code,
                name = EXCLUDED.name,
                location = EXCLUDED.location,
                manager_name = EXCLUDED.manager_name,
                phone = EXCLUDED.phone,
                operating_hours = EXCLUDED.operating_hours,
                status = EXCLUDED.status,
                description = EXCLUDED.description;
        """, [branch_id, payload.code, payload.name, payload.location, payload.manager_name, payload.phone, payload.operating_hours, payload.status, payload.description, now])

        audit.log_action(
            user_id=str(current_user.id),
            action="SAVE_BRANCH",
            resource_type="branch",
            details={"branch_code": payload.code, "branch_name": payload.name, "result": "SUCCESS"}
        )
        return {"status": "success", "branch_id": branch_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/branches/{branch_id}")
async def delete_branch(branch_id: str, current_user: User = Depends(get_current_user)):
    """Delete a branch record."""
    conn = db_manager.get_connection()
    try:
        conn.execute("DELETE FROM branches WHERE id = ?", [branch_id])
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/branches/import")
async def import_branches(payload: List[BranchSavePayload], current_user: User = Depends(get_current_user)):
    """Batch import branch rows from spreadsheet data."""
    conn = db_manager.get_connection()
    try:
        from datetime import datetime
        from uuid import uuid4

        imported = 0
        now = datetime.utcnow()
        for b in payload:
            bid = b.id or str(uuid4())
            conn.execute("""
                INSERT INTO branches (id, code, name, location, manager_name, phone, operating_hours, status, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    location = EXCLUDED.location,
                    manager_name = EXCLUDED.manager_name,
                    phone = EXCLUDED.phone,
                    operating_hours = EXCLUDED.operating_hours,
                    status = EXCLUDED.status;
            """, [bid, b.code, b.name, b.location, b.manager_name, b.phone, b.operating_hours, b.status, b.description or "", now])
            imported += 1

        return {"status": "success", "imported_count": imported}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class DepartmentSavePayload(BaseModel):
    id: Optional[str] = None
    code: str
    name: str
    branch: Optional[str] = "Anna Nagar Branch"
    manager_name: Optional[str] = "Unassigned"
    description: Optional[str] = ""
    status: str = "Active"


@router.get("/departments")
async def get_departments_catalog(current_user: User = Depends(get_current_user)):
    """Fetch complete list of departments with calculated live member counts from DuckDB."""
    conn = db_manager.get_connection()
    try:
        # Calculate live member counts per department from users table
        member_counts = {}
        try:
            counts_res = conn.execute("SELECT department, COUNT(*) FROM users WHERE department IS NOT NULL GROUP BY department").fetchall()
            for dept, count in counts_res:
                if dept:
                    member_counts[dept.strip().lower()] = count
        except Exception:
            pass

        rows = conn.execute("""
            SELECT id, code, name, COALESCE(branch, 'Anna Nagar Branch'), COALESCE(manager_name, 'Unassigned'), COALESCE(description, ''), COALESCE(status, 'Active')
            FROM departments
            ORDER BY created_at DESC
        """).fetchall()

        departments = []
        for r in rows:
            dept_name = str(r[2])
            # Live member count calculation
            mem_count = member_counts.get(dept_name.strip().lower(), 0)

            departments.append({
                "id": str(r[0]),
                "code": str(r[1]),
                "name": dept_name,
                "branch": str(r[3]),
                "manager_name": str(r[4]),
                "description": str(r[5]),
                "department_members": mem_count,
                "status": str(r[6])
            })

        return departments
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/departments/save")
async def save_department(payload: DepartmentSavePayload, current_user: User = Depends(get_current_user)):
    """Create or update department profile."""
    conn = db_manager.get_connection()
    audit = AuditService()
    try:
        from datetime import datetime
        from uuid import uuid4

        dept_id = payload.id or str(uuid4())
        now = datetime.utcnow()

        conn.execute("""
            INSERT INTO departments (id, code, name, branch, manager_name, description, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                code = EXCLUDED.code,
                name = EXCLUDED.name,
                branch = EXCLUDED.branch,
                manager_name = EXCLUDED.manager_name,
                description = EXCLUDED.description,
                status = EXCLUDED.status;
        """, [dept_id, payload.code, payload.name, payload.branch, payload.manager_name, payload.description, payload.status, now])

        audit.log_action(
            user_id=str(current_user.id),
            action="SAVE_DEPARTMENT",
            resource_type="department",
            details={"dept_code": payload.code, "dept_name": payload.name, "result": "SUCCESS"}
        )
        return {"status": "success", "department_id": dept_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/departments/{department_id}")
async def delete_department(department_id: str, current_user: User = Depends(get_current_user)):
    """Delete a department record."""
    conn = db_manager.get_connection()
    try:
        conn.execute("DELETE FROM departments WHERE id = ?", [department_id])
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/departments/import")
async def import_departments(payload: List[DepartmentSavePayload], current_user: User = Depends(get_current_user)):
    """Batch import department rows from spreadsheet data."""
    conn = db_manager.get_connection()
    try:
        from datetime import datetime
        from uuid import uuid4

        imported = 0
        now = datetime.utcnow()
        for d in payload:
            did = d.id or str(uuid4())
            conn.execute("""
                INSERT INTO departments (id, code, name, branch, manager_name, description, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    branch = EXCLUDED.branch,
                    manager_name = EXCLUDED.manager_name,
                    description = EXCLUDED.description,
                    status = EXCLUDED.status;
            """, [did, d.code, d.name, d.branch, d.manager_name, d.description or "", d.status, now])
            imported += 1

        return {"status": "success", "imported_count": imported}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))






# Legacy Upgrade compatibility
upgrade_router = APIRouter(prefix="/upgrade", tags=["upgrade-gating"])

@upgrade_router.post("/license")
async def upgrade_license_compat(payload: LicenseUploadPayload, current_user: User = Depends(PermissionChecker("license.manage"))):
    """Legacy compatibility endpoint pointing to the validation-before-replacement upload pipeline."""
    return await upload_license(payload, current_user)

"""
CLARIUS Backend - Centralized Authorization Service
"""

from uuid import UUID
from typing import Set, Dict, Any, Optional, List
import logging
from app.infrastructure.database import db_manager

logger = logging.getLogger("clarius.authorization")

class AuthorizationService:
    """Central gateway for security permission checks, role hierarchy, and scopes."""

    def __init__(self):
        self.db_manager = db_manager

    def get_user_roles(self, user_id: UUID) -> Set[str]:
        """Get all roles directly assigned to a user."""
        conn = self.db_manager.get_connection()
        rows = conn.execute(
            "SELECT role_id FROM user_roles WHERE user_id = ?",
            [str(user_id)]
        ).fetchall()
        return {r[0] for r in rows}

    def get_inherited_permissions(self, role_id: str, visited: Optional[Set[str]] = None) -> Set[str]:
        """Recursively retrieve direct and inherited permissions for a role."""
        if visited is None:
            visited = set()
        if role_id in visited:
            return set()
        visited.add(role_id)

        conn = self.db_manager.get_connection()
        # Direct permissions for this role
        rows = conn.execute(
            "SELECT permission_id FROM role_permissions WHERE role_id = ?",
            [role_id]
        ).fetchall()
        perms = {r[0] for r in rows}

        # Parent permissions (A child inherits permissions from its parent role)
        parent_rows = conn.execute(
            "SELECT parent_role_id FROM role_hierarchy WHERE child_role_id = ?",
            [role_id]
        ).fetchall()

        for p_row in parent_rows:
            parent_id = p_row[0]
            perms.update(self.get_inherited_permissions(parent_id, visited))

        return perms

    def get_effective_permissions(self, user_id: UUID) -> Set[str]:
        """Resolve all effective permissions for a user across all assigned roles."""
        roles = self.get_user_roles(user_id)
        effective_perms = set()
        for role in roles:
            effective_perms.update(self.get_inherited_permissions(role))
        return effective_perms

    def check_scope(self, user_id: UUID, permission: str, resource: Optional[str] = None, context: Optional[dict] = None) -> bool:
        """Verify if the user's access scopes allow access to the resource/context."""
        roles = self.get_user_roles(user_id)
        # Owner and Admin bypass scope checks
        if "owner" in roles or "admin" in roles:
            return True

        if not context:
            return True

        conn = self.db_manager.get_connection()
        # Retrieve all user access scopes
        rows = conn.execute(
            """
            SELECT s.scope_type, s.scope_value 
            FROM user_access_scopes uas
            JOIN access_scopes s ON uas.scope_id = s.id
            WHERE uas.user_id = ?
            """,
            [str(user_id)]
        ).fetchall()

        if not rows:
            # If no scopes are assigned, default to allow unless specific context restriction requires it
            return True

        user_scopes = {}
        for scope_type, scope_value in rows:
            if scope_type not in user_scopes:
                user_scopes[scope_type] = set()
            user_scopes[scope_type].add(scope_value)

        # Check branch constraint
        if "branch" in context and "branch" in user_scopes:
            if context["branch"] not in user_scopes["branch"]:
                return False

        return True

    def authorize(self, user_id: UUID, permission: str, resource: Optional[str] = None, context: Optional[dict] = None) -> bool:
        """Central gateway method coordinating checks."""
        # 1. Resolve role-based permissions
        effective_perms = self.get_effective_permissions(user_id)
        
        # Superuser/Owner bypass or exact permission match
        if "all" in effective_perms or permission in effective_perms:
            # 2. Check resource-level scopes
            return self.check_scope(user_id, permission, resource, context)
            
        return False

    def would_create_cycle(self, parent_role_id: str, child_role_id: str) -> bool:
        """Check if adding hierarchy parent -> child would introduce a cycle."""
        if parent_role_id == child_role_id:
            return True

        conn = self.db_manager.get_connection()
        visited = set()
        # Traverse downwards starting from child_role_id.
        # If we can reach parent_role_id, it is a cycle.
        to_visit = [child_role_id]
        while to_visit:
            curr = to_visit.pop(0)
            if curr == parent_role_id:
                return True
            if curr in visited:
                continue
            visited.add(curr)

            rows = conn.execute(
                "SELECT child_role_id FROM role_hierarchy WHERE parent_role_id = ?",
                [curr]
            ).fetchall()
            for r in rows:
                to_visit.append(r[0])
        return False

    def add_role_hierarchy(self, parent_role_id: str, child_role_id: str) -> bool:
        """Add relationship to role_hierarchy table after cycle validation."""
        if self.would_create_cycle(parent_role_id, child_role_id):
            raise ValueError(f"Cannot add hierarchy: cycle detected between {parent_role_id} and {child_role_id}")
        
        conn = self.db_manager.get_connection()
        conn.execute(
            "INSERT OR IGNORE INTO role_hierarchy (parent_role_id, child_role_id) VALUES (?, ?)",
            [parent_role_id, child_role_id]
        )
        return True


# Global singleton instance
authorization_service = AuthorizationService()

"""
CLARIUS Backend - Enterprise RBAC, Security, and Licensing Test Suite
"""

import sys
import os
import json
import base64
import unittest
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import ed25519

# Add app to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.main import app
from app.api.authorization_service import authorization_service
from app.infrastructure.database import db_manager
from app.domain.entities import User, UserRole
from app.infrastructure.security import create_access_token
from app.infrastructure.licensing import LicenseStatus, CapabilityService

# Test private key hex (matching public key hex in licensing.py)
PRIVATE_KEY_HEX = "5c8f8ab692e2a8684617a233b664d509f6b9868e2f0727dc00966a935fa7c062"


class TestEnterpriseSecurity(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.db = db_manager.get_connection()
        
        # Initialize schema first to ensure tables exist
        db_manager.initialize_schema()
        
        # Clear users & RBAC tables for isolation
        self.db.execute("DELETE FROM users;")
        self.db.execute("DELETE FROM user_roles;")
        self.db.execute("DELETE FROM user_access_scopes;")
        self.db.execute("DELETE FROM access_scopes;")
        
        # Setup cryptography key
        self.private_key = ed25519.Ed25519PrivateKey.from_private_bytes(
            bytes.fromhex(PRIVATE_KEY_HEX)
        )

        # Create test users
        self.admin_id = uuid4()
        self.manager_id = uuid4()
        self.staff_id = uuid4()

        # Insert users
        now = datetime.utcnow()
        self.db.execute(
            "INSERT INTO users (id, username, email, hashed_password, role, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [str(self.admin_id), "admin_user", "admin@test.com", "hash", "admin", True, now, now]
        )
        self.db.execute(
            "INSERT INTO users (id, username, email, hashed_password, role, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [str(self.manager_id), "manager_user", "manager@test.com", "hash", "manager", True, now, now]
        )
        self.db.execute(
            "INSERT INTO users (id, username, email, hashed_password, role, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [str(self.staff_id), "staff_user", "staff@test.com", "hash", "staff", True, now, now]
        )

        # Map new user roles
        self.db.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", [str(self.admin_id), "admin"])
        self.db.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", [str(self.manager_id), "manager"])
        self.db.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", [str(self.staff_id), "staff"])

        # Tokens
        self.admin_token = create_access_token(self.admin_id, "admin")
        self.manager_token = create_access_token(self.manager_id, "manager")
        self.staff_token = create_access_token(self.staff_id, "staff")

    def _create_signed_license(self, payload: dict) -> str:
        """Helper to serialize, encode, and sign a license file payload."""
        payload_json = json.dumps(payload)
        payload_b64 = base64.urlsafe_b64encode(payload_json.encode('utf-8')).decode('utf-8').rstrip("=")
        signature = self.private_key.sign(payload_json.encode('utf-8'))
        sig_b64 = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip("=")
        return f"CLARIUS-LICENSE-v1\n{payload_b64}\n{sig_b64}"

    def test_role_hierarchy_permissions(self):
        """Confirm child roles inherit parent permissions. Prevent circular validation."""
        # Clean default hierarchy first
        self.db.execute("DELETE FROM role_hierarchy;")
        
        # admin is parent of manager, manager is parent of staff
        authorization_service.add_role_hierarchy("admin", "manager")
        authorization_service.add_role_hierarchy("manager", "staff")

        # Map a permission to admin
        self.db.execute("INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)", ["admin", "system.settings.update"])

        # Check effective permissions
        admin_perms = authorization_service.get_effective_permissions(self.admin_id)
        manager_perms = authorization_service.get_effective_permissions(self.manager_id)
        staff_perms = authorization_service.get_effective_permissions(self.staff_id)

        # Manager inherits from Admin, so Manager should have system.settings.update
        self.assertIn("system.settings.update", admin_perms)
        self.assertIn("system.settings.update", manager_perms)
        # Staff inherits from Manager, so Staff should also have it
        self.assertIn("system.settings.update", staff_perms)

        # Test circular inheritance prevention
        with self.assertRaises(ValueError):
            # Attempting to make staff a parent of admin (staff -> admin)
            # Since admin is parent of manager -> parent of staff, this is circular.
            authorization_service.add_role_hierarchy("staff", "admin")

    def test_scope_aware_access(self):
        """Verify Manager A (Chennai) is allowed access to Chennai sales but denied Bangalore sales."""
        # Map Chennai scope to manager_user
        scope_id = "branch_Chennai"
        self.db.execute("INSERT INTO access_scopes (id, scope_type, scope_value) VALUES (?, ?, ?)", [scope_id, "branch", "Chennai"])
        self.db.execute("INSERT INTO user_access_scopes (user_id, scope_id) VALUES (?, ?)", [str(self.manager_id), scope_id])

        # Test Chennai context (Allow)
        self.assertTrue(
            authorization_service.authorize(self.manager_id, "sales.read", context={"branch": "Chennai"})
        )

        # Test Bangalore context (Deny)
        self.assertFalse(
            authorization_service.authorize(self.manager_id, "sales.read", context={"branch": "Bangalore"})
        )

        # Test Admin user bypass (Allow always)
        self.assertTrue(
            authorization_service.authorize(self.admin_id, "sales.read", context={"branch": "Bangalore"})
        )

    def test_direct_api_bypass(self):
        """Confirm backend rejects direct requests targeting protected routes without valid permission."""
        # Clear role hierarchy so staff does not inherit admin permissions
        self.db.execute("DELETE FROM role_hierarchy;")

        headers_staff = {"Authorization": f"Bearer {self.staff_token}"}
        headers_admin = {"Authorization": f"Bearer {self.admin_token}"}

        # Request with staff token (which lacks system.settings.update) should yield 403
        res = self.client.get("/admin/settings", headers=headers_staff)
        self.assertEqual(res.status_code, 403)

        # Request with admin token should yield 200
        res = self.client.get("/admin/settings", headers=headers_admin)
        self.assertEqual(res.status_code, 200)

    def test_license_upload_atomicity(self):
        """Confirm invalid license uploads do not overwrite existing active licenses."""
        # 1. Setup active valid license
        original_lic_path = Path("config/license.lic")
        original_lic_path.parent.mkdir(parents=True, exist_ok=True)
        
        expiry = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        valid_payload = {
            "edition": "univa",
            "expires_at": expiry,
            "organization": {"max_users": 10, "max_branches": 3},
            "deployment": {"fingerprint_strictness": "none"}
        }
        valid_license_str = self._create_signed_license(valid_payload)
        original_lic_path.write_text(valid_license_str, encoding="utf-8")

        # 2. Upload invalid/tampered license
        headers_admin = {"Authorization": f"Bearer {self.admin_token}"}
        invalid_license_str = valid_license_str + "TAMPERED"

        res = self.client.post(
            "/admin/license/upload",
            json={"license_key": invalid_license_str},
            headers=headers_admin
        )
        # Should return 400 Bad Request
        self.assertEqual(res.status_code, 400)

        # 3. Verify original valid license is still intact
        current_content = original_lic_path.read_text(encoding="utf-8")
        self.assertEqual(current_content, valid_license_str)


if __name__ == "__main__":
    unittest.main()

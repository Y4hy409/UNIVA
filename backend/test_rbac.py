"""
CLARIUS Backend - Role-Based Access Control (RBAC) Test Suite

This module runs client-level tests against FastAPI routers, verifying that
unauthenticated requests are blocked, and role privileges are properly gated (P1.2).
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from uuid import uuid4
from datetime import datetime
from fastapi.testclient import TestClient

# Add app to python path
sys.path.insert(0, str(Path(__file__).parent))

from app.main import app
from app.domain.entities import User, UserRole
from app.infrastructure.security import create_access_token


class TestRBAC(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.owner_id = uuid4()
        self.analyst_id = uuid4()
        self.staff_id = uuid4()
        
        # Generate tokens
        self.owner_token = create_access_token(self.owner_id, UserRole.OWNER.value)
        self.analyst_token = create_access_token(self.analyst_id, UserRole.ANALYST.value)
        self.staff_token = create_access_token(self.staff_id, UserRole.STAFF.value)

        # Mock database lookup for current user resolution
        now = datetime.utcnow()
        self.owner_user = User(
            id=self.owner_id,
            username="owner_user",
            email="owner@test.com",
            hashed_password="hashed",
            role=UserRole.OWNER,
            is_active=True,
            created_at=now,
            updated_at=now
        )
        self.analyst_user = User(
            id=self.analyst_id,
            username="analyst_user",
            email="analyst@test.com",
            hashed_password="hashed",
            role=UserRole.ANALYST,
            is_active=True,
            created_at=now,
            updated_at=now
        )
        self.staff_user = User(
            id=self.staff_id,
            username="staff_user",
            email="staff@test.com",
            hashed_password="hashed",
            role=UserRole.STAFF,
            is_active=True,
            created_at=now,
            updated_at=now
        )

    @patch("app.infrastructure.licensing.CapabilityService.has_capability", return_value=True)
    @patch("app.api.dependencies.DuckDBUserRepository.get_by_id")
    def test_unauthenticated_requests_blocked(self, mock_get_user, mock_cap):
        # Request without header should yield 401
        res = self.client.post("/analytics/query", json={"query_text": "SELECT * FROM sales"})
        self.assertEqual(res.status_code, 401)

    @patch("app.infrastructure.licensing.CapabilityService.has_capability", return_value=True)
    @patch("app.ai.agents.core.sql_agent.SQLAgent.process_natural_language_query")
    @patch("app.api.dependencies.DuckDBUserRepository.get_by_id")
    def test_owner_full_access(self, mock_get_user, mock_query, mock_cap):
        mock_get_user.return_value = self.owner_user
        mock_query.return_value = {"success": True, "sql": "SELECT 1", "data": []}
        
        headers = {"Authorization": f"Bearer {self.owner_token}"}
        res = self.client.post("/analytics/query", json={"query_text": "SELECT * FROM sales"}, headers=headers)
        self.assertEqual(res.status_code, 200)

    @patch("app.infrastructure.licensing.CapabilityService.has_capability", return_value=True)
    @patch("app.ai.agents.core.sql_agent.SQLAgent.process_natural_language_query")
    @patch("app.api.dependencies.DuckDBUserRepository.get_by_id")
    def test_analyst_blocked_from_import(self, mock_get_user, mock_query, mock_cap):
        mock_get_user.return_value = self.analyst_user
        
        headers = {"Authorization": f"Bearer {self.analyst_token}"}
        files = {"file": ("data.csv", b"col1,col2\n1,2", "text/csv")}
        res = self.client.post(
            "/data-sources/import",
            files=files,
            data={"target_table": "sales", "mappings": '{"col1": "val1"}'},
            headers=headers
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("Insufficient role permissions", res.json()["detail"])

    @patch("app.infrastructure.licensing.CapabilityService.has_capability", return_value=True)
    @patch("app.api.dependencies.DuckDBUserRepository.get_by_id")
    def test_staff_blocked_from_queries(self, mock_get_user, mock_cap):
        mock_get_user.return_value = self.staff_user
        
        headers = {"Authorization": f"Bearer {self.staff_token}"}
        res = self.client.post("/analytics/query", json={"query_text": "SELECT 1"}, headers=headers)
        self.assertEqual(res.status_code, 403)


if __name__ == '__main__':
    unittest.main()

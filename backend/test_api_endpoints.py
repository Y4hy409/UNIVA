"""
CLARIUS Backend - API Endpoint Integration Test Suite

This module runs mock client tests against live FastAPI routers to ensure
endpoints properly enforce SQL validation, file uploads, and auth boundaries.
"""

import sys
import unittest
from unittest.mock import patch
from pathlib import Path
from uuid import uuid4
from datetime import datetime
from fastapi.testclient import TestClient

# Add app to python path
sys.path.insert(0, str(Path(__file__).parent))

from app.main import app
from app.domain.entities import User, UserRole
from app.api.dependencies import get_current_user


class TestAPIEndpoints(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        # Patch capability service to allow API queries to bypass licensing gate
        self.cap_patcher = patch("app.infrastructure.licensing.CapabilityService.has_capability", return_value=True)
        self.mock_cap = self.cap_patcher.start()

        # Build dummy Owner user context
        now = datetime.utcnow()
        self.dummy_user = User(
            id=uuid4(),
            username="test_owner",
            email="test_owner@test.com",
            hashed_password="hashed",
            role=UserRole.OWNER,
            is_active=True,
            created_at=now,
            updated_at=now
        )
        
        # Override FastAPI dependency injection
        app.dependency_overrides[get_current_user] = lambda: self.dummy_user
        
        # Provide any bearer token header so HTTPBearer parser does not raise 401/403
        self.headers = {"Authorization": "Bearer dummy_token"}

    def tearDown(self):
        self.cap_patcher.stop()
        app.dependency_overrides.clear()

    @patch("app.ai.agents.core.sql_agent.SQLAgent.generate_sql")
    def test_analytics_query_unauthorized_drop(self, mock_gen):
        mock_gen.return_value = "DROP TABLE test_sales"
        
        payload = {"query_text": "DROP TABLE test_sales"}
        response = self.client.post("/analytics/query", json=payload, headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Security violation", data["error"])

    @patch("app.ai.agents.core.sql_agent.SQLAgent.generate_sql")
    def test_analytics_query_unauthorized_table(self, mock_gen):
        mock_gen.return_value = "SELECT * FROM users"
        
        payload = {"query_text": "SELECT * FROM users"}
        response = self.client.post("/analytics/query", json=payload, headers=self.headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Unauthorized access", data["error"])

    def test_documents_upload_unsupported_format(self):
        files = {"file": ("evil.exe", b"malicious payload", "application/octet-stream")}
        response = self.client.post(
            "/documents/upload",
            files=files,
            data={"doc_type": "policy", "title": "Evil"},
            headers=self.headers
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("Unsupported file format", data["detail"])

    def test_documents_upload_path_traversal(self):
        files = {"file": ("../../../../evil.txt", b"safe content", "text/plain")}
        response = self.client.post(
            "/documents/upload",
            files=files,
            data={"doc_type": "policy", "title": "Evil Path"},
            headers=self.headers
        )
        
        self.assertIn(response.status_code, [200, 202])
        data = response.json()
        self.assertTrue("job_id" in data or "id" in data)

    def test_data_sources_import_unsupported_format(self):
        files = {"file": ("data.txt", b"plain data", "text/plain")}
        response = self.client.post(
            "/data-sources/import",
            files=files,
            data={"target_table": "sales", "mappings": '{"col": "val"}'},
            headers=self.headers
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("Unsupported file format", data["detail"])

    def test_data_sources_tables_list(self):
        response = self.client.get("/data-sources/tables", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_documents_query_get(self):
        response = self.client.get("/documents/query?q=policy", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        self.assertIsInstance(data["results"], list)

    def test_documents_list(self):
        response = self.client.get("/documents", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)


if __name__ == '__main__':
    unittest.main()


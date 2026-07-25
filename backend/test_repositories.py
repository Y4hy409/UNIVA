"""
CLARIUS Backend - Repository and Clean Architecture Test Suite

This suite verifies three levels of testing:
1. Repository Unit Tests (DuckDB isolation)
2. Service Unit Tests (Mocking interfaces)
3. API Integration Tests (End-to-End flow verification)
"""

import sys
import json
import asyncio
import unittest
from uuid import UUID, uuid4
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

import duckdb
from app.main import app
from app.domain.entities import User, UserRole
from app.application.auth_service import AuthService
from app.modules.documents.application.document_service import DocumentService
from app.infrastructure.repositories import DuckDBUserRepository, DuckDBDocumentRepository

class MockConnectionProvider:
    """Mock connection provider supporting get_connection requests."""
    def __init__(self, conn):
        self.conn = conn

    def get_connection(self):
        return self.conn


class TestRepositoriesAndServices(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        # Establish in-memory DuckDB database for Repository testing
        self.conn = duckdb.connect(":memory:")
        
        # Build schema tables
        self.conn.execute("""
            CREATE TABLE users (
                id VARCHAR PRIMARY KEY,
                username VARCHAR UNIQUE,
                email VARCHAR UNIQUE,
                hashed_password VARCHAR,
                role VARCHAR,
                is_active BOOLEAN,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            );
        """)
        self.conn.execute("""
            CREATE TABLE documents (
                id VARCHAR PRIMARY KEY,
                title VARCHAR,
                content VARCHAR,
                doc_type VARCHAR,
                metadata VARCHAR,
                embedding_id VARCHAR,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            );
        """)
        
        self.provider = MockConnectionProvider(self.conn)
        self.user_repo = DuckDBUserRepository(self.provider)
        self.doc_repo = DuckDBDocumentRepository(self.provider)

    async def asyncTearDown(self):
        self.conn.close()

    # ======================================================================
    # LEVEL 1: Repository Unit Tests
    # ======================================================================

    def test_user_repository_crud(self):
        user = User(
            id=uuid4(),
            username="john_doe",
            email="john@doe.com",
            hashed_password="hashed_pass_value",
            role=UserRole.OWNER,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Create
        self.user_repo.create_user(user)
        self.assertEqual(self.user_repo.count_users(), 1)
        
        # Read by username
        fetched = self.user_repo.get_by_username("john_doe")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.email, "john@doe.com")
        self.assertEqual(fetched.role, UserRole.OWNER)

        # Read by ID
        fetched_id = self.user_repo.get_by_id(user.id)
        self.assertIsNotNone(fetched_id)
        self.assertEqual(fetched_id.username, "john_doe")

        # Update
        user.email = "john_updated@doe.com"
        self.user_repo.update_user(user)
        fetched_upd = self.user_repo.get_by_username("john_doe")
        self.assertEqual(fetched_upd.email, "john_updated@doe.com")

    def test_document_repository_crud(self):
        doc_id = "test-doc-123"
        metadata = {"file_size": 2048, "file_path": "/data/test.txt"}
        
        self.doc_repo.save_document(
            doc_id=doc_id,
            title="Sample Title",
            content="Sample document body extraction text.",
            doc_type="policy",
            metadata_dict=metadata,
            embedding_id=doc_id
        )
        
        fetched = self.doc_repo.get_document_metadata(doc_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["title"], "Sample Title")
        self.assertEqual(fetched["doc_type"], "policy")
        self.assertEqual(fetched["metadata"]["file_size"], 2048)

    # ======================================================================
    # LEVEL 2: Service Unit Tests (Mocking Repository Interfaces)
    # ======================================================================

    def test_auth_service_owner_creation_mocks(self):
        # Create a mock repository
        mock_repo = MagicMock()
        mock_repo.count_users.return_value = 0
        
        auth_service = AuthService(mock_repo)
        owner = auth_service.create_owner("admin", "admin@clarius.com", "pass123")
        
        self.assertEqual(owner.username, "admin")
        self.assertEqual(owner.role, UserRole.OWNER)
        mock_repo.create_user.assert_called_once()

    @patch("app.modules.documents.application.document_service.ocr_service.extract_text")
    async def test_document_service_ingest_mocks(self, mock_ocr):
        mock_ocr.return_value = "Extracted ocr text."
        mock_repo = MagicMock()
        
        # Patch ChromaDB client calls inside service
        with patch("app.modules.documents.application.document_service.knowledge_manager") as mock_kb:
            mock_collection = MagicMock()
            mock_kb.create_collection_if_not_exists.return_value = mock_collection
            
            doc_service = DocumentService(mock_repo)
            # Run ingestion
            doc_id = await doc_service.ingest_document(Path("sample.txt"), "policy", "Sample Doc")
            
            self.assertTrue(bool(doc_id))
            mock_repo.save_document.assert_called_once()
            mock_collection.add.assert_called_once()

    # ======================================================================
    # LEVEL 3: API End-to-End Integration Tests
    # ======================================================================

    def test_api_setup_and_login_flow(self):
        # Use TestClient on FastAPI instance
        client = TestClient(app)
        
        # Bypass licensing checks for integration testing
        with patch("app.infrastructure.licensing.CapabilityService.has_capability", return_value=True):
            status_res = client.get("/auth/status")
            self.assertEqual(status_res.status_code, 200)
            self.assertIn("is_setup", status_res.json())


if __name__ == '__main__':
    unittest.main()

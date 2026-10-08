import unittest
import json
from uuid import uuid4
from datetime import datetime

from app.infrastructure.database import DatabaseManager
from app.infrastructure.repositories import DuckDBDocumentRepository

class TestDocumentsManagement(unittest.TestCase):
    def setUp(self):
        self.db = DatabaseManager(db_path=":memory:")
        self.db.initialize_schema()
        self.repo = DuckDBDocumentRepository(self.db)

    def test_save_and_count_documents(self):
        self.repo.save_document(
            doc_id=str(uuid4()),
            title="Payment Policy",
            content="Standard payment terms policy document.",
            doc_type="policy",
            metadata_dict={"file_size": 2048},
            embedding_id="embed-1"
        )
        
        conn = self.db.get_connection()
        count = conn.execute("SELECT COUNT(*) FROM documents WHERE doc_type = 'policy'").fetchone()[0]
        self.assertEqual(count, 1)

    def test_purge_duplicate_documents(self):
        conn = self.db.get_connection()
        now = datetime.utcnow()
        
        # Insert 3 duplicate Evil Path entries
        for i in range(3):
            conn.execute(
                "INSERT INTO documents (id, title, content, doc_type, metadata, embedding_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [f"evil-{i}", "Evil Path", "Sample text", "policy", "{}", f"emb-{i}", now, now]
            )
            
        initial_count = conn.execute("SELECT COUNT(*) FROM documents WHERE title = 'Evil Path'").fetchone()[0]
        self.assertEqual(initial_count, 3)

        # Execute purge logic
        conn.execute("""
            DELETE FROM documents 
            WHERE id NOT IN (
                SELECT MAX(id) 
                FROM documents 
                GROUP BY title, doc_type
            );
        """)
        
        after_count = conn.execute("SELECT COUNT(*) FROM documents WHERE title = 'Evil Path'").fetchone()[0]
        self.assertEqual(after_count, 1)

    def test_delete_document_by_id(self):
        doc_id = str(uuid4())
        self.repo.save_document(
            doc_id=doc_id,
            title="Sample SOP",
            content="Standard operating procedure text.",
            doc_type="sop",
            metadata_dict={},
            embedding_id="embed-sop"
        )
        
        conn = self.db.get_connection()
        conn.execute("DELETE FROM documents WHERE id = ?", [doc_id])
        
        res = conn.execute("SELECT id FROM documents WHERE id = ?", [doc_id]).fetchone()
        self.assertIsNone(res)

if __name__ == "__main__":
    unittest.main()

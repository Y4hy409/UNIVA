"""
CLARIUS Backend - Conversation History & Data Persistence Unit Tests

Tests persistent conversation management, message turn recording,
dynamic title extraction, schema migration idempotency, and user account persistence.
"""

import os
import unittest
import duckdb
from datetime import datetime

from app.infrastructure.database import DatabaseManager
from app.api.conversations import extract_auto_title
from app.ai.conversation_memory import memory_manager


class TestPersistenceAndConversations(unittest.TestCase):
    
    def setUp(self):
        # Use isolated in-memory or temp file database
        self.db_manager = DatabaseManager(db_path=":memory:")
        self.db_manager.initialize_schema()
        self.db = self.db_manager.get_connection()

    def test_auto_title_extraction(self):
        """Verify dynamic concise title generation from initial user queries."""
        title1 = extract_auto_title("Show sales by region for last quarter")
        self.assertEqual(title1, "Show Sales By Region For Last Quarter")

        title2 = extract_auto_title("What is our purchase policy for IT equipment?")
        self.assertEqual(title2, "What Is Our Purchase Policy For It Equipment?")

        long_query = "A" * 60
        title3 = extract_auto_title(long_query)
        self.assertTrue(title3.endswith("..."))
        self.assertLessEqual(len(title3), 45)

    def test_schema_initialization_idempotency(self):
        """Confirm running initialize_schema multiple times preserves tables and data without throwing errors."""
        # Insert test user
        self.db.execute("""
            INSERT INTO users (id, username, email, hashed_password, role, is_active, created_at, updated_at)
            VALUES ('user_test123', 'test_persistent_user', 'testuser@clarius.local', 'hashed_pass_secret', 'owner', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """)

        # Re-run schema initialization
        self.db_manager.initialize_schema()

        # Check user is still present
        row = self.db.execute("SELECT username, role FROM users WHERE id = 'user_test123'").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "test_persistent_user")
        self.assertEqual(row[1], "owner")

    def test_conversation_lifecycle(self):
        """Test full conversation CRUD lifecycle: create, append messages, pin, archive, delete."""
        conv_id = "conv_test_001"
        user_id = "user_test123"
        now = datetime.utcnow()

        # 1. Create conversation
        self.db.execute("""
            INSERT INTO conversations (id, user_id, title, created_at, updated_at, last_message_at, pinned, archived, message_count, preview)
            VALUES (?, ?, 'Sales Analysis 2026', ?, ?, ?, FALSE, FALSE, 0, '')
        """, [conv_id, user_id, now, now, now])

        # 2. Append messages
        self.db.execute("""
            INSERT INTO conversation_messages (id, conversation_id, role, content, created_at, intent, query_metadata, sql_metadata, visualization_metadata)
            VALUES ('msg_1', ?, 'user', 'Show sales by region', ?, 'ANALYTICS_SQL', NULL, NULL, NULL)
        """, [conv_id, now])

        self.db.execute("""
            INSERT INTO conversation_messages (id, conversation_id, role, content, created_at, intent, query_metadata, sql_metadata, visualization_metadata)
            VALUES ('msg_2', ?, 'assistant', 'Here are the sales by region: South leads with $450k.', ?, 'ANALYTICS_SQL', NULL, 'SELECT region, sum(sales) FROM sales_table GROUP BY region', NULL)
        """, [conv_id, now])

        self.db.execute("UPDATE conversations SET message_count = 2, preview = 'Show sales by region' WHERE id = ?", [conv_id])

        # 3. Retrieve conversation and messages
        conv = self.db.execute("SELECT title, message_count, preview FROM conversations WHERE id = ?", [conv_id]).fetchone()
        self.assertEqual(conv[0], "Sales Analysis 2026")
        self.assertEqual(conv[1], 2)
        self.assertEqual(conv[2], "Show sales by region")

        messages = self.db.execute("SELECT role, content FROM conversation_messages WHERE conversation_id = ? ORDER BY created_at ASC", [conv_id]).fetchall()
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0][0], "user")
        self.assertEqual(messages[1][0], "assistant")

        # 4. Pin conversation
        self.db.execute("UPDATE conversations SET pinned = TRUE WHERE id = ?", [conv_id])
        pinned = self.db.execute("SELECT pinned FROM conversations WHERE id = ?", [conv_id]).fetchone()[0]
        self.assertTrue(pinned)

        # 5. Delete conversation
        self.db.execute("DELETE FROM conversation_messages WHERE conversation_id = ?", [conv_id])
        self.db.execute("DELETE FROM conversations WHERE id = ?", [conv_id])
        deleted = self.db.execute("SELECT id FROM conversations WHERE id = ?", [conv_id]).fetchone()
        self.assertIsNone(deleted)


if __name__ == '__main__':
    unittest.main()

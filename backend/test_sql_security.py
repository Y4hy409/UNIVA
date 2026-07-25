"""
CLARIUS Backend - SQL Security Test Suite

This module runs comprehensive tests on the SQLSecurityValidator class,
verifying that safe operations are allowed and dangerous queries are rejected.
"""

import sys
import unittest
import duckdb

# Add app to python path
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.infrastructure.sql_validator import SQLSecurityValidator


class MockSchemaHelper:
    """Mock database helper to expose schema tables to validator."""
    def __init__(self, tables):
        self.tables = tables

    def execute(self, query):
        class MockResult:
            def __init__(self, data):
                self.data = data
            def fetchall(self):
                return self.data
        return MockResult([(t,) for t in self.tables])


class TestSQLSecurity(unittest.TestCase):
    
    def setUp(self):
        # We bootstrap a list of approved business tables
        self.approved_tables = ["test_sales", "test_customers", "data_inventory"]
        self.helper = MockSchemaHelper(self.approved_tables)
        self.validator = SQLSecurityValidator(self.helper)

    def test_allowed_queries(self):
        allowed_queries = [
            "SELECT * FROM test_sales",
            "SELECT product_name, SUM(amount) FROM test_sales GROUP BY product_name",
            "SELECT c.name, s.amount FROM test_customers c JOIN test_sales s ON c.id = s.customer_id",
            "WITH recent_sales AS (SELECT * FROM test_sales WHERE amount > 100) SELECT * FROM recent_sales",
            "SELECT amount, ROW_NUMBER() OVER (ORDER BY transaction_date) FROM test_sales",
            "SELECT * FROM (SELECT * FROM test_sales) WHERE amount < 50",
            "SELECT count(*) FROM data_inventory"
        ]
        
        for q in allowed_queries:
            with self.subTest(query=q):
                is_safe, error = self.validator.validate(q)
                self.assertTrue(is_safe, f"Failed to allow safe query: {q}. Error: {error}")

    def test_rejected_mutations_and_ddl(self):
        rejected = [
            "DROP TABLE test_sales",
            "DELETE FROM test_sales WHERE id = 1",
            "UPDATE test_sales SET amount = 0",
            "INSERT INTO test_sales (id, amount) VALUES (1, 100)",
            "ALTER TABLE test_sales ADD COLUMN description VARCHAR",
            "TRUNCATE TABLE test_sales",
            "CREATE TABLE temp_sales (id INTEGER)",
            "REPLACE INTO test_sales SELECT * FROM test_sales",
            "GRANT ALL PRIVILEGES ON test_sales TO public",
            "REVOKE SELECT ON test_sales FROM public"
        ]
        
        for q in rejected:
            with self.subTest(query=q):
                is_safe, error = self.validator.validate(q)
                self.assertFalse(is_safe, f"Failed to block dangerous DDL/DML query: {q}")
                self.assertTrue(bool(error))

    def test_rejected_duckdb_admin_and_files(self):
        rejected = [
            "INSTALL httpfs",
            "LOAD httpfs",
            "COPY test_sales TO 'sales_export.csv'",
            "ATTACH 'other_db.db' AS secondary",
            "DETACH secondary",
            "SELECT * FROM read_csv('data.csv')",
            "SELECT * FROM read_parquet('data.parquet')",
            "SELECT * FROM read_json('data.json')",
            "COPY (SELECT * FROM test_sales) TO 'out.csv' WITH (HEADER 1, DELIMITER ',')"
        ]
        
        for q in rejected:
            with self.subTest(query=q):
                is_safe, error = self.validator.validate(q)
                self.assertFalse(is_safe, f"Failed to block administrative/file query: {q}")
                self.assertTrue(bool(error))

    def test_unauthorized_tables(self):
        rejected = [
            "SELECT * FROM users",
            "SELECT * FROM dashboards",
            "SELECT * FROM audit_logs",
            "SELECT * FROM sqlite_master",
            "SELECT * FROM unapproved_table",
            "SELECT * FROM test_sales JOIN users ON test_sales.user_id = users.id"
        ]
        
        for q in rejected:
            with self.subTest(query=q):
                is_safe, error = self.validator.validate(q)
                self.assertFalse(is_safe, f"Failed to block unauthorized table access: {q}")
                self.assertTrue("unauthorized" in error.lower())

    def test_evasion_bypass_attempts(self):
        rejected = [
            # Semicolon statement chaining
            "SELECT * FROM test_sales; DROP TABLE test_sales",
            "SELECT * FROM test_sales;\nUPDATE test_sales SET amount = 100",
            # Comment obfuscation
            "SELECT/**/from/**/test_sales",
            "SELECT * FROM test_sales -- DROP TABLE test_sales",
            "SELECT * FROM test_sales; --\nDROP TABLE test_sales",
            "WITH evil AS (SELECT * FROM test_sales) SELECT * FROM evil; INSTALL httpfs;"
        ]
        
        for q in rejected:
            with self.subTest(query=q):
                is_safe, error = self.validator.validate(q)
                self.assertFalse(is_safe, f"Failed to block bypass attempt: {q}")


if __name__ == '__main__':
    unittest.main()

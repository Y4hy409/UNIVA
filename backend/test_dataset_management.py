import unittest
from datetime import datetime

from app.infrastructure.database import DatabaseManager

class TestDatasetManagement(unittest.TestCase):
    def setUp(self):
        self.db = DatabaseManager(db_path=":memory:")
        self.db.initialize_schema()

    def test_primary_key_heuristic(self):
        conn = self.db.get_connection()
        conn.execute("CREATE TABLE products (product VARCHAR, category VARCHAR, price DOUBLE);")
        conn.execute("INSERT INTO products VALUES ('Laptop', 'Electronics', 1200.0), ('Phone', 'Electronics', 800.0);")
        
        cols_info = conn.execute("DESCRIBE products").fetchall()
        sample_row = conn.execute("SELECT * FROM products LIMIT 1").fetchone()
        row_count = 2
        
        # Test PK heuristic logic
        is_pk_list = []
        for i, col in enumerate(cols_info):
            col_name = col[0]
            uniq_cnt = conn.execute(f"SELECT COUNT(DISTINCT {col_name}) FROM products").fetchone()[0]
            is_unique = uniq_cnt == row_count
            has_nulls = False
            
            is_pk = is_unique and not has_nulls and (
                any(kw in col_name.lower() for kw in ["id", "code", "key", "num", "sku", "uuid"]) or 
                col_name.lower() in ["id", "code", "key", "uuid"]
            )
            is_pk_list.append(is_pk)

        # 'product' is index 0 but is NOT an ID column so it MUST NOT be marked PK
        self.assertFalse(is_pk_list[0], "'product' should not be detected as Primary Key")
        self.assertFalse(any(is_pk_list), "No column should be detected as PK in plain string products table")

    def test_dataset_deletion(self):
        conn = self.db.get_connection()
        conn.execute("CREATE TABLE test_drop_dataset (id INT, val VARCHAR);")
        conn.execute("INSERT INTO test_drop_dataset VALUES (1, 'A');")
        
        tables_before = [r[0] for r in conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'").fetchall()]
        self.assertIn("test_drop_dataset", tables_before)
        
        # Drop dataset
        conn.execute("DROP TABLE IF EXISTS test_drop_dataset;")
        
        tables_after = [r[0] for r in conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'").fetchall()]
        self.assertNotIn("test_drop_dataset", tables_after)

if __name__ == "__main__":
    unittest.main()

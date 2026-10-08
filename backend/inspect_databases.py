"""
CLARIUS Database Inspector Script
Run this script directly in VS Code / Antigravity terminal:
    python inspect_databases.py
"""

import os
import sys
from pathlib import Path

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title.upper()}")
    print("=" * 70)

def inspect_duckdb(db_path: Path):
    print_header("1. DUCKDB ANALYTICS & BUSINESS DATA STORE")
    print(f"File Path: {db_path.resolve()}")
    if not db_path.exists():
        print("[-] DuckDB file not found.")
        return

    file_size_mb = db_path.stat().st_size / (1024 * 1024)
    print(f"File Size: {file_size_mb:.2f} MB")

    try:
        import duckdb
        # Open in read-only mode so it never conflicts with a running backend server
        conn = duckdb.connect(str(db_path), read_only=True)
        
        # Get all tables
        tables = conn.execute("SHOW TABLES;").fetchall()
        table_names = [t[0] for t in tables]
        print(f"\nTotal Registered Tables: {len(table_names)}")
        print(f"Tables: {', '.join(table_names)}\n")

        for tname in table_names:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {tname};").fetchone()[0]
                cols = conn.execute(f"DESCRIBE {tname};").fetchall()
                col_names = [c[0] for c in cols]
                print(f"  * Table '{tname}': {count} records | Columns ({len(col_names)}): {', '.join(col_names[:6])}{'...' if len(col_names) > 6 else ''}")
                
                # Show sample 2 rows if table has data
                if count > 0:
                    sample = conn.execute(f"SELECT * FROM {tname} LIMIT 2;").fetchdf()
                    print(f"    Sample Data:\n{sample.to_string(index=False, max_cols=5)}\n")
            except Exception as te:
                print(f"    [!] Error reading table {tname}: {te}")

        conn.close()
    except Exception as e:
        print(f"[-] DuckDB inspection error: {e}")

def inspect_chromadb(chroma_path: Path):
    print_header("2. CHROMADB VECTOR EMBEDDINGS STORE")
    print(f"Directory: {chroma_path.resolve()}")
    if not chroma_path.exists():
        print("[-] ChromaDB directory not found.")
        return

    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(chroma_path))
        collections = client.list_collections()
        print(f"Total Vector Collections: {len(collections)}\n")

        for col in collections:
            count = col.count()
            print(f"  * Collection '{col.name}': {count} vector embeddings")
            if count > 0:
                sample = col.peek(limit=2)
                docs = sample.get('documents', [])
                metas = sample.get('metadatas', [])
                for i, doc in enumerate(docs):
                    meta_str = str(metas[i]) if i < len(metas) else "{}"
                    doc_snippet = (doc[:100] + '...') if len(doc) > 100 else doc
                    print(f"    Chunk #{i+1}: {doc_snippet}")
                    print(f"    Metadata: {meta_str}\n")
    except Exception as e:
        print(f"[-] ChromaDB inspection error: {e}")

if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data"

    duckdb_file = data_dir / "clarius.db"
    chromadb_dir = data_dir / "chromadb"

    print("\n" + "#" * 70)
    print("      CLARIUS LOCAL DATABASE & VECTOR STORE INSPECTOR")
    print("#" * 70)

    inspect_duckdb(duckdb_file)
    inspect_chromadb(chromadb_dir)
    print("=" * 70 + "\n")

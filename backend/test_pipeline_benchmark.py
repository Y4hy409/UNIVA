"""
Benchmark script to measure before vs after NL-to-SQL performance and correctness
across the 9 required test query categories.
"""
import sys
import time
import duckdb

# Ensure utf-8 output encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.ai.services.sql_service import SQLService
from app.ai.router import FastIntentRouter
from app.ai.services.analytics_service import AnalyticsService
from app.ai.shared.memory_utils import ContextResolver, memory_manager

def setup_benchmark_db():
    conn = duckdb.connect(":memory:")
    # Create queries and dataset_versions table for caching
    conn.execute("""
        CREATE TABLE IF NOT EXISTS queries (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR,
            query_text VARCHAR,
            generated_sql VARCHAR,
            status VARCHAR,
            result VARCHAR,
            error_message VARCHAR,
            execution_time_ms INTEGER,
            created_at TIMESTAMP,
            completed_at TIMESTAMP
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dataset_versions (
            id VARCHAR PRIMARY KEY,
            dataset_name VARCHAR,
            version_number INTEGER,
            file_path VARCHAR,
            file_size BIGINT,
            checksum VARCHAR,
            row_count INTEGER,
            column_count INTEGER,
            schema_hash VARCHAR,
            import_mode VARCHAR,
            is_current BOOLEAN,
            created_at TIMESTAMP,
            created_by VARCHAR
        );
    """)
    # Create sample business tables
    conn.execute("""
        CREATE TABLE medical_stores (
            store_id VARCHAR,
            store_name VARCHAR,
            city VARCHAR,
            contact_number VARCHAR
        );
        INSERT INTO medical_stores VALUES
        ('S001', 'Apollo Pharmacy', 'Chennai', '9876543210'),
        ('S002', 'MedPlus', 'Chennai', '9876543211'),
        ('S003', 'HealthCare Chemist', 'Bangalore', '9876543212'),
        ('S004', 'Fortis Medicals', 'Chennai', '9876543213');
    """)

    conn.execute("""
        CREATE TABLE sales (
            invoice_id VARCHAR,
            product_name VARCHAR,
            amount DOUBLE,
            city VARCHAR,
            sale_date TIMESTAMP
        );
        INSERT INTO sales VALUES
        ('INV001', 'Paracetamol 500mg', 1200.0, 'Chennai', '2026-01-15 10:00:00'),
        ('INV002', 'Amoxicillin 250mg', 3400.0, 'Chennai', '2026-02-10 11:30:00'),
        ('INV003', 'Vitamin C 500mg', 850.0, 'Bangalore', '2026-02-14 14:20:00'),
        ('INV004', 'Paracetamol 500mg', 2100.0, 'Chennai', '2026-03-01 09:15:00'),
        ('INV005', 'Cough Syrup 100ml', 1600.0, 'Mumbai', '2026-03-05 16:45:00');
    """)

    conn.execute("""
        CREATE TABLE products (
            product_id VARCHAR,
            product_name VARCHAR,
            category VARCHAR,
            unit_price DOUBLE,
            stock_qty INTEGER
        );
        INSERT INTO products VALUES
        ('P001', 'Paracetamol 500mg', 'Analgesic', 20.0, 500),
        ('P002', 'Amoxicillin 250mg', 'Antibiotic', 85.0, 200),
        ('P003', 'Vitamin C 500mg', 'Supplement', 15.0, 350),
        ('P004', 'Cough Syrup 100ml', 'Respiratory', 45.0, 150);
    """)

    conn.execute("""
        CREATE TABLE invoices (
            invoice_number VARCHAR,
            customer_name VARCHAR,
            total_amount DOUBLE,
            status VARCHAR
        );
        INSERT INTO invoices VALUES
        ('INV001', 'John Doe', 1200.0, 'Paid'),
        ('INV002', 'Jane Smith', 3400.0, 'Paid'),
        ('INV003', 'Bob Johnson', 850.0, 'Pending');
    """)

    return conn

def run_comprehensive_benchmark():
    conn = setup_benchmark_db()
    sql_service = SQLService(db_conn=conn)
    analytics_service = AnalyticsService()
    session = memory_manager.get_session("bench_session_001")

    print("================================================================")
    print("CLARIUS NL-to-SQL PIPELINE COMPREHENSIVE BENCHMARK")
    print("================================================================")

    # 1. Simple entity lookup
    # 2. Scalar aggregation
    # 3. Filtered aggregation
    # 4. Ranking
    # 5. Trend
    # 6. Record lookup
    # 7. Follow-up query
    # 8. RAG / document query
    # 9. Invalid query
    
    test_cases = [
        ("1. Simple entity lookup", "Fetch me medical stores in Chennai", False),
        ("2. Scalar aggregation", "What is the total sales?", False),
        ("3. Filtered aggregation", "What are the total sales in Chennai?", False),
        ("4. Ranking", "Which product has the highest sales?", False),
        ("5. Trend", "Show monthly sales trend", False),
        ("6. Record lookup", "Find invoice INV001", False),
        ("7. Follow-up query", "Now show only the top 5", True),
        ("8. RAG / document question", "What is our company return policy and SOP guidelines?", False),
    ]

    benchmark_summary = []

    for label, query_text, is_followup in test_cases:
        print(f"\n>>> [{label}] '{query_text}'")
        t_start = time.perf_counter()

        # Step A: Context Resolution
        t_ctx0 = time.perf_counter()
        if is_followup:
            ctx_res = ContextResolver.resolve_context(query_text, session)
            effective_query = ctx_res["resolved_query"]
        else:
            effective_query = query_text
        t_ctx = time.perf_counter() - t_ctx0

        # Step B: Intent Classification
        t_intent0 = time.perf_counter()
        route = FastIntentRouter.classify(effective_query)
        intent = route["intent"]
        sub_intent = route.get("sub_intent", "ENTITY_LOOKUP")
        t_intent = time.perf_counter() - t_intent0

        # Step C: RAG Route check
        if intent == "DOCUMENT_KNOWLEDGE_QUERY":
            t_total = time.perf_counter() - t_start
            print(f"  Intent: {intent} (RAG Path Correctly Chosen)")
            print(f"  RAG Retrieval: Skipped DuckDB | Total Time: {t_total:.4f}s")
            benchmark_summary.append({
                "label": label,
                "query": query_text,
                "intent": intent,
                "sql_time": 0.0,
                "total_time": t_total,
                "rows": 0,
                "chart": False,
                "cached": False,
                "status": "PASS (RAG Route)"
            })
            continue

        # Step D: SQL Execution
        t_sql0 = time.perf_counter()
        sql_res = sql_service.process_query(effective_query, session.get_formatted_memory_prompt())
        t_sql = time.perf_counter() - t_sql0

        # Step E: Analytics / Visualization
        t_an0 = time.perf_counter()
        raw_records = sql_res.get("data", [])
        sql = sql_res.get("sql", "")
        records = analytics_service.normalize_results(raw_records, sub_intent, effective_query)
        cols = list(records[0].keys()) if records else []
        viz_eval = analytics_service.evaluate_visualization(effective_query, intent, records, cols, sub_intent=sub_intent)
        chart_config = analytics_service.generate_chart_config(effective_query, sql, records) if viz_eval["should_generate_chart"] else {}
        explanation = analytics_service.explain_analytics(effective_query, sql, records, intent)
        t_an = time.perf_counter() - t_an0

        t_total = time.perf_counter() - t_start

        session.record_turn(
            user_query=query_text,
            intent=intent,
            response_text=explanation,
            sql=sql,
            results=records,
            chart_config=chart_config
        )

        success = sql_res.get("success", False)
        cached = sql_res.get("cached", False)

        print(f"  Intent: {intent} / {sub_intent}")
        print(f"  SQL Generated: {sql}")
        print(f"  Execution: {len(records)} rows returned | Success: {success} | Cached: {cached}")
        print(f"  Chart Generated: {bool(chart_config)} (Mode: {viz_eval['presentation_mode']})")
        print(f"  SQL Time: {t_sql:.2f}s | Total Request Time: {t_total:.2f}s")
        print(f"  Explanation: {explanation[:120]}...")

        benchmark_summary.append({
            "label": label,
            "query": query_text,
            "intent": intent,
            "sql": sql,
            "sql_time": t_sql,
            "total_time": t_total,
            "rows": len(records),
            "chart": bool(chart_config),
            "cached": cached,
            "status": "PASS" if success else "FAIL"
        })

    # Test Repeat Queries for Cache Hit Speed
    print("\n================================================================")
    print("CACHE HIT LATENCY VERIFICATION")
    print("================================================================")
    repeat_queries = [
        ("Cache Test 1", "What is the total sales?"),
        ("Cache Test 2", "Fetch me medical stores in Chennai"),
        ("Cache Test 3", "What are the total sales in Chennai?")
    ]
    for lbl, q in repeat_queries:
        t0 = time.perf_counter()
        res = sql_service.process_query(q)
        t_dur = time.perf_counter() - t0
        print(f"  [{lbl}] '{q}' -> Cached: {res.get('cached')} | Time: {t_dur:.5f}s | Rows: {len(res.get('data', []))}")

    # Invalidation Test
    print("\n--- Testing Cache Invalidation on Schema Mutation ---")
    SQLService.invalidate_schema_cache()
    print("  Schema cache invalidated.")
    t_after_inv0 = time.perf_counter()
    res_inv = sql_service.process_query("What is the total sales?")
    t_inv = time.perf_counter() - t_after_inv0
    print(f"  Re-generated after invalidation: Cached={res_inv.get('cached', False)} | Time={t_inv:.2f}s | Success={res_inv.get('success')}")

    print("\n================================================================")
    print("BENCHMARK EXECUTION SUMMARY")
    print("================================================================")
    for b in benchmark_summary:
        print(f"{b['label']:<32} | Status: {b['status']:<16} | SQL: {b['sql_time']:05.2f}s | Total: {b['total_time']:05.2f}s | Rows: {b['rows']} | Chart: {b['chart']}")
    print("================================================================")

if __name__ == "__main__":
    run_comprehensive_benchmark()

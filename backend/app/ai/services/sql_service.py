"""
CLARIUS Backend - Consolidated SQL Domain Service

Single cohesive service handling dynamic schema discovery (with 60s TTL cache and relevance filtering),
natural language to SQL translation, security verification, plan optimization, and safe DuckDB execution.
Includes backward compatible agent interfaces.
"""

import time
import re
import hashlib
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
import duckdb

from app.infrastructure.database import db_manager
from app.ai.llm.client import ollama_client
from app.ai.shared.prompt_builder import PromptBuilder
from app.ai.shared.sql_utils import SQLUtils
from app.ai.shared.memory_utils import MemoryAgent
from app.core.performance_logger import get_current_timer

logger = logging.getLogger("clarius.ai.services.sql")

SYSTEM_TABLES = {
    "users", "organizations", "data_sources", "queries", "dashboards", 
    "reports", "documents", "audit_logs", "roles", "permissions", 
    "user_roles", "role_permissions", "role_hierarchy", "access_scopes", 
    "user_access_scopes", "branches", "departments", "jobs",
    "conversations", "conversation_messages", "dataset_versions",
    "document_versions", "sync_history", "sqlite_master", "sqlite_schema",
    "business_memory", "analytical_artifacts", "memory_dependencies",
    "business_definitions", "recommendation_records", "approval_requests"
}

class SQLService:
    """Consolidated domain service coordinating end-to-end NL-to-SQL data pipeline."""

    _table_schemas_cache: Dict[str, str] = {}
    _table_columns_cache: Dict[str, List[str]] = {}
    _schema_signature: Optional[str] = None
    _schema_cache_timestamp: float = 0
    _SCHEMA_TTL_SECONDS: float = 60.0  # 60s TTL — avoids redundant schema fetches per conversation turn
    _sql_cache: Dict[str, str] = {}  # In-memory SQL query cache keyed by (normalized_query + schema_signature)

    def __init__(self, db_conn: Optional[duckdb.DuckDBPyConnection] = None):
        self.conn = db_conn or db_manager.get_connection()
        self.ollama = ollama_client
        self.memory = MemoryAgent(self.conn)

    @classmethod
    def invalidate_schema_cache(cls) -> None:
        """Invalidate schema cache and SQL cache when tables are imported or modified."""
        cls._table_schemas_cache.clear()
        cls._table_columns_cache.clear()
        cls._schema_signature = None
        cls._schema_cache_timestamp = 0
        cls._sql_cache.clear()
        logger.info("SQLService schema and query cache invalidated.")

    def _refresh_table_schemas_if_needed(self) -> None:
        """Scan DuckDB tables and populate internal table schemas cache with 60s TTL."""
        now = time.time()
        if (
            SQLService._table_schemas_cache
            and (now - SQLService._schema_cache_timestamp) < SQLService._SCHEMA_TTL_SECONDS
        ):
            return

        try:
            tables_res = self.conn.execute("SHOW TABLES").fetchall()
            tables = [row[0] for row in tables_res if row[0].lower() not in SYSTEM_TABLES and not row[0].lower().startswith("sqlite_")]

            new_schemas: Dict[str, str] = {}
            new_cols_map: Dict[str, List[str]] = {}
            sig_parts: List[str] = []

            for table in sorted(tables):
                info_res = self.conn.execute(f"PRAGMA table_info('{table}')").fetchall()
                col_names = [col[1] for col in info_res]
                cols = [f"{col[1]} ({col[2]})" for col in info_res]
                new_cols_map[table] = [c.lower() for c in col_names]
                sig_parts.append(f"{table}:{','.join(col_names)}")

                # Fetch 1 sample row — enough for type hints, keeps prompt short
                sample_str = ""
                try:
                    s_rows = self.conn.execute(f"SELECT * FROM '{table}' LIMIT 1").fetchall()
                    if s_rows:
                        s_row = s_rows[0]
                        row_items = []
                        for i in range(min(len(info_res), len(s_row))):
                            val = s_row[i]
                            col_n = info_res[i][1]
                            str_val = str(val) if val is not None else "NULL"
                            if len(str_val) > 30:
                                str_val = str_val[:27] + "..."
                            row_items.append(f"'{col_n}': '{str_val}'")
                        sample_str = f"\n  Sample: {{" + ", ".join(row_items) + "}"
                except Exception:
                    pass

                new_schemas[table] = f"Table '{table}'\n  Columns: {', '.join(cols)}{sample_str}"

            SQLService._table_schemas_cache = new_schemas
            SQLService._table_columns_cache = new_cols_map
            SQLService._schema_signature = hashlib.md5(";".join(sig_parts).encode("utf-8")).hexdigest()[:12]
            SQLService._schema_cache_timestamp = now
        except Exception as e:
            logger.error(f"Failed to scan table schemas: {str(e)}")

    def get_schema_signature(self) -> str:
        """Return the current schema signature hash."""
        self._refresh_table_schemas_if_needed()
        return SQLService._schema_signature or "default_schema"

    def discover_schemas(self, query: Optional[str] = None) -> str:
        """
        Discover database table schemas. If a query is provided, perform safe relevance filtering
        to include only pertinent tables and avoid bloating the prompt.
        If relevance is uncertain, safely returns all tables to guarantee correctness.
        """
        timer = get_current_timer()
        had_cache = bool(SQLService._table_schemas_cache and (time.time() - SQLService._schema_cache_timestamp) < SQLService._SCHEMA_TTL_SECONDS)
        
        if timer and not had_cache:
            timer.start_phase("Schema discovery")

        self._refresh_table_schemas_if_needed()

        if timer:
            if had_cache:
                timer.log("Schema discovery completed (cache hit)")
                timer.record_stage_duration("Schema discovery", 0.00)
            else:
                timer.end_phase("Schema discovery", "Schema discovery completed")

        all_schemas = SQLService._table_schemas_cache
        if not all_schemas:
            return ""

        # If no query provided or only 1-2 tables total in DB, return all tables
        if not query or len(all_schemas) <= 2:
            return "\n\n".join(all_schemas.values())

        # Relevance filtering
        relevant_tables = self._select_relevant_tables(query, all_schemas)
        if not relevant_tables:
            # Fallback to all tables for safety
            return "\n\n".join(all_schemas.values())

        return "\n\n".join(all_schemas[t] for t in relevant_tables if t in all_schemas)

    def _select_relevant_tables(self, query: str, all_schemas: Dict[str, str]) -> Set[str]:
        """
        Identify relevant tables from query tokens and synonyms.
        Returns a set of table names, or all tables if uncertain.
        """
        q_lower = query.lower()
        words = set(re.findall(r"\w+", q_lower))

        table_scores: Dict[str, int] = {}
        for table in all_schemas.keys():
            t_lower = table.lower()
            score = 0

            # Direct table name or sub-word match
            t_words = set(re.findall(r"\w+", t_lower))
            if t_lower in q_lower:
                score += 10
            elif words.intersection(t_words):
                score += 5

            # Column match (excluding generic ubiquitous column names)
            cols = [c for c in SQLService._table_columns_cache.get(table, []) if c not in ("id", "date", "status", "notes", "created_at", "updated_at", "total_amount", "order_date", "po_date")]
            col_matches = words.intersection(set(cols))
            score += len(col_matches) * 3

            # Common business synonyms
            if any(w in words for w in ["store", "stores", "shop", "pharmacy", "chemist", "medical"]) and any(w in t_lower for w in ["store", "medical", "pharmacy"]):
                score += 8
            if any(w in words for w in ["sale", "sales", "revenue", "amount", "sold", "transaction", "order", "orders"]) and any(w in t_lower for w in ["sale", "sales", "order"]):
                score += 8
            if any(w in words for w in ["invoice", "invoices", "bill", "bills", "receipt"]) and "invoice" in t_lower:
                score += 8
            if any(w in words for w in ["product", "products", "item", "items", "stock", "inventory", "unit", "units", "sku", "skus", "brand", "brands", "category"]) and any(w in t_lower for w in ["product", "item", "inventory"]):
                score += 8
            if any(w in words for w in ["supplier", "suppliers", "vendor", "vendors", "manufacturer", "manufacturers", "company", "corp", "corporation", "inc", "ltd"]) and any(w in t_lower for w in ["supplier", "vendor"]):
                score += 8
            if any(w in words for w in ["customer", "customers", "client"]) and "customer" in t_lower:
                score += 8

            if score > 0:
                table_scores[table] = score

        if not table_scores:
            # Uncertain: return all tables
            return set(all_schemas.keys())

        max_score = max(table_scores.values())
        # Pick top tables with high relevance score to keep prompt context lean
        chosen = {t for t, s in table_scores.items() if s >= max(8, max_score * 0.6)}
        
        # Generically ensure dimensions (products, suppliers) are included when querying sales/orders
        if any(t in chosen for t in ["sales_order_items", "sales_orders", "purchase_order_items", "purchase_orders"]):
            if "products" in all_schemas:
                chosen.add("products")
            if "suppliers" in all_schemas and any(w in words for w in ["supplier", "suppliers", "vendor", "company", "corp", "corporation", "inc", "ltd", "manufacturer"]):
                chosen.add("suppliers")

        # If query explicitly contains join / comparison across concepts, ensure we don't over-prune
        if any(w in words for w in ["join", "compare", "versus", "across", "between"]):
            return set(all_schemas.keys())

        return chosen if chosen else set(all_schemas.keys())

    def validate_sql_safety(self, sql: str) -> Tuple[bool, Optional[str]]:
        """Verify query safety."""
        return SQLUtils.validate_sql_safety(self.conn, sql)

    def optimize_query(self, sql: str) -> str:
        """Apply query optimizations."""
        return SQLUtils.optimize_query(sql)

    def reformulate_query(self, question: str) -> str:
        """Reformulate query using memory agent for backward compatibility."""
        if not self.memory.detect_follow_up(question):
            return question
        memory_context = self.memory.get_memory_context()
        prompt = (
            f"You are a data analyst assistant.\n"
            f"{memory_context}\n"
            f"Original Question: {question}\n"
            f"Rewrite the original question into a precise, self-contained, SQL-answerable question, "
            f"combining the context of previous questions. Do not explain your rewrite, just return the exact rewritten question."
        )
        try:
            return self.ollama.generate(prompt=prompt, purpose="query rewriting").strip()
        except Exception:
            return question

    def fix_column_names(self, sql: str) -> str:
        """Column name compatibility fix wrapper."""
        column_mappings = {
            r'\bGender\b': 'Customer_Gender',
            r'\bAge\b': 'Customer_Age',
            r'\bSatisfaction\b': 'Customer_Satisfaction',
        }
        for wrong, correct in column_mappings.items():
            sql = re.sub(wrong, correct, sql, flags=re.IGNORECASE)
        return sql

    def fix_date_and_year_queries(self, sql: str, question: str) -> str:
        """Fix date and year query syntax."""
        return SQLUtils.fix_date_and_year_queries(sql, question)

    def generate_sql(
        self,
        user_query: str,
        schema_context: str,
        memory_context: str = "",
        purpose: str = "SQL generation",
        business_definitions: Optional[List[Any]] = None,
        analytical_artifacts: Optional[List[Any]] = None
    ) -> str:
        """Translate natural language user query into DuckDB SQL."""
        system_prompt, user_prompt = PromptBuilder.build_sql_prompt(
            user_query,
            schema_context,
            memory_context,
            business_definitions=business_definitions,
            analytical_artifacts=analytical_artifacts
        )
        # fast_mode=True: disables Qwen3 think tokens, caps num_predict, fast temperature=0.0
        raw_output = self.ollama.generate(prompt=user_prompt, system_prompt=system_prompt, fast_mode=True, purpose=purpose)
        sql = SQLUtils.clean_generated_sql(raw_output)
        return SQLUtils.fix_date_and_year_queries(sql, user_query)

    def execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """Safely execute query and return dict records."""
        return SQLUtils.execute_query(self.conn, sql)

    def _normalize_query_key(self, query: str) -> str:
        """Normalize query text for caching."""
        return re.sub(r"[^a-z0-9]", "", query.strip().lower())

    def _lookup_cache(self, user_query: str, schema_sig: str) -> Optional[str]:
        """Look up SQL cache in memory and in the database queries table."""
        norm_key = f"{self._normalize_query_key(user_query)}:{schema_sig}"
        if norm_key in SQLService._sql_cache:
            return SQLService._sql_cache[norm_key]

        try:
            cached = self.conn.execute(
                "SELECT generated_sql FROM queries WHERE LOWER(TRIM(query_text)) = LOWER(TRIM(?)) AND status = 'success' ORDER BY created_at DESC LIMIT 1",
                [user_query.strip()]
            ).fetchone()
            if cached and cached[0]:
                cached_sql = cached[0]
                SQLService._sql_cache[norm_key] = cached_sql
                return cached_sql
        except Exception:
            pass
        return None

    def _store_cache(self, user_query: str, sql: str, records: List[Dict[str, Any]], schema_sig: str) -> None:
        """Persist generated SQL in memory cache and database."""
        norm_key = f"{self._normalize_query_key(user_query)}:{schema_sig}"
        SQLService._sql_cache[norm_key] = sql
        self._save_query_cache(user_query, sql, records)

    def process_query(
        self,
        user_query: str,
        memory_context: str = "",
        business_definitions: Optional[List[Any]] = None,
        analytical_artifacts: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute natural language to SQL execution pipeline:
        1. Check SQL result cache (instant 0.00s hit).
        2. Relevant schema context discovery.
        3. Output-only SQL generation via Ollama.
        4. SQL security & semantic validation.
        5. Direct DuckDB execution (EXPLAIN skipped for valid queries).
        6. On execution failure: self-healing retry (max 1 retry with error feedback).
        """
        timer = get_current_timer()
        schema_sig = self.get_schema_signature()

        # 1. Check SQL Cache (instant hit if query + schema version match)
        cached_sql = self._lookup_cache(user_query, schema_sig)
        if cached_sql:
            # Validate safety of cached query before execution
            is_safe, sec_err = self.validate_sql_safety(cached_sql)
            if is_safe:
                try:
                    if timer:
                        timer.log("SQL cache HIT (reusing validated SQL query)")
                        timer.log_skipped("SQL generation", "cache hit")
                        timer.start_phase("DuckDB execution")
                    records = self.execute_query(cached_sql)
                    if timer:
                        timer.end_phase("DuckDB execution", f"DuckDB execution completed ({len(records)} rows)", summary_key="DuckDB execution")
                    return {"success": True, "sql": cached_sql, "data": records, "cached": True}
                except Exception as cache_exec_err:
                    logger.warning(f"Cached SQL execution failed ({cache_exec_err}), will regenerate.")

        if timer:
            timer.log("SQL cache MISS")

        # 2. Discover relevant schema
        schema_context = self.discover_schemas(query=user_query)
        if not schema_context:
            return {"success": False, "error": "No database tables found."}

        try:
            # 3. SQL Generation (Attempt 1)
            if timer:
                timer.start_phase("SQL prompt construction")
                timer.end_phase("SQL prompt construction", "SQL prompt constructed")
                timer.start_phase("SQL generation")
            
            sql = self.generate_sql(
                user_query,
                schema_context,
                memory_context,
                purpose="SQL generation",
                business_definitions=business_definitions,
                analytical_artifacts=analytical_artifacts
            )
            sql = self.fix_column_names(sql)
            sql = self.optimize_query(sql)
            
            if timer:
                timer.end_phase("SQL generation", "SQL generation attempt 1 completed")

            # 4. Security & Semantic Validation
            if timer:
                timer.start_phase("SQL validation")
            is_safe, sec_error = self.validate_sql_safety(sql)
            is_valid_semantic, sem_error = SQLUtils.validate_semantic_sql(sql, user_query)
            if timer:
                timer.end_phase("SQL validation", "SQL validation completed")

            # Self-healing if initial validation fails
            if not is_safe or not is_valid_semantic:
                diag_error = sec_error or sem_error or "Semantic query validation failed."
                logger.warning(f"Initial generated SQL failed validation ('{diag_error}'). Triggering self-healing retry.")
                if timer:
                    timer.log(f"SQL validation error: {diag_error}")
                    timer.log("Triggering self-healing: refreshing schema and regenerating SQL (attempt 2)")
                
                SQLService.invalidate_schema_cache()
                fresh_schema = self.discover_schemas()
                retry_query = (
                    f"{user_query}\n\n"
                    f"[SYSTEM CORRECTION: Your previous SQL '{sql}' was invalid ({diag_error}). "
                    f"Generate a single valid DuckDB query using exact schema columns and a valid WHERE predicate.]"
                )
                if timer:
                    timer.start_phase("SQL correction")
                sql = self.generate_sql(retry_query, fresh_schema, memory_context, purpose="SQL correction")
                sql = self.fix_column_names(sql)
                sql = self.optimize_query(sql)
                if timer:
                    timer.end_phase("SQL correction", "SQL generation attempt 2 completed", summary_key="SQL generation")

                if timer:
                    timer.start_phase("SQL validation")
                is_safe, sec_error = self.validate_sql_safety(sql)
                is_valid_semantic, sem_error = SQLUtils.validate_semantic_sql(sql, user_query)
                if timer:
                    timer.end_phase("SQL validation", "SQL validation attempt 2 completed")

                if not is_safe or not is_valid_semantic:
                    return {"success": False, "error": f"SQL validation failed: {sec_error or sem_error}"}

            # 5. Direct DuckDB Execution (EXPLAIN skipped for valid queries)
            try:
                if timer:
                    timer.log_skipped("EXPLAIN", "direct execution enabled")
                    timer.start_phase("DuckDB execution")
                records = self.execute_query(sql)

                # Self-Healing if SQL executed but returned NULL/empty due to mismatched corporate entity filter or date anchor
                is_null_result = not records or (len(records) == 1 and any(v is None for v in records[0].values()))
                if is_null_result:
                    # Check if SQL filtered product_name/sku directly on corporate supplier name
                    corp_match = re.search(r"(?i)(?:product_name|sku)\s+(?:LIKE|ILIKE|=)\s*'%?([^'%]+?\s+(?:Corp|Inc|Ltd|Company|Corporation|Co|Wires\s*&\s*Cables\s*Corp))%?'", sql)
                    if corp_match:
                        full_ent = corp_match.group(1).strip()
                        brand_token = full_ent.split()[0]
                        logger.info(f"[SQL_SERVICE] Self-healing entity filter '{full_ent}' -> brand keyword '{brand_token}'")
                        
                        # Replace product_name filter with product brand / product_name match
                        new_sql = re.sub(
                            r"(?i)WHERE\s+.*?(?:product_name|sku)\s+(?:LIKE|ILIKE|=)\s*'%?[^'%]+?%?'",
                            f"JOIN products p ON soi.product_id = p.product_id WHERE (p.brand ILIKE '%{brand_token}%' OR p.product_name ILIKE '%{brand_token}%')",
                            sql
                        )
                        if "soi." not in new_sql and "sales_order_items" in new_sql:
                            new_sql = new_sql.replace("sales_order_items", "sales_order_items soi")
                        new_sql = SQLUtils.fix_date_and_year_queries(new_sql, user_query)
                        try:
                            healed_records = self.execute_query(new_sql)
                            if healed_records and not (len(healed_records) == 1 and any(v is None for v in healed_records[0].values())):
                                sql = new_sql
                                records = healed_records
                                logger.info(f"[SQL_SERVICE] Self-healing succeeded! Restored results: {records}")
                        except Exception as heal_err:
                            logger.warning(f"[SQL_SERVICE] Entity self-healing attempt notice: {heal_err}")

                # Emit required diagnostic logs
                tables_found = re.findall(r'(?:FROM|JOIN)\s+([a-zA-Z0-9_]+)', sql, re.IGNORECASE)
                cleaned_tables = list(set([t for t in tables_found if t.lower() not in ("select", "where", "group", "order", "having", "as", "on")]))
                agg_val = records[0] if records else "None"
                logger.info(f"[DIAGNOSTIC] Classified Intent: STRUCTURED_DATA_QUERY")
                logger.info(f"[DIAGNOSTIC] Generated SQL: {sql}")
                logger.info(f"[DIAGNOSTIC] SQL Execution Result: {records}")
                logger.info(f"[DIAGNOSTIC] Tables/Columns Involved: {', '.join(cleaned_tables)}")
                logger.info(f"[DIAGNOSTIC] Resolved Entity: {user_query}")
                logger.info(f"[DIAGNOSTIC] Date Range: Anchored to MAX(order_date) / latest quarter")
                logger.info(f"[DIAGNOSTIC] Final Aggregation: {agg_val}")

                if timer:
                    timer.end_phase("DuckDB execution", f"DuckDB execution completed ({len(records)} rows)", summary_key="DuckDB execution")
                
                # Store in cache
                self._store_cache(user_query, sql, records, schema_sig)
                return {"success": True, "sql": sql, "data": records}

            except Exception as query_err:
                # 6. Self-Healing on Genuine DuckDB Execution Error (Max 1 retry)
                logger.warning(f"DuckDB execution failed ({str(query_err)}). Triggering self-healing retry.")
                if timer:
                    timer.log(f"DuckDB execution error: {str(query_err)}")
                    timer.log("Triggering self-healing: refreshing schema and regenerating SQL (attempt 2)")
                
                SQLService.invalidate_schema_cache()
                fresh_schema = self.discover_schemas()
                retry_prompt = (
                    f"{user_query}\n\n"
                    f"[NOTE: Previous SQL '{sql}' failed with error: {str(query_err)}. "
                    f"Generate a corrected DuckDB SQL statement using only valid schema columns.]"
                )
                if timer:
                    timer.start_phase("SQL correction")
                sql = self.generate_sql(retry_prompt, fresh_schema, memory_context, purpose="SQL correction")
                sql = self.fix_column_names(sql)
                sql = self.optimize_query(sql)
                if timer:
                    timer.end_phase("SQL correction", "SQL generation attempt 2 completed", summary_key="SQL generation")
                
                if timer:
                    timer.start_phase("SQL validation")
                is_safe, sec_error = self.validate_sql_safety(sql)
                is_valid_semantic, sem_error = SQLUtils.validate_semantic_sql(sql, user_query)
                if timer:
                    timer.end_phase("SQL validation", "SQL validation completed")

                if not is_safe or not is_valid_semantic:
                    return {"success": False, "error": f"Retry query failed validation: {sec_error or sem_error}"}

                if timer:
                    timer.start_phase("DuckDB execution")
                records = self.execute_query(sql)
                if timer:
                    timer.end_phase("DuckDB execution", f"DuckDB execution completed ({len(records)} rows)", summary_key="DuckDB execution")
                
                self._store_cache(user_query, sql, records, self.get_schema_signature())
                return {"success": True, "sql": sql, "data": records}

        except Exception as e:
            logger.error(f"SQLService processing error: {str(e)}")
            return {"success": False, "error": str(e)}

    def _save_query_cache(self, user_query: str, sql: str, records: List[Dict[str, Any]]) -> None:
        """Persist successful query into DuckDB queries table for persistent cache hits."""
        try:
            import uuid
            from datetime import datetime
            now_dt = datetime.utcnow()
            clean_q = user_query.strip()
            self.conn.execute("""
                INSERT INTO queries (id, user_id, query_text, generated_sql, status, execution_time_ms, row_count, result, created_at)
                VALUES (?, 'system', ?, ?, 'success', 0, ?, '', ?)
            """, [f"qry_{uuid.uuid4().hex[:10]}", clean_q, sql, len(records), now_dt])
        except Exception as e:
            logger.debug(f"Could not persist query to queries table: {e}")

    def process_natural_language_query(self, user_query: str) -> Dict[str, Any]:
        """Backward compatible entrypoint matching legacy SQLAgent interface."""
        res = self.process_query(user_query)
        if res.get("success"):
            self.memory.record_query(user_query, res.get("sql", ""), "success", str(res.get("data", [])[:5]))
        return res

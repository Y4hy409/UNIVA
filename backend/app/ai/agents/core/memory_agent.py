import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import duckdb

class MemoryAgent:
    """Manages chat context and detects follow-up intent from recent user queries."""
    
    def __init__(self, db_conn: Optional[duckdb.DuckDBPyConnection] = None, max_entries: int = 5):
        self.conn = db_conn
        self.max_entries = max_entries
        self.local_cache: List[Dict[str, Any]] = []

    def record_query(self, query_text: str, generated_sql: str = "", status: str = "success", result: str = "") -> None:
        """Record query and result in queries table for session memory persistence."""
        entry = {
            "question": query_text,
            "sql": generated_sql,
            "status": status,
            "result": result
        }
        self.local_cache.append(entry)
        if len(self.local_cache) > self.max_entries * 2:
            self.local_cache = self.local_cache[-self.max_entries:]

        if self.conn:
            try:
                now = datetime.utcnow()
                self.conn.execute(
                    """
                    INSERT INTO queries (id, user_id, query_text, generated_sql, status, result, error_message, execution_time_ms, created_at, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [str(uuid.uuid4()), "default_user", query_text, generated_sql, status, str(result)[:1000], "", 0, now, now]
                )
            except Exception:
                pass

    def load_history_from_db(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch previous query logs from the CLARIUS queries database table or memory cache."""
        history = []
        if self.conn:
            try:
                res = self.conn.execute(
                    "SELECT query_text, generated_sql, status, result "
                    "FROM queries "
                    "WHERE status = 'success' OR status = 'ok' "
                    "ORDER BY created_at DESC LIMIT ?", 
                    [limit]
                ).fetchall()
                for row in reversed(res):
                    history.append({
                        "question": row[0],
                        "sql": row[1],
                        "status": row[2],
                        "result": row[3]
                    })
            except Exception:
                pass
        
        if not history and self.local_cache:
            history = self.local_cache[-limit:]
            
        return history

    def get_memory_context(self) -> str:
        history = self.load_history_from_db(self.max_entries)
        if not history:
            return ""
        context = "\nPrevious Conversation / Query History:\n"
        for i, item in enumerate(history, 1):
            q = item.get('question', '')
            sql = item.get('sql', '')
            context += f"{i}. User asked: \"{q}\"\n"
            if sql:
                context += f"   Generated SQL: {sql}\n"
        return context

    def detect_follow_up(self, question: str) -> bool:
        """Returns True if there is previous history context to inform the current prompt."""
        history = self.load_history_from_db(1)
        return len(history) > 0


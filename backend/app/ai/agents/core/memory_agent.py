from typing import List, Dict, Any, Optional
import duckdb

class MemoryAgent:
    """Manages chat context and detects follow-up intent from recent user queries."""
    
    def __init__(self, db_conn: Optional[duckdb.DuckDBPyConnection] = None, max_entries: int = 5):
        self.conn = db_conn
        self.max_entries = max_entries
        self.local_cache: List[Dict[str, Any]] = []

    def load_history_from_db(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch previous query logs from the CLARIUS queries database table."""
        if not self.conn:
            return self.local_cache
        try:
            res = self.conn.execute(
                "SELECT query_text, generated_sql, status, result "
                "FROM queries "
                "ORDER BY created_at DESC LIMIT ?", 
                (limit,)
            ).fetchall()
            # Construct standard history list of dicts: newest last
            history = []
            for row in reversed(res):
                history.append({
                    "question": row[0],
                    "sql": row[1],
                    "status": row[2],
                    "result": row[3]
                })
            return history
        except Exception:
            return self.local_cache

    def get_memory_context(self) -> str:
        history = self.load_history_from_db(self.max_entries)
        if not history:
            return ""
        context = "\nPrevious Conversation Context:\n"
        for i, item in enumerate(history, 1):
            context += f"{i}. Q: \"{item['question']}\"\n"
        return context

    def detect_follow_up(self, question: str) -> bool:
        follow_up_words = [
            "what about", "how about", "also", "too", "same for",
            "that region", "that product", "there", "it", "this",
            "those", "these", "them"
        ]
        q_lower = question.lower()
        return any(word in q_lower for word in follow_up_words)

"""
CLARIUS Backend - Conversation Memory Manager

Manages persistent session-based conversation state including query history,
SQL statements, chart metadata, retrieved documents, entities, filters, and business dimensions.
Supports rolling interaction limits and context summarization.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("clarius.ai.conversation_memory")

class ConversationSession:
    """Represents a single chat session's persistent memory state."""
    
    def __init__(self, conversation_id: str, max_interactions: int = 20):
        self.conversation_id = conversation_id
        self.max_interactions = max_interactions
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        self.messages: List[Dict[str, Any]] = []
        self.intent_history: List[str] = []
        self.sql_history: List[str] = []
        self.chart_history: List[Dict[str, Any]] = []
        self.analytics_history: List[Dict[str, Any]] = []
        self.retrieved_documents: List[Dict[str, Any]] = []
        self.entity_history: List[str] = []
        self.business_dimensions: Dict[str, Any] = {}
        self.filters: Dict[str, Any] = {}
        self.summary: str = ""
        
        # Cache for last interaction for fast resolution
        self.last_query: str = ""
        self.last_sql: str = ""
        self.last_intent: str = ""
        self.last_results: List[Dict[str, Any]] = []

    def record_turn(
        self,
        user_query: str,
        intent: str,
        response_text: str = "",
        sql: str = "",
        results: Optional[List[Dict[str, Any]]] = None,
        chart_config: Optional[Dict[str, Any]] = None,
        documents: Optional[List[Dict[str, Any]]] = None,
        dimensions: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a completed conversation turn into session memory."""
        self.updated_at = datetime.utcnow()
        
        turn_data = {
            "query": user_query,
            "intent": intent,
            "response": response_text,
            "sql": sql,
            "has_results": bool(results),
            "result_count": len(results) if results else 0,
            "timestamp": self.updated_at.isoformat()
        }
        self.messages.append(turn_data)
        self.intent_history.append(intent)
        
        if sql:
            self.sql_history.append(sql)
            self.last_sql = sql
            
        if chart_config:
            self.chart_history.append(chart_config)
            
        if documents:
            self.retrieved_documents.extend(documents)
            
        if dimensions:
            self.business_dimensions.update(dimensions)
            
        if filters:
            self.filters.update(filters)
            
        if results is not None:
            self.last_results = results[:10]  # sample
            
        self.last_query = user_query
        self.last_intent = intent
        
        # Enforce rolling history limit & trim
        self._trim_history()

    def _trim_history(self) -> None:
        """Keep history within max_interactions limit and auto-summarize older turns."""
        if len(self.messages) > self.max_interactions:
            overflow_turns = self.messages[:-self.max_interactions]
            self.messages = self.messages[-self.max_interactions:]
            
            # Simple automatic summarization of past queries
            past_queries = [t.get("query", "") for t in overflow_turns if t.get("query")]
            if past_queries:
                summary_addition = f"Previously discussed topics: {', '.join(past_queries)}. "
                self.summary = (self.summary + " " + summary_addition).strip()

    def get_structured_context(self) -> Dict[str, Any]:
        """Return structured conversation memory snapshot."""
        return {
            "conversation_id": self.conversation_id,
            "summary": self.summary,
            "last_query": self.last_query,
            "last_sql": self.last_sql,
            "last_intent": self.last_intent,
            "dimensions": self.business_dimensions,
            "filters": self.filters,
            "recent_turns": self.messages[-5:],
            "sql_history": self.sql_history[-5:]
        }

    def get_formatted_memory_prompt(self) -> str:
        """Format memory into a concise string for LLM prompts."""
        if not self.messages:
            return ""
            
        lines = ["Recent Conversation History:"]
        if self.summary:
            lines.append(f"Summary: {self.summary}")
            
        for turn in self.messages[-5:]:
            lines.append(f"- User: \"{turn['query']}\"")
            if turn.get("sql"):
                lines.append(f"  SQL: {turn['sql']}")
            if turn.get("response"):
                lines.append(f"  Assistant: {turn['response'][:100]}...")
                
        return "\n".join(lines)


class ConversationMemoryManager:
    """Singleton memory manager handling session lookup and lifecycle."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConversationMemoryManager, cls).__new__(cls)
            cls._instance.sessions: Dict[str, ConversationSession] = {}
        return cls._instance

    def get_session(self, conversation_id: Optional[str]) -> ConversationSession:
        """Get or create session for given conversation_id."""
        cid = conversation_id or "default_session"
        if cid not in self.sessions:
            logger.info(f"Creating new conversation session: {cid}")
            self.sessions[cid] = ConversationSession(conversation_id=cid)
        return self.sessions[cid]

    def clear_session(self, conversation_id: str) -> None:
        """Reset session memory for New Chat."""
        if conversation_id in self.sessions:
            logger.info(f"Clearing conversation session: {conversation_id}")
            del self.sessions[conversation_id]

# Global singleton instance
memory_manager = ConversationMemoryManager()

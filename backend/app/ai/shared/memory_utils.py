"""
CLARIUS Backend - Centralized Memory Utilities

Manages session-based conversation context, follow-up detection, context resolution,
and history summarization across chat interactions.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.ai.llm.client import ollama_client
from app.ai.shared.prompt_builder import PromptBuilder
from app.ai.agents.core.memory_agent import MemoryAgent

logger = logging.getLogger("clarius.ai.shared.memory_utils")

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
        self.retrieved_documents: List[Dict[str, Any]] = []
        self.filters: Dict[str, Any] = {}
        self.summary: str = ""

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
        filters: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record turn into session memory."""
        self.updated_at = datetime.utcnow()

        turn_data = {
            "query": user_query,
            "intent": intent,
            "response": response_text,
            "sql": sql,
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

        if filters:
            self.filters.update(filters)

        if results is not None:
            self.last_results = results[:10]

        self.last_query = user_query
        self.last_intent = intent

        self._trim_history()

    def _trim_history(self) -> None:
        """Keep history within max_interactions limit and auto-summarize older turns."""
        if len(self.messages) > self.max_interactions:
            overflow_turns = self.messages[:-self.max_interactions]
            self.messages = self.messages[-self.max_interactions:]
            past_queries = [t.get("query", "") for t in overflow_turns if t.get("query")]
            if past_queries:
                self.summary = f"{self.summary} Previously discussed: {', '.join(past_queries)}.".strip()

    def get_formatted_memory_prompt(self) -> str:
        """Format history into string for LLM prompts."""
        if not self.messages:
            return ""

        lines = ["Recent Conversation History:"]
        if self.summary:
            lines.append(f"Summary: {self.summary}")

        for turn in self.messages[-5:]:
            lines.append(f"- User: \"{turn['query']}\"")
            if turn.get("sql"):
                lines.append(f"  SQL: {turn['sql']}")

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
        cid = conversation_id or "default_session"
        if cid not in self.sessions:
            logger.info(f"Creating conversation session: {cid}")
            self.sessions[cid] = ConversationSession(conversation_id=cid)
        return self.sessions[cid]

    def clear_session(self, conversation_id: str) -> None:
        if conversation_id in self.sessions:
            del self.sessions[conversation_id]


class ContextResolver:
    """Resolves follow-up queries using heuristics and LLM context merging."""

    FOLLOW_UP_INDICATORS = {
        "only", "also", "compare", "sort", "group", "same", "that", "those", "it", "them",
        "previous", "again", "show more", "next", "filter", "exclude", "include", "instead",
        "last month", "this year", "descending", "ascending", "highest", "lowest", "top", "bottom"
    }

    @classmethod
    def resolve_context(cls, query: str, session: ConversationSession) -> Dict[str, Any]:
        """Resolve user query into a self-contained question."""
        q_lower = query.strip().lower()
        words = set(re.findall(r"\w+", q_lower))

        is_follow_up = bool(session.last_query or session.last_sql) and (
            bool(words.intersection(cls.FOLLOW_UP_INDICATORS)) or len(words) <= 4
        )

        if not is_follow_up:
            return {
                "resolved_query": query,
                "is_follow_up": False,
                "base_sql": "",
                "base_query": ""
            }

        prev_query = session.last_query
        prev_sql = session.last_sql

        # Deterministic matchers for location, sort, compare
        loc_match = re.match(r"^(only|just|for|in|filter by)\s+([a-zA-Z\s]+)$", query.strip(), re.IGNORECASE)
        if loc_match:
            entity = loc_match.group(2).strip().title()
            return {
                "resolved_query": f"{prev_query} for {entity}",
                "is_follow_up": True,
                "base_sql": prev_sql,
                "base_query": prev_query
            }

        sort_match = re.match(r"^(sort|order)\s+(descending|ascending|by\s+[a-zA-Z\s]+|desc|asc)$", query.strip(), re.IGNORECASE)
        if sort_match:
            return {
                "resolved_query": f"{prev_query} sorted {sort_match.group(2).strip()}",
                "is_follow_up": True,
                "base_sql": prev_sql,
                "base_query": prev_query
            }

        # LLM Context Resolver Fallback
        prompt = PromptBuilder.build_context_resolver_prompt(query, prev_sql, session.get_formatted_memory_prompt())
        try:
            resolved = ollama_client.generate(prompt=prompt).strip().strip('"')
            if resolved:
                return {
                    "resolved_query": resolved,
                    "is_follow_up": True,
                    "base_sql": prev_sql,
                    "base_query": prev_query
                }
        except Exception as e:
            logger.error(f"LLM Context resolution error: {str(e)}")

        return {
            "resolved_query": f"{prev_query} - {query}",
            "is_follow_up": True,
            "base_sql": prev_sql,
            "base_query": prev_query
        }

# Global singleton
memory_manager = ConversationMemoryManager()

"""
CLARIUS Backend - Conversation Context Resolver

Analyzes incoming user messages against active conversation session state.
Detects follow-up queries, pronouns, filter modifications, and resolves implicit references
into explicit, self-contained business queries before intent routing & SQL generation.
"""

import re
import logging
from typing import Dict, Any, Optional, Tuple
from app.ai.conversation_memory import ConversationSession
from app.ai.llm.client import ollama_client

logger = logging.getLogger("clarius.ai.context_resolver")

class ConversationContextResolver:
    """Resolves follow-up queries using rule-based heuristics and local LLM context merging."""

    FOLLOW_UP_INDICATORS = {
        "only", "also", "compare", "sort", "group", "same", "that", "those", "it", "them",
        "previous", "again", "show more", "next", "filter", "exclude", "include", "instead",
        "last month", "this year", "descending", "ascending", "highest", "lowest", "top",
        "bottom", "order by", "now", "where", "with", "than", "and"
    }

    # Common location/category filter follow-up patterns
    LOCATION_REGEX = r"^(only|just|for|in|filter by)\s+([a-zA-Z\s]+)$"
    SORT_REGEX = r"^(sort|order)\s+(descending|ascending|by\s+[a-zA-Z\s]+|desc|asc)$"
    COMPARE_REGEX = r"^(compare\s+with|and|versus|vs)\s+([a-zA-Z\s]+)$"

    @classmethod
    def is_follow_up(cls, query: str, session: ConversationSession) -> bool:
        """Check if query is a follow-up referring to previous session context."""
        if not session.last_query and not session.last_sql:
            return False

        q_lower = query.strip().lower()
        words = set(re.findall(r"\w+", q_lower))

        # Check keyword intersections
        if words.intersection(cls.FOLLOW_UP_INDICATORS):
            return True

        # Check short phrase length (<= 4 words) when session has history
        if len(words) <= 4:
            return True

        return False

    @classmethod
    def resolve_context(cls, query: str, session: ConversationSession) -> Dict[str, Any]:
        """
        Main entry point for resolving user query context.
        Returns dict containing:
        - resolved_query: self-contained query text
        - is_follow_up: bool
        - base_sql: str (previous SQL if applicable)
        - base_query: str (previous query text)
        """
        if not cls.is_follow_up(query, session):
            return {
                "resolved_query": query,
                "is_follow_up": False,
                "base_sql": "",
                "base_query": ""
            }

        prev_query = session.last_query
        prev_sql = session.last_sql
        q_clean = query.strip()
        q_lower = q_clean.lower()

        logger.info(f"ContextResolver: Resolving follow-up '{query}' against previous '{prev_query}'")

        # 1. Deterministic Rule Matching for common follow-up forms
        
        # Pattern: "Only <Entity>" or "for <Entity>"
        loc_match = re.match(cls.LOCATION_REGEX, q_lower, re.IGNORECASE)
        if loc_match:
            entity = loc_match.group(2).strip().title()
            resolved = f"{prev_query} for {entity}"
            return {
                "resolved_query": resolved,
                "is_follow_up": True,
                "base_sql": prev_sql,
                "base_query": prev_query
            }

        # Pattern: "Sort descending" / "Order by sales"
        sort_match = re.match(cls.SORT_REGEX, q_lower, re.IGNORECASE)
        if sort_match:
            sort_dir = sort_match.group(2).strip()
            resolved = f"{prev_query} sorted {sort_dir}"
            return {
                "resolved_query": resolved,
                "is_follow_up": True,
                "base_sql": prev_sql,
                "base_query": prev_query
            }

        # Pattern: "Compare with Bangalore"
        compare_match = re.match(cls.COMPARE_REGEX, q_lower, re.IGNORECASE)
        if compare_match:
            target = compare_match.group(2).strip().title()
            resolved = f"Compare {prev_query} with {target}"
            return {
                "resolved_query": resolved,
                "is_follow_up": True,
                "base_sql": prev_sql,
                "base_query": prev_query
            }

        # 2. LLM Context Resolver Fallback for complex follow-up queries
        memory_prompt = session.get_formatted_memory_prompt()
        prompt = (
            f"You are a Data Conversation Context Resolver.\n"
            f"Given the conversation history and the latest follow-up question, rewrite the latest question into a clear, self-contained business query.\n\n"
            f"{memory_prompt}\n"
            f"Previous SQL Query: {prev_sql}\n"
            f"Latest User Message: \"{query}\"\n\n"
            f"Rules:\n"
            f"1. Combine previous filters, dimensions, and targets with the new request.\n"
            f"2. Return ONLY the rewritten self-contained question. Do not explain."
        )

        try:
            llm_resolved = ollama_client.generate(prompt=prompt).strip().strip('"')
            if llm_resolved:
                logger.info(f"ContextResolver LLM rewrite: '{query}' -> '{llm_resolved}'")
                return {
                    "resolved_query": llm_resolved,
                    "is_follow_up": True,
                    "base_sql": prev_sql,
                    "base_query": prev_query
                }
        except Exception as e:
            logger.error(f"ContextResolver LLM rewrite failed: {str(e)}")

        # Fallback: append follow-up to base query
        fallback_resolved = f"{prev_query} - {query}"
        return {
            "resolved_query": fallback_resolved,
            "is_follow_up": True,
            "base_sql": prev_sql,
            "base_query": prev_query
        }

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

from app.application.memory.context_retrieval_service import context_retrieval_service
from app.application.memory.business_memory_service import business_memory_service
from app.domain.memory_models import MemoryStatus

logger = logging.getLogger("clarius.ai.context_resolver")

class ConversationContextResolver:
    """Resolves follow-up queries and cross-functional references using rule heuristics, Business Memory, and local LLM context merging."""

    FOLLOW_UP_INDICATORS = {
        "only", "also", "compare", "sort", "group", "same", "that", "those", "it", "them",
        "previous", "again", "show more", "next", "filter", "exclude", "include", "instead",
        "last month", "this year", "descending", "ascending", "highest", "lowest", "top",
        "bottom", "order by", "now", "where", "with", "than", "and", "above", "that analysis",
        "the sales", "that report", "same numbers", "same data"
    }

    # Common location/category filter follow-up patterns
    LOCATION_REGEX = r"^(only|just|for|in|filter by)\s+([a-zA-Z\s]+)$"
    SORT_REGEX = r"^(sort|order)\s+(descending|ascending|by\s+[a-zA-Z\s]+|desc|asc)$"
    COMPARE_REGEX = r"^(compare\s+with|and|versus|vs)\s+([a-zA-Z\s]+)$"

    @classmethod
    def is_follow_up(cls, query: str, session: ConversationSession) -> bool:
        """Check if query is a follow-up referring to previous session context or cross-functional memory."""
        q_lower = query.strip().lower()
        words = set(re.findall(r"\w+", q_lower))

        # Check keyword intersections
        if words.intersection(cls.FOLLOW_UP_INDICATORS):
            return True

        # Check cross-functional keywords (e.g. "from that analysis", "approved definition", "the recommendation")
        if any(phrase in q_lower for phrase in ["that analysis", "the analysis", "that report", "the report", "same data", "same numbers", "approved definition", "the recommendation"]):
            return True

        # Check short phrase length (<= 4 words) when session has history
        if session.last_query and len(words) <= 4:
            return True

        return False

    @classmethod
    def resolve_context(
        cls,
        query: str,
        session: ConversationSession,
        user_id: str = "default_user",
        workspace_id: str = "default_workspace",
        target_function: str = "CLARIUS"
    ) -> Dict[str, Any]:
        """
        Main entry point for resolving user query context.
        Queries Business Memory Layer across conversations and functions.
        """
        # 1. Retrieve cross-functional business memory context
        retrieval_res = context_retrieval_service.retrieve_context(
            query=query,
            user_id=user_id,
            workspace_id=workspace_id,
            target_function=target_function
        )

        prev_query = session.last_query
        prev_sql = session.last_sql
        active_artifact = None

        # Check if cross-functional analytical artifact is matched
        if retrieval_res.analytical_artifacts:
            active_artifact = retrieval_res.analytical_artifacts[0]
            if not prev_query and active_artifact.query_text:
                prev_query = active_artifact.query_text
            if not prev_sql and active_artifact.generated_sql:
                prev_sql = active_artifact.generated_sql

            # If artifact dataset was modified (REQUIRES_REVALIDATION), trigger auto-revalidation
            if active_artifact.status == MemoryStatus.REQUIRES_REVALIDATION:
                logger.info(f"ContextResolver: Revalidating stale artifact '{active_artifact.id}' against latest dataset version.")
                revalidated = business_memory_service.revalidate_artifact(active_artifact.id)
                if revalidated:
                    active_artifact = revalidated
                    prev_sql = active_artifact.generated_sql

        if not cls.is_follow_up(query, session) and not active_artifact and not retrieval_res.business_definitions:
            return {
                "resolved_query": query,
                "is_follow_up": False,
                "base_sql": "",
                "base_query": "",
                "context_result": retrieval_res,
                "active_artifact": None
            }

        q_clean = query.strip()
        q_lower = q_clean.lower()

        logger.info(f"ContextResolver: Resolving query '{query}' (prev_query='{prev_query}')")

        # 2. Deterministic Rule Matching for common follow-up forms
        
        # Pattern: "Only <Entity>" or "for <Entity>"
        loc_match = re.match(cls.LOCATION_REGEX, q_lower, re.IGNORECASE)
        if loc_match and prev_query:
            entity = loc_match.group(2).strip().title()
            resolved = f"{prev_query} for {entity}"
            return {
                "resolved_query": resolved,
                "is_follow_up": True,
                "base_sql": prev_sql,
                "base_query": prev_query,
                "context_result": retrieval_res,
                "active_artifact": active_artifact
            }

        # Pattern: "Sort descending" / "Order by sales"
        sort_match = re.match(cls.SORT_REGEX, q_lower, re.IGNORECASE)
        if sort_match and prev_query:
            sort_dir = sort_match.group(2).strip()
            resolved = f"{prev_query} sorted {sort_dir}"
            return {
                "resolved_query": resolved,
                "is_follow_up": True,
                "base_sql": prev_sql,
                "base_query": prev_query,
                "context_result": retrieval_res,
                "active_artifact": active_artifact
            }

        # Pattern: "Compare with Bangalore" / "What about Bangalore?"
        compare_match = re.match(cls.COMPARE_REGEX, q_lower, re.IGNORECASE)
        if compare_match and prev_query:
            target = compare_match.group(2).strip().title()
            resolved = f"Compare {prev_query} with {target}"
            return {
                "resolved_query": resolved,
                "is_follow_up": True,
                "base_sql": prev_sql,
                "base_query": prev_query,
                "context_result": retrieval_res,
                "active_artifact": active_artifact
            }

        if q_lower.startswith("what about ") and prev_query:
            target = q_clean[11:].strip().title()
            resolved = f"{prev_query} for {target}"
            return {
                "resolved_query": resolved,
                "is_follow_up": True,
                "base_sql": prev_sql,
                "base_query": prev_query,
                "context_result": retrieval_res,
                "active_artifact": active_artifact
            }

        # Cross-functional reference patterns: "Create a report using that analysis"
        if any(w in q_lower for w in ["report", "dashboard", "simulation"]) and active_artifact:
            resolved = f"{query} using {active_artifact.query_text}"
            return {
                "resolved_query": resolved,
                "is_follow_up": True,
                "base_sql": active_artifact.generated_sql,
                "base_query": active_artifact.query_text,
                "context_result": retrieval_res,
                "active_artifact": active_artifact
            }

        # 3. LLM Context Resolver Fallback for complex follow-up queries
        memory_prompt = session.get_formatted_memory_prompt()
        if active_artifact and not memory_prompt:
            memory_prompt = f"Previous Analysis: \"{active_artifact.query_text}\"\nSQL: {active_artifact.generated_sql}"

        prompt = (
            f"You are a Data Conversation Context Resolver.\n"
            f"Given the conversation history/business memory and the latest question, rewrite the latest question into a clear, self-contained business query.\n\n"
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
                    "base_query": prev_query,
                    "context_result": retrieval_res,
                    "active_artifact": active_artifact
                }
        except Exception as e:
            logger.error(f"ContextResolver LLM rewrite failed: {str(e)}")

        # Fallback: append follow-up to base query
        fallback_resolved = f"{prev_query} - {query}" if prev_query else query
        return {
            "resolved_query": fallback_resolved,
            "is_follow_up": bool(prev_query),
            "base_sql": prev_sql,
            "base_query": prev_query,
            "context_result": retrieval_res,
            "active_artifact": active_artifact
        }

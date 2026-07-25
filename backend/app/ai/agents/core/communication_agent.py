"""
CLARIUS Backend - Communication Agent

This agent formats conversational responses and constructs system summaries for users (P1.3).
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger("clarius.ai.agents.communication")

class CommunicationAgent:
    """Orchestrates responses and constructs summaries from query statistics or execution data."""

    def format_analytics_explanation(self, query: str, sql_executed: str, data_count: int) -> str:
        """Construct a natural description explaining what data was queried."""
        if data_count == 0:
            return f"I ran the generated database query but found no matching records for: '{query}'."
            
        return (
            f"I resolved your question '{query}' by executing the secure SQL query:\n"
            f"```sql\n{sql_executed}\n```\n"
            f"This returned {data_count} matching rows in the dashboard visualization."
        )

    def format_rag_answer(self, query: str, passages: List[Dict[str, Any]]) -> str:
        """Format matching text passages into a structured reference response."""
        if not passages:
            return "I searched the uploaded document catalog but could not find relevant references."
            
        lines = [f"Based on the matching text chunks for your search '{query}':\n"]
        for idx, item in enumerate(passages):
            title = item["metadata"].get("title", f"Document Chunk {idx + 1}")
            content = item["content"].strip()
            lines.append(f"**Reference {idx + 1}: {title}**\n> {content}\n")
            
        return "\n".join(lines)

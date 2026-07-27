"""
CLARIUS Backend - Communication Agent

This agent formats conversational responses and constructs system summaries for users (P1.3).
"""

import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger("clarius.ai.agents.communication")

class CommunicationAgent:
    """Orchestrates responses and constructs summaries from query statistics or execution data."""

    def format_analytics_explanation(self, query: str, sql_executed: str, data_count: int, records: List[Dict[str, Any]] = None) -> str:
        """Construct a natural description explaining what data was queried."""
        if data_count == 0:
            return "No matching records found."

        # If it's a single value (e.g. 1 row, 1 column), extract and show it directly
        if records and len(records) == 1:
            row = records[0]
            if len(row) == 1:
                val = list(row.values())[0]
                key = list(row.keys())[0]
                label = key.replace("_", " ").title()
                return f"{label}: {val}"

        # Adaptive formatting based on query terms
        clean_q = query.lower().strip()
        if "list" in clean_q or "show" in clean_q or "get" in clean_q:
            # E.g. "show all products" -> "Here are the products:"
            match = re.search(r"(?:list|show|get|view)\s+(?:all\s+)?([a-zA-Z0-9_\s]+)", clean_q)
            if match:
                target = match.group(1).strip()
                return f"Here are the {target}:"

        return "Query results:"

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

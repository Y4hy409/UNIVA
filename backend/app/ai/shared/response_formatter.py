"""
CLARIUS Backend - Centralized Response Formatter

Unified formatting helper for text descriptions, KPI cards, document RAG reference blocks,
and fallback visualization configurations.
"""

import re
from typing import Dict, Any, List, Optional

class ResponseFormatter:
    """Consolidated response formatting utility for text, tables, and charts."""

    @staticmethod
    def format_analytics_explanation(
        query: str,
        sql_executed: str,
        data_count: int,
        records: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Construct natural descriptions for query results."""
        if data_count == 0 or not records:
            return "No matching records found."

        clean_q = query.lower().strip()

        # Single row, single column -> direct label and value formatting
        if len(records) == 1 and len(records[0]) == 1:
            key = list(records[0].keys())[0]
            val = list(records[0].values())[0]
            label = key.replace("_", " ").title()
            return f"{label}: {val}"

        # Adaptive text header based on query action verb
        if any(verb in clean_q for verb in ["list", "show", "get", "view"]):
            match = re.search(r"(?:list|show|get|view)\s+(?:all\s+)?([a-zA-Z0-9_\s]+)", clean_q)
            if match:
                target = match.group(1).strip()
                return f"Here are the {target}:"

        return "Query results:"

    @staticmethod
    def format_rag_answer(query: str, passages: List[Dict[str, Any]]) -> str:
        """Format matching document text chunks into a structured reference response."""
        if not passages:
            return "I searched the uploaded document catalog but could not find relevant references."

        lines = [f"Based on matching document references for '{query}':\n"]
        for idx, item in enumerate(passages):
            title = item.get("metadata", {}).get("title", f"Document Reference {idx + 1}")
            content = item.get("content", "").strip()
            lines.append(f"**Reference {idx + 1}: {title}**\n> {content}\n")

        return "\n".join(lines)

    @staticmethod
    def build_fallback_chart_config(data_samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Produce a default modern ECharts configuration if LLM chart generation is bypassed or fails."""
        if not data_samples:
            return {}

        keys = list(data_samples[0].keys())
        x_col = keys[0]
        y_col = keys[0]

        for k, v in data_samples[0].items():
            if isinstance(v, (int, float)):
                y_col = k
                break

        x_data = [str(row.get(x_col, "")) for row in data_samples[:15]]
        y_data = [row.get(y_col, 0) for row in data_samples[:15]]

        return {
            "title": {"text": "Query Results Visualization"},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": x_data},
            "yAxis": {"type": "value"},
            "series": [{"data": y_data, "type": "bar"}]
        }

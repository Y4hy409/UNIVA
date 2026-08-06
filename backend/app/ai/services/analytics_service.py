"""
CLARIUS Backend - Consolidated Analytics Domain Service

Single cohesive service handling intelligent visualization decisions,
Apache ECharts config generation, and AI analytical insights synthesis.
"""

import json
import re
import logging
from typing import Dict, Any, List, Optional

from app.ai.llm.client import ollama_client
from app.ai.shared.prompt_builder import PromptBuilder
from app.ai.shared.response_formatter import ResponseFormatter

logger = logging.getLogger("clarius.ai.services.analytics")

class AnalyticsService:
    """Consolidated domain service for visual analytics and insight explanations."""

    EXPLICIT_CHART_KEYWORDS = {
        "chart", "graph", "plot", "visualize", "visualization", "dashboard",
        "comparison graph", "bar chart", "line chart", "pie chart", "scatter"
    }

    TIME_SERIES_KEYWORDS = {"date", "month", "year", "quarter", "daily", "monthly", "yearly", "quarterly", "trend", "over time"}
    COMPOSITION_KEYWORDS = {"share", "percentage", "proportion", "breakdown", "distribution", "pie", "portion"}

    def __init__(self):
        self.ollama = ollama_client

    def evaluate_visualization(
        self,
        user_query: str,
        intent: str,
        sql_results: List[Dict[str, Any]],
        columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Evaluate visualization requirements and recommend chart decision."""
        q_lower = user_query.strip().lower()
        cols = columns or (list(sql_results[0].keys()) if sql_results else [])
        row_count = len(sql_results)

        if intent in {"CONVERSATION", "UI_ACTION", "DOCUMENT_KNOWLEDGE_QUERY"} or row_count == 0:
            return {"should_generate_chart": False, "decision": "TEXT_ONLY", "reason": "No chart needed."}

        has_explicit = any(kw in q_lower for kw in self.EXPLICIT_CHART_KEYWORDS)

        if row_count == 1 and len(cols) <= 2 and not has_explicit:
            return {"should_generate_chart": False, "decision": "KPI_CARD", "reason": "Single metric lookup result."}

        if row_count < 3 and not has_explicit:
            return {"should_generate_chart": False, "decision": "TABLE_ONLY", "reason": "Fewer than 3 rows."}

        has_time = any(c.lower() in self.TIME_SERIES_KEYWORDS for c in cols) or any(kw in q_lower for kw in self.TIME_SERIES_KEYWORDS)
        if has_time:
            return {"should_generate_chart": True, "decision": "LINE_CHART", "reason": "Time series data identified."}

        has_comp = any(kw in q_lower for kw in self.COMPOSITION_KEYWORDS)
        if has_comp and row_count <= 7:
            return {"should_generate_chart": True, "decision": "PIE_CHART", "reason": "Composition data identified."}

        return {"should_generate_chart": True, "decision": "BAR_CHART", "reason": "Category comparison identified."}

    def generate_chart_config(self, user_query: str, sql_query: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate Apache ECharts configuration dictionary."""
        if not records:
            return {}

        records_sample = json.dumps(records[:10])
        system_prompt, user_prompt = PromptBuilder.build_echarts_config_prompt(user_query, sql_query, records_sample)

        try:
            raw_output = self.ollama.generate(prompt=user_prompt, system_prompt=system_prompt)
            match = re.search(r"```json(.*?)```", raw_output, re.DOTALL | re.IGNORECASE)
            json_text = match.group(1).strip() if match else raw_output.strip()
            return json.loads(json_text)
        except Exception as e:
            logger.error(f"ECharts generation fallback triggered: {str(e)}")
            return ResponseFormatter.build_fallback_chart_config(records)

    def explain_analytics(self, user_query: str, sql: str, records: List[Dict[str, Any]], intent: str) -> str:
        """Synthesize natural language business explanation for query results."""
        if intent == "ANALYTICS_QUERY" and records:
            prompt = PromptBuilder.build_analytics_explanation_prompt(user_query, str(records[:10]))
            try:
                return self.ollama.generate(prompt=prompt)
            except Exception:
                pass

        return ResponseFormatter.format_analytics_explanation(user_query, sql, len(records), records)

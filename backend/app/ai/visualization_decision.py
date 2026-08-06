"""
CLARIUS Backend - Visualization Decision Engine

Determines whether query responses should generate charts or remain text/table only,
and selects optimal visualization types based on user intent, data cardinality, and explicit requests.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("clarius.ai.visualization_decision")

class VisualizationDecisionAgent:
    """Intelligent decision engine evaluating whether and how to visualize analytical data."""

    EXPLICIT_CHART_KEYWORDS = {
        "chart", "graph", "plot", "visualize", "visualization", "dashboard",
        "comparison graph", "bar chart", "line chart", "pie chart", "scatter"
    }

    COUNT_SINGLE_VALUE_PATTERNS = [
        r"^(what is|show|get|how much is)\s+.*(today'?s revenue|today revenue|revenue today)",
        r"^how many\b",
        r"^(count|total count|total number)\b",
        r"\bis there\b",
        r"\bdoes .* exist\b"
    ]

    TIME_SERIES_KEYWORDS = {
        "date", "month", "year", "quarter", "daily", "monthly", "yearly", "quarterly", "trend", "over time"
    }

    COMPOSITION_KEYWORDS = {
        "share", "percentage", "proportion", "breakdown", "distribution", "pie", "portion"
    }

    @classmethod
    def evaluate(
        self,
        user_query: str,
        intent: str,
        sql_results: List[Dict[str, Any]],
        columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate visualization requirement.
        Returns:
        {
            "should_generate_chart": bool,
            "decision": str,  # TEXT_ONLY, TABLE_ONLY, BAR_CHART, LINE_CHART, PIE_CHART, SCATTER, KPI_CARD, MULTI_CHART
            "reason": str
        }
        """
        q_lower = user_query.strip().lower()
        cols = columns or (list(sql_results[0].keys()) if sql_results else [])
        row_count = len(sql_results)

        # 1. Non-data intents -> TEXT_ONLY
        if intent in {"CONVERSATION", "UI_ACTION", "DOCUMENT_KNOWLEDGE_QUERY"}:
            return {
                "should_generate_chart": False,
                "decision": "TEXT_ONLY",
                "reason": f"Intent '{intent}' does not produce visualizable tabular data."
            }

        # 2. Check Explicit User Chart Request
        has_explicit_chart_req = any(kw in q_lower for kw in self.EXPLICIT_CHART_KEYWORDS)

        # 3. Empty Results -> TEXT_ONLY
        if row_count == 0:
            return {
                "should_generate_chart": False,
                "decision": "TEXT_ONLY",
                "reason": "Query returned zero rows."
            }

        # 4. Count / Single-value / Single-row check
        is_single_val_query = any(re.search(pat, q_lower) for pat in self.COUNT_SINGLE_VALUE_PATTERNS)
        if (row_count == 1 or is_single_val_query) and not has_explicit_chart_req:
            # If single row with 1 or 2 numeric columns, check if KPI Card or text
            if row_count == 1 and len(cols) <= 2:
                return {
                    "should_generate_chart": False,
                    "decision": "KPI_CARD",
                    "reason": "Single value / metric lookup result."
                }
            return {
                "should_generate_chart": False,
                "decision": "TEXT_ONLY",
                "reason": "Single value / single row query does not require a full chart."
            }

        # 5. Threshold check: Auto chart requires >= 3 categories / rows unless explicitly requested
        if row_count < 3 and not has_explicit_chart_req:
            return {
                "should_generate_chart": False,
                "decision": "TABLE_ONLY",
                "reason": f"Result set contains {row_count} rows (< 3 auto-chart threshold)."
            }

        # 6. Chart Type Selection Logic
        
        # Check time series columns or query terms
        has_time_col = any(c.lower() in self.TIME_SERIES_KEYWORDS for c in cols)
        has_time_query = any(kw in q_lower for kw in self.TIME_SERIES_KEYWORDS)

        if has_time_col or has_time_query:
            return {
                "should_generate_chart": True,
                "decision": "LINE_CHART",
                "reason": "Time series / trend data identified."
            }

        # Check composition / pie chart terms
        has_composition_kw = any(kw in q_lower for kw in self.COMPOSITION_KEYWORDS)
        if has_composition_kw and row_count <= 7:
            return {
                "should_generate_chart": True,
                "decision": "PIE_CHART",
                "reason": "Composition / distribution data identified."
            }

        # Default for multi-category ranking & comparisons (>= 3 rows) -> BAR_CHART
        return {
            "should_generate_chart": True,
            "decision": "BAR_CHART",
            "reason": "Category comparison / ranking query with sufficient rows."
        }

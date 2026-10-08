"""
CLARIUS Backend - Consolidated Analytics Domain Service

Single cohesive service handling intelligent visualization decisions,
deterministic Apache ECharts config generation, and AI analytical insights synthesis.
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
        "comparison graph", "bar chart", "line chart", "pie chart", "scatter", "scatter plot"
    }

    TIME_SERIES_KEYWORDS = {"date", "month", "year", "quarter", "daily", "monthly", "yearly", "quarterly", "trend", "over time"}
    RANKING_KEYWORDS = {"top", "best", "worst", "lowest", "highest", "ranking", "compare", "comparison", "by region", "by category", "by product", "by department", "versus", "vs"}
    COMPOSITION_KEYWORDS = {"share", "percentage", "proportion", "breakdown", "distribution", "portion"}
    CORRELATION_KEYWORDS = {"relationship", "correlation", "versus", "vs", "scatter", "against"}

    def __init__(self):
        self.ollama = ollama_client

    def normalize_results(
        self,
        records: List[Dict[str, Any]],
        sub_intent: str,
        user_query: str
    ) -> List[Dict[str, Any]]:
        """
        Normalize results: perform semantic deduplication for entity lookups
        and prune redundant filter columns when explicitly specified by the user.
        """
        if not records:
            return []

        q_lower = user_query.strip().lower()
        cleaned_records = list(records)

        # 1. Semantic Deduplication for Entity Lookups
        if sub_intent == "ENTITY_LOOKUP" or any(kw in q_lower for kw in ["fetch", "find", "list", "show", "get"]):
            seen = set()
            unique_records = []
            for r in cleaned_records:
                # Key based on string values of row items
                row_key = tuple(str(v).strip().lower() for k, v in r.items())
                if row_key not in seen:
                    seen.add(row_key)
                    unique_records.append(r)
            cleaned_records = unique_records

        # 2. Smart Redundant Column Pruning (e.g. location='Chennai' when user explicitly queried 'in Chennai')
        if len(cleaned_records) > 0 and len(cleaned_records[0].keys()) > 1:
            first_row = cleaned_records[0]
            cols = list(first_row.keys())

            # Detect location/city columns
            loc_cols = [c for c in cols if c.lower() in {"location", "city", "branch_location", "address_city", "state", "region"}]
            for loc_col in loc_cols:
                # Check if every row has the identical location value
                loc_values = set(str(r.get(loc_col, "")).strip().lower() for r in cleaned_records)
                if len(loc_values) == 1:
                    single_val = list(loc_values)[0]
                    # Check if user explicitly mentioned this location in their query
                    if single_val and single_val in q_lower and len(cols) > 1:
                        # Omit redundant column if entity columns (like store_name, customer_name) exist
                        entity_cols = [c for c in cols if c != loc_col]
                        if entity_cols:
                            pruned = []
                            for r in cleaned_records:
                                new_r = {k: v for k, v in r.items() if k != loc_col}
                                pruned.append(new_r)
                            cleaned_records = pruned
                            break

        return cleaned_records

    def evaluate_visualization(
        self,
        user_query: str,
        intent: str,
        sql_results: List[Dict[str, Any]],
        columns: Optional[List[str]] = None,
        sub_intent: str = "ENTITY_LOOKUP"
    ) -> Dict[str, Any]:
        """
        Evaluate visualization suitability based on query intent, sub-intent, and result set metrics.
        Never generates charts for simple entity lookups, record details, or document RAG.
        Returns both decision (TABLE_ONLY, KPI_CARD, TEXT_ONLY, BAR_CHART, LINE_CHART, PIE_CHART, SCATTER)
        and presentation_mode (TABLE, KPI_CARD, TEXT, CHART_AND_TABLE).
        """
        q_lower = user_query.strip().lower()
        cols = columns or (list(sql_results[0].keys()) if sql_results else [])
        row_count = len(sql_results)

        # 1. Non-visual intents or empty results -> TEXT_ONLY
        if intent in {"CONVERSATION", "UI_ACTION", "DOCUMENT_KNOWLEDGE_QUERY"} or row_count == 0:
            return {"should_generate_chart": False, "decision": "TEXT_ONLY", "presentation_mode": "TEXT", "reason": "Non-visual intent or empty results."}

        has_explicit = any(kw in q_lower for kw in self.EXPLICIT_CHART_KEYWORDS)
        
        def is_num(v):
            if isinstance(v, (int, float)):
                return True
            if isinstance(v, str):
                cleaned = v.replace(',', '').replace('$', '').replace('₹', '').strip()
                try:
                    float(cleaned)
                    return True
                except ValueError:
                    return False
            return False

        numeric_cols = [c for c in cols if any(is_num(r.get(c)) for r in sql_results[:5])]

        # 2. Single scalar metric -> KPI_CARD (unless explicit chart requested)
        if row_count == 1 and len(cols) <= 2 and not has_explicit:
            return {"should_generate_chart": False, "decision": "KPI_CARD", "presentation_mode": "KPI_CARD", "reason": "Single metric scalar result."}

        # 3. Correlation / Relationship -> SCATTER PLOT
        has_correlation = any(kw in q_lower for kw in self.CORRELATION_KEYWORDS)
        if has_correlation and len(numeric_cols) >= 2:
            return {"should_generate_chart": True, "decision": "SCATTER", "presentation_mode": "CHART_AND_TABLE", "reason": "Metric correlation requested."}

        # 4. Temporal Trend -> LINE_CHART
        has_time_col = any(c.lower() in self.TIME_SERIES_KEYWORDS or "date" in c.lower() or "time" in c.lower() or "month" in c.lower() or "year" in c.lower() for c in cols)
        has_time_kw = any(kw in q_lower for kw in self.TIME_SERIES_KEYWORDS) or sub_intent == "TREND"
        if (has_time_kw or has_time_col) and (has_explicit or intent == "ANALYTICS_QUERY" or sub_intent == "TREND" or "monthly" in q_lower or "yearly" in q_lower or "daily" in q_lower or "trend" in q_lower):
            return {"should_generate_chart": True, "decision": "LINE_CHART", "presentation_mode": "CHART_AND_TABLE", "reason": "Temporal trend analysis identified."}

        # 5. Composition / Share -> PIE_CHART
        has_comp_kw = any(kw in q_lower for kw in self.COMPOSITION_KEYWORDS) or sub_intent == "DISTRIBUTION"
        if (has_comp_kw or "pie" in q_lower) and row_count <= 7 and len(numeric_cols) >= 1:
            return {"should_generate_chart": True, "decision": "PIE_CHART", "presentation_mode": "CHART_AND_TABLE", "reason": "Composition share identified."}

        # 6. Ranking / Comparison -> BAR_CHART (only if numeric measure column exists)
        has_ranking_kw = any(kw in q_lower for kw in self.RANKING_KEYWORDS) or sub_intent in {"RANKING", "AGGREGATION", "COMPARISON"}
        if (has_ranking_kw or (has_explicit and "pie" not in q_lower) or intent == "ANALYTICS_QUERY") and len(cols) >= 2 and row_count >= 2 and len(numeric_cols) >= 1:
            return {"should_generate_chart": True, "decision": "BAR_CHART", "presentation_mode": "CHART_AND_TABLE", "reason": "Category ranking or comparison identified."}

        # 7. Explicit chart request fallback if specified and numeric metrics exist
        if has_explicit and len(numeric_cols) >= 1:
            return {"should_generate_chart": True, "decision": "BAR_CHART", "presentation_mode": "CHART_AND_TABLE", "reason": "Explicit chart requested."}

        # 8. Simple Entity Lookup & Record Detail -> TABLE_ONLY (No Chart)
        if (sub_intent in {"ENTITY_LOOKUP", "RECORD_DETAIL"} or any(kw in q_lower for kw in ["fetch", "list", "find", "get", "show available", "where is"])) and not has_explicit:
            return {"should_generate_chart": False, "decision": "TABLE_ONLY", "presentation_mode": "TABLE", "reason": "Simple entity lookup query."}

        # 9. DEFAULT FOR ALL OTHER STRUCTURED QUERIES -> TABLE_ONLY
        return {"should_generate_chart": False, "decision": "TABLE_ONLY", "presentation_mode": "TABLE", "reason": "Tabular data lookup."}

    def generate_chart_config(self, user_query: str, sql_query: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate Apache ECharts configuration dictionary deterministically or via LLM with empty chart protection."""
        if not records or len(records) < 2:
            return {}

        # Attempt fast deterministic ECharts construction first
        det_config = self._build_deterministic_chart(user_query, records)
        if det_config:
            return det_config

        # Fallback to LLM for complex prompts
        records_sample = json.dumps(records[:10])
        system_prompt, user_prompt = PromptBuilder.build_echarts_config_prompt(user_query, sql_query, records_sample)

        try:
            raw_output = self.ollama.generate(prompt=user_prompt, system_prompt=system_prompt, purpose="chart generation")
            match = re.search(r"```json(.*?)```", raw_output, re.DOTALL | re.IGNORECASE)
            json_text = match.group(1).strip() if match else raw_output.strip()
            config = json.loads(json_text)
            
            # Empty chart protection check
            if not config.get("series") or not isinstance(config["series"], list) or len(config["series"]) == 0:
                return {}
            return config
        except Exception as e:
            logger.error(f"ECharts generation fallback triggered: {str(e)}")
            return {}

    def _build_deterministic_chart(self, user_query: str, records: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Construct fast deterministic ECharts options from schema with numeric data variation protection."""
        if not records or len(records) < 2:
            return None

        cols = list(records[0].keys())
        if len(cols) < 2:
            return None

        q_lower = user_query.lower()
        dim_col = cols[0]
        val_col = None

        # Identify numeric column for yAxis
        for c in cols:
            if any(isinstance(r.get(c), (int, float)) for r in records[:5]):
                val_col = c
                break

        # Protect against building empty charts for non-numeric datasets
        if not val_col:
            return None

        # Identify label/dimension column for xAxis
        for c in cols:
            if c != val_col and any(isinstance(r.get(c), str) for r in records[:5]):
                dim_col = c
                break

        x_data = [str(r.get(dim_col, "")) for r in records[:12]]
        y_data = [float(r.get(val_col, 0) or 0) for r in records[:12]]

        # Protect against flat / zero variation datasets (empty charts)
        if all(v == 0 for v in y_data) or len(set(y_data)) <= 1:
            return None

        is_line = any(kw in q_lower for kw in self.TIME_SERIES_KEYWORDS) or "date" in dim_col.lower() or "time" in dim_col.lower()
        is_pie = any(kw in q_lower for kw in self.COMPOSITION_KEYWORDS) or "pie" in q_lower

        if is_pie:
            pie_data = [{"name": str(r.get(dim_col, "")), "value": float(r.get(val_col, 0) or 0)} for r in records[:7]]
            return {
                "title": {"text": f"{val_col.replace('_', ' ').title()} Breakdown", "textStyle": {"color": "#f8fafc", "fontSize": 13}},
                "tooltip": {"trigger": "item"},
                "series": [{"type": "pie", "radius": "60%", "data": pie_data}]
            }

        chart_type = "line" if is_line else "bar"
        has_long_labels = any(len(str(x)) > 7 for x in x_data) or len(x_data) > 5
        return {
            "title": {"text": f"{val_col.replace('_', ' ').title()} by {dim_col.replace('_', ' ').title()}", "textStyle": {"color": "#f8fafc", "fontSize": 14}},
            "tooltip": {"trigger": "axis"},
            "grid": {"left": "3%", "right": "4%", "bottom": "14%", "top": "16%", "containLabel": True},
            "xAxis": {
                "type": "category",
                "data": x_data,
                "axisLine": {"lineStyle": {"color": "#64748b"}},
                "axisLabel": {
                    "interval": 0,
                    "rotate": 25 if has_long_labels else 0,
                    "color": "#94a3b8",
                    "fontSize": 12
                }
            },
            "yAxis": {"type": "value", "axisLine": {"lineStyle": {"color": "#64748b"}}, "splitLine": {"lineStyle": {"color": "#1e293b"}}},
            "series": [{
                "name": val_col.replace('_', ' ').title(),
                "type": chart_type,
                "smooth": is_line,
                "data": y_data,
                "itemStyle": {"color": "#3b82f6" if is_line else "#10b981"}
            }]
        }

    def explain_analytics(self, user_query: str, sql: str, records: List[Dict[str, Any]], intent: str) -> str:
        """Synthesize natural language business explanation for query results."""
        if intent == "ANALYTICS_QUERY" and records:
            prompt = PromptBuilder.build_analytics_explanation_prompt(user_query, str(records[:10]))
            try:
                return self.ollama.generate(prompt=prompt, fast_mode=True, purpose="analytics")
            except Exception:
                pass

        return ResponseFormatter.format_analytics_explanation(user_query, sql, len(records), records)

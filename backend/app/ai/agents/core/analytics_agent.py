"""
CLARIUS Backend - Analytics Chart Visualization Agent

This agent analyzes query results and generates optimal Apache ECharts configuration
JSON templates offline (ADR-006).
"""

import json
import re
import logging
from typing import Dict, Any, List, Optional

from app.ai.llm.client import ollama_client

logger = logging.getLogger("clarius.agents.visualization")

class AnalyticsAgent:
    """Agent generating ECharts configurations based on data structure and user query."""
    
    def __init__(self):
        self.ollama = ollama_client

    def generate_chart_config(self, user_query: str, sql_query: str, data_samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Ask Ollama to choose chart type and return Apache ECharts options JSON."""
        # Define system prompt
        system_prompt = (
            "You are a Data Visualization and Apache ECharts expert.\n"
            "Given a user business question, the SQL query used to fetch data, and a sample of the resulting database records, "
            "generate a valid, complete Apache ECharts options dictionary.\n\n"
            "Rules:\n"
            "1. Output ONLY a valid JSON object matching the ECharts option format. Do not explain your choice.\n"
            "2. Make it look beautiful and modern (clean design, dark-mode ready, nice font hierarchy, clear tooltip).\n"
            "3. Choose the best chart type: 'bar', 'line', 'pie', etc. based on the data columns.\n"
            "4. Example structure:\n"
            "{\n"
            "  \"title\": { \"text\": \"Sales Trend\" },\n"
            "  \"tooltip\": { \"trigger\": \"axis\" },\n"
            "  \"xAxis\": { \"type\": \"category\", \"data\": [\"Jan\", \"Feb\"] },\n"
            "  \"yAxis\": { \"type\": \"value\" },\n"
            "  \"series\": [{ \"data\": [120, 200], \"type\": \"line\" }]\n"
            "}\n"
            "5. Inject actual data values and categories from the provided records samples into the xAxis.data and series.data arrays."
        )

        prompt = (
            f"User Question: '{user_query}'\n"
            f"SQL Query: '{sql_query}'\n"
            f"Fetched Data Records Sample: {json.dumps(data_samples[:10])}"
        )

        try:
            raw_output = self.ollama.generate(prompt=prompt, system_prompt=system_prompt)
            return self._parse_json_config(raw_output)
        except Exception as e:
            logger.error(f"Failed to generate ECharts config via LLM: {str(e)}", exc_info=True)
            # Fallback default simple bar config if generation fails
            return self._fallback_chart_config(data_samples)

    def _parse_json_config(self, text: str) -> Dict[str, Any]:
        """Extract and parse JSON block from LLM response."""
        # Find JSON code blocks if present
        match = re.search(r"```json(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(1).strip()
        else:
            match = re.search(r"```(.*?)```", text, re.DOTALL)
            if match:
                text = match.group(1).strip()
                
        # Parse clean text
        return json.loads(text.strip())

    def _fallback_chart_config(self, data_samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Produce a generic fallback ECharts configuration if LLM fails."""
        if not data_samples:
            return {}
            
        # Try to identify string/date column for X axis, and numerical column for Y axis
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

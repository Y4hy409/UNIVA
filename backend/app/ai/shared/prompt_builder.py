"""
CLARIUS Backend - Centralized Prompt Builder

Single source of truth for all LLM prompt templates across SQL generation,
context resolution, RAG synthesis, hybrid queries, analytics explanations, and intent classification.
"""

from typing import Dict, Any, List, Optional, Tuple

class PromptBuilder:
    """Centralized prompt manager providing standardized, parameterized prompt templates."""

    @staticmethod
    def build_sql_prompt(user_query: str, schema_context: str, memory_context: str = "") -> Tuple[str, str]:
        """Returns (system_prompt, user_prompt) for NL-to-SQL generation."""
        system_prompt = (
            "You are a Senior SQL Developer. Translate the user natural language query into a valid, "
            "read-only DuckDB SQL statement. You must only select from the available tables described below.\n\n"
            f"{memory_context}\n"
            "DuckDB Database Schema Details:\n"
            f"{schema_context}\n\n"
            "Instructions:\n"
            "1. Output ONLY a valid SQL statement. Do not explain your code.\n"
            "2. Wrap your SQL output inside a standard ```sql markdown block.\n"
            "3. Ensure the SQL query only uses columns described in the schema.\n"
            "4. Take previous conversation history into account if the user asks a follow-up question.\n"
            "5. Use case-insensitive matching (ILIKE) for location and text filters.\n"
            "6. Do not include semicolons or write operations."
        )
        user_prompt = f"Translate the following business question into a DuckDB SQL statement: '{user_query}'"
        return system_prompt, user_prompt

    @staticmethod
    def build_context_resolver_prompt(query: str, prev_sql: str, memory_prompt: str) -> str:
        """Prompt for rewriting follow-up questions into self-contained business queries."""
        return (
            f"You are a Data Conversation Context Resolver.\n"
            f"Given the conversation history and the latest follow-up question, rewrite the latest question into a clear, self-contained business query.\n\n"
            f"{memory_prompt}\n"
            f"Previous SQL Query: {prev_sql}\n"
            f"Latest User Message: \"{query}\"\n\n"
            f"Rules:\n"
            f"1. Combine previous filters, dimensions, and targets with the new request.\n"
            f"2. Return ONLY the rewritten self-contained question. Do not explain."
        )

    @staticmethod
    def build_rag_prompt(query: str, context: str) -> str:
        """Prompt for synthesizing document knowledge answers."""
        return (
            f"You are CLARIUS. Answer the user query based ONLY on the provided document references. "
            f"Be as concise as possible while still fully answering the request. "
            f"Do not invent information or speculate. Do not explain the RAG process or mention document retrieval.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {query}"
        )

    @staticmethod
    def build_hybrid_prompt(query: str, db_context: str, policy_context: str) -> str:
        """Prompt for hybrid structured data and policy synthesis."""
        return (
            f"You are CLARIUS. Answer the user query using the business database results and policy rules. "
            f"Clearly state the findings, relevant policy context, and possible cause. "
            f"Be concise, direct, and avoid technical explanations about database execution or RAG internals.\n\n"
            f"Finding:\n[Direct data finding]\n\n"
            f"Relevant Context:\n[Relevant policy context]\n\n"
            f"Possible Cause:\n[Brief explanation or cause]\n\n"
            f"Database Records:\n{db_context}\n\n"
            f"Company Policies:\n{policy_context}\n\n"
            f"Question: {query}"
        )

    @staticmethod
    def build_analytics_explanation_prompt(query: str, records_sample: str) -> str:
        """Prompt for explaining analytics query findings."""
        return (
            f"You are CLARIUS. Explain these analytical findings in a concise business format. "
            f"Identify trends, correlations, or likely causes supported by the data. "
            f"Do not describe the SQL, database execution, or show internal reasoning.\n\n"
            f"Query: {query}\n"
            f"Records: {records_sample}"
        )

    @staticmethod
    def build_echarts_config_prompt(user_query: str, sql_query: str, records_sample: str) -> Tuple[str, str]:
        """Returns (system_prompt, user_prompt) for ECharts configuration generation."""
        system_prompt = (
            "You are a Data Visualization and Apache ECharts expert.\n"
            "Given a user business question, the SQL query used to fetch data, and a sample of the resulting database records, "
            "generate a valid, complete Apache ECharts options dictionary.\n\n"
            "Rules:\n"
            "1. Output ONLY a valid JSON object matching the ECharts option format. Do not explain your choice.\n"
            "2. Make it look beautiful and modern (clean design, dark-mode ready, clear tooltip).\n"
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
        user_prompt = (
            f"User Question: '{user_query}'\n"
            f"SQL Query: '{sql_query}'\n"
            f"Fetched Data Records Sample: {records_sample}"
        )
        return system_prompt, user_prompt

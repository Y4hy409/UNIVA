"""
CLARIUS / UNIVA Backend - Centralized Prompt Builder

Single source of truth for all LLM prompt templates across SQL generation,
context resolution, Business Memory synthesis, Copilot simulations,
hybrid queries, analytics explanations, and intent classification.
"""

from typing import Dict, Any, List, Optional, Tuple
from app.domain.memory_models import ContextRetrievalResult


class PromptBuilder:
    """Centralized prompt manager providing standardized, parameterized prompt templates."""

    @staticmethod
    def build_sql_prompt(
        user_query: str,
        schema_context: str,
        memory_context: str = "",
        business_definitions: Optional[List[Any]] = None,
        analytical_artifacts: Optional[List[Any]] = None
    ) -> Tuple[str, str]:
        """Returns (system_prompt, user_prompt) for output-only NL-to-SQL generation."""
        sections = []

        if business_definitions:
            def_lines = ["Relevant Business Definitions:"]
            for bdef in business_definitions:
                formula_str = f" [Formula: {bdef.formula}]" if getattr(bdef, "formula", None) else ""
                def_lines.append(f"- {bdef.term}: {bdef.definition}{formula_str}")
            sections.append("\n".join(def_lines))

        if analytical_artifacts:
            art_lines = ["Relevant Analytical Artifacts:"]
            for art in analytical_artifacts[:2]:
                art_lines.append(f"- Previous SQL for '{art.query_text}': {art.generated_sql}")
            sections.append("\n".join(art_lines))

        if memory_context:
            sections.append(f"Conversation History Context:\n{memory_context}")

        context_block = ("\n\n" + "\n\n".join(sections) + "\n\n") if sections else "\n\n"

        system_prompt = (
            "Generate exactly one valid DuckDB SELECT/WITH query.\n"
            "Return SQL only. Do not provide explanations. Do not use markdown fences. Do not generate multiple queries.\n"
            "Use only tables and columns present in the supplied schema. Preserve all filters from the user's question. Do not invent columns or tables.\n"
            f"{context_block}"
            "Database Schema:\n"
            f"{schema_context}\n\n"
            "Rules:\n"
            "1. Use ONLY exact column and table names from the schema above.\n"
            "2. Preserve all filters from the user's question (e.g., location/city like 'Chennai' -> `WHERE city ILIKE '%Chennai%'` or `WHERE location ILIKE '%Chennai%'`). Never output an empty WHERE clause.\n"
            "3. If an approved business definition specifies a metric column or formula, adhere to that definition.\n"
            "4. For entity lookups (e.g. stores, customers, suppliers), use SELECT DISTINCT to avoid duplicates.\n"
            "5. For dirty numeric/currency columns: `COALESCE(TRY_CAST(REGEXP_REPLACE(CAST(col AS VARCHAR), '[^0-9.]', '', 'g') AS DOUBLE), 0)`.\n"
            "6. For date/month grouping: `STRFTIME(TRY_CAST(date_col AS TIMESTAMP), '%Y-%m')` or `EXTRACT(YEAR FROM TRY_CAST(date_col AS TIMESTAMP))`.\n"
            "7. DUCKDB DATE RULE: DuckDB's DATE() function accepts ONLY 1 parameter (e.g. `CAST(date_col AS DATE)`). Do NOT generate 2-parameter `DATE(col, 'modifier')`. Use `date_trunc('month', CAST(date_col AS DATE))` or `date_trunc('quarter', CAST(date_col AS DATE))`.\n"
            "8. COMPANY / BRAND ENTITY MATCHING: When a query asks about sales, revenue, or units of a company, supplier, or brand (e.g., 'Orbit Wires & Cables Corp', 'Lumina Lighting'), JOIN `products p ON sales_order_items.product_id = p.product_id` and match by product brand or primary brand keyword (`p.brand ILIKE '%Orbit%'` OR `p.product_name ILIKE '%Orbit%'`). Do NOT search product_name for full corporate suffixes like 'Wires & Cables Corp'.\n"
            "9. RELATIVE DATES & LATEST QUARTER: For relative date queries ('latest quarter', 'current quarter', 'last month'), anchor date filters against the dataset maximum date: `soi.order_date >= date_trunc('quarter', (SELECT MAX(order_date) FROM sales_order_items))` (or `sales_orders`) rather than `CURRENT_DATE`.\n"
            "10. Return ONLY the raw executable SQL query string. No explanations, no markdown ticks."
        )
        user_prompt = f"Question: {user_query}\nSQL:"
        return system_prompt, user_prompt

    @staticmethod
    def build_business_copilot_prompt(
        query: Optional[str] = None,
        context_result: Optional[ContextRetrievalResult] = None,
        database_data_sample: Optional[str] = None,
        user_request: Optional[str] = None
    ) -> str:
        """
        Builds structured prompt with strict priority hierarchy:
        CURRENT USER REQUEST > CURRENT VERIFIED DATA > VERIFIED MEMORY > DOCUMENT KNOWLEDGE > MODEL GENERAL KNOWLEDGE
        """
        effective_q = user_request or query or ""
        lines = [
            "You are UNIVA / CLARIUS, an enterprise AI Business Copilot.",
            "Synthesize verified analytical and business context to answer the user request.",
            "",
            "=== STRICT PRIORITY HIERARCHY ===",
            "1. CURRENT USER REQUEST",
            "2. CURRENT VERIFIED DATABASE DATA",
            "3. VERIFIED BUSINESS MEMORY & ANALYTICAL ARTIFACTS",
            "4. VERIFIED DOCUMENT KNOWLEDGE (POLICIES / SOPS)",
            "5. MODEL GENERAL KNOWLEDGE",
            "",
            f"=== 1. CURRENT USER REQUEST ===\n{effective_q}",
            ""
        ]

        if database_data_sample:
            lines.extend([
                "=== 2. CURRENT VERIFIED DATABASE DATA ===",
                database_data_sample,
                ""
            ])

        if context_result.business_definitions:
            def_items = [f"- {d.term}: {d.definition}" + (f" (Formula: {d.formula})" if d.formula else "") for d in context_result.business_definitions]
            lines.extend([
                "=== 3. RELEVANT APPROVED BUSINESS DEFINITIONS ===",
                "\n".join(def_items),
                ""
            ])

        if context_result.analytical_artifacts:
            art_items = [f"- Analysis: '{a.name}' (Dataset: {a.dataset_name}:v{a.dataset_version})\n  SQL: {a.generated_sql}\n  Summary: {a.summary}" for a in context_result.analytical_artifacts]
            lines.extend([
                "=== 4. RELEVANT ANALYTICAL ARTIFACTS ===",
                "\n".join(art_items),
                ""
            ])

        if context_result.decisions:
            dec_items = [f"- {d.title}: {d.content}" for d in context_result.decisions]
            lines.extend([
                "=== 5. RELEVANT APPROVED BUSINESS DECISIONS ===",
                "\n".join(dec_items),
                ""
            ])

        if context_result.user_preferences:
            pref_items = [f"- {k}: {v}" for k, v in context_result.user_preferences.items()]
            lines.extend([
                "=== 6. RELEVANT USER PREFERENCES ===",
                "\n".join(pref_items),
                ""
            ])

        if context_result.dataset_context:
            lines.extend([
                "=== 7. DATASET LINEAGE CONTEXT ===",
                f"Dataset: {context_result.dataset_context.get('primary_dataset', 'Unknown')} (v{context_result.dataset_context.get('version', 1)}) Status: {context_result.dataset_context.get('status', 'ACTIVE')}",
                ""
            ])

        lines.extend([
            "=== CONSTRAINTS & GROUNDING ===",
            "- Ground all factual statements in the provided verified data or memory.",
            "- Distinguish clearly between FACTS, DERIVED RESULTS, and RECOMMENDATIONS.",
            "- If the data does not support a claim or is ambiguous, explicitly state the limitation. NEVER guess.",
            "- Provide a clear, actionable, executive-ready response."
        ])

        return "\n".join(lines)

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
            "5. Inject actual data values and categories from the provided records samples into the xAxis.data and series.data arrays.\n"
            "6. Always set grid: { left: '3%', right: '4%', bottom: '14%', top: '16%', containLabel: true } so axis labels never get truncated.\n"
            "7. Set xAxis.axisLabel: { interval: 0, rotate: 25 } if categories have long text or multiple items, ensuring all bar names are fully visible."
        )
        user_prompt = (
            f"User Question: '{user_query}'\n"
            f"SQL Query: '{sql_query}'\n"
            f"Fetched Data Records Sample: {records_sample}"
        )
        return system_prompt, user_prompt

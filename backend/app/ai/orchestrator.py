import logging
from typing import Any, List, Mapping, Optional, Dict
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.llms import LLM
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.tools import Tool
from langchain_core.prompts import PromptTemplate

from app.ai.llm.client import ollama_client
from app.ai.agents.core.sql_agent import SQLAgent
from app.ai.agents.core.rag_agent import DocumentRetrievalAgent
from app.ai.agents.core.optimization_agent import QueryOptimizationAgent
from app.ai.agents.core.analytics_agent import AnalyticsAgent
from app.infrastructure.database import db_manager

logger = logging.getLogger("clarius.ai.orchestrator")

class OllamaLangChainLLM(LLM):
    """Custom LangChain LLM wrapper around CLARIUS's offline OllamaClient."""
    
    @property
    def _llm_type(self) -> str:
        return "clarius_ollama"
        
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        return ollama_client.generate(prompt=prompt)


class LangChainOrchestrator:
    """
    CLARIUS LangChain-based Agent Orchestrator.
    Handles Tool calling, Prompt orchestration, and Memory management across agents.
    """
    
    def __init__(self, db_conn = None):
        self.conn = db_conn or db_manager.get_connection()
        self.llm = OllamaLangChainLLM()
        self.sql_agent = SQLAgent(db_conn=self.conn)
        self.rag_agent = DocumentRetrievalAgent()
        self.optimization_agent = QueryOptimizationAgent(self.conn)
        self.analytics_agent = AnalyticsAgent()
        
        # Define tools mapped to respective agents
        self.tools = [
            Tool(
                name="business_database_query",
                func=self._run_db_query,
                description=(
                    "Use this tool to search, compute, and query structured business data (sales, revenue, orders, inventory, etc.). "
                    "Input should be a clear natural language question."
                )
            ),
            Tool(
                name="company_knowledge_search",
                func=self._run_rag_search,
                description=(
                    "Use this tool to retrieve information from unstructured company manuals, PDFs, handbooks, SOPs, and policies. "
                    "Input should be a search query."
                )
            ),
            Tool(
                name="chart_visualization_generator",
                func=self._run_chart_generator,
                description=(
                    "Use this tool to generate a beautiful Apache ECharts visualization layout config for the query results. "
                    "Input should be a JSON-formatted string containing: {'query': '...', 'sql': '...', 'data': [...]}"
                )
            )
        ]
        
        # Setup Agent executor
        self.prompt = PromptTemplate.from_template(
            "You are CLARIUS, a fast, precise, local-first AI Business Copilot for MSMEs.\n"
            "Answer the user query by selecting the most appropriate tool.\n\n"
            "Tools available:\n"
            "{tools}\n\n"
            "Tool names are: {tool_names}\n\n"
            "To answer, use this format:\n"
            "Thought: Do I need to use a tool? Yes\n"
            "Action: the action to take, should be one of [{tool_names}]\n"
            "Action Input: the input to the action\n"
            "Observation: the result of the action\n"
            "... (this Thought/Action/Action Input/Observation can repeat N times)\n"
            "Thought: I now know the final answer\n"
            "Final Answer: the final answer to the original input question\n\n"
            "Begin!\n\n"
            "Question: {input}\n"
            "Thought: {agent_scratchpad}"
        )
        
        self.agent = create_react_agent(self.llm, self.tools, self.prompt)
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            handle_parsing_errors=True,
            max_iterations=5,
            verbose=True
        )

    def _run_db_query(self, question: str) -> str:
        """SQL Agent Tool wrapper."""
        try:
            res = self.sql_agent.process_natural_language_query(question)
            if res.get("success", False):
                # Apply optimizer if query is direct SQL
                sql = res.get("sql")
                if sql:
                    optimized_sql = self.optimization_agent.optimize_query(sql)
                    res["sql"] = optimized_sql
                return str(res)
            return f"Error querying database: {res.get('error')}"
        except Exception as e:
            return f"Database query failed: {str(e)}"

    def _run_rag_search(self, query: str) -> str:
        """RAG Agent Tool wrapper."""
        try:
            passages = self.rag_agent.retrieve_passages(query)
            if not passages:
                return "No company handbook or document references found."
            formatted = []
            for p in passages:
                formatted.append(f"Document: {p['metadata'].get('title', 'Doc')}\nContent: {p['content']}")
            return "\n\n".join(formatted)
        except Exception as e:
            return f"Document search failed: {str(e)}"

    def _run_chart_generator(self, input_str: str) -> str:
        """Visualization Engine Tool wrapper."""
        import json
        try:
            params = json.loads(input_str)
            query = params.get("query", "")
            sql = params.get("sql", "")
            data = params.get("data", [])
            chart_config = self.analytics_agent.generate_chart_config(query, sql, data)
            return json.dumps(chart_config)
        except Exception as e:
            return f"Failed to generate visualization config: {str(e)}"

    def execute(self, user_query: str) -> str:
        """Coordinate query routing and execution across CLARIUS agents."""
        # Check cache/reuse before running full LangChain chain
        try:
            cached = self.conn.execute(
                "SELECT result FROM queries WHERE query_text = ? AND status = 'success' ORDER BY created_at DESC LIMIT 1",
                (user_query,)
            ).fetchone()
            if cached:
                logger.info(f"Orchestrator returning cached response for: {user_query}")
                return cached[0]
        except Exception as e:
            logger.error(f"Failed to check cache: {str(e)}")

        try:
            # Detect follow-up reformulation
            reformulated_query = self.sql_agent.reformulate_query(user_query)
            response = self.executor.invoke({"input": reformulated_query})
            final_answer = response.get("output", "").strip()
            return final_answer
        except Exception as e:
            logger.error(f"Orchestrator execution error: {str(e)}")
            return f"Failed to process request: {str(e)}"

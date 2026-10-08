import json
import logging
from typing import Any, List, Optional, Dict
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.llms import LLM
try:
    from langchain.agents import AgentExecutor, create_react_agent
except ImportError:
    try:
        from langchain.agents.react.agent import create_react_agent
        from langchain.agents.agent import AgentExecutor
    except ImportError:
        AgentExecutor = None
        create_react_agent = None

from langchain_core.tools import Tool
from langchain_core.prompts import PromptTemplate

from app.ai.llm.client import ollama_client
from app.ai.services.sql_service import SQLService
from app.ai.services.analytics_service import AnalyticsService
from app.ai.agents.core.rag_agent import DocumentRetrievalAgent
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
    Handles Tool calling, Prompt orchestration, and Memory management across domain services.
    """
    
    def __init__(self, db_conn = None):
        self.conn = db_conn or db_manager.get_connection()
        self.llm = OllamaLangChainLLM()
        self.sql_service = SQLService(db_conn=self.conn)
        self.rag_agent = DocumentRetrievalAgent()
        self.analytics_service = AnalyticsService()
        self._memory_cache: Dict[str, str] = {}
        
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
        
        self.prompt = PromptTemplate.from_template(
            "You are CLARIUS, a fast, precise, local-first AI Business Copilot for MSMEs.\n"
            "Answer the user query by selecting the most appropriate tool.\n\n"
            "CRITICAL TOOL SELECTION RULES:\n"
            "1. For numerical sales figures, product sales, quarterly performance, orders, inventory levels, revenue, and customer metrics, ONLY use 'business_database_query'. Do NOT fallback to 'company_knowledge_search' for numerical database queries.\n"
            "2. ONLY use 'company_knowledge_search' for questions about company policies, SOPs, HR manuals, credit terms, and compliance guidelines.\n\n"
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
        
        if create_react_agent and AgentExecutor:
            try:
                self.agent = create_react_agent(self.llm, self.tools, self.prompt)
                self.executor = AgentExecutor(
                    agent=self.agent,
                    tools=self.tools,
                    handle_parsing_errors=True,
                    max_iterations=5,
                    verbose=True
                )
            except Exception:
                self.agent = None
                self.executor = None
        else:
            self.agent = None
            self.executor = None

    def _run_db_query(self, question: str) -> str:
        """SQL Tool wrapper."""
        try:
            res = self.sql_service.process_query(question)
            if res.get("success", False):
                return str(res)
            return f"DATABASE QUERY ERROR: {res.get('error')}. Note: Do NOT attempt to answer numerical business data questions using company_knowledge_search document search."
        except Exception as e:
            return f"DATABASE QUERY FAILURE: {str(e)}. Note: Do NOT attempt to answer numerical business data questions using company_knowledge_search document search."

    def _run_rag_search(self, query: str) -> str:
        """RAG Tool wrapper."""
        try:
            passages = self.rag_agent.retrieve_passages(query)
            if not passages:
                return "No company handbook or document references found."
            formatted = [f"Document: {p['metadata'].get('title', 'Doc')}\nContent: {p['content']}" for p in passages]
            return "\n\n".join(formatted)
        except Exception as e:
            return f"Document search failed: {str(e)}"

    def _run_chart_generator(self, input_str: str) -> str:
        """Visualization Engine Tool wrapper."""
        try:
            params = json.loads(input_str)
            query = params.get("query", "")
            sql = params.get("sql", "")
            data = params.get("data", [])
            chart_config = self.analytics_service.generate_chart_config(query, sql, data)
            return json.dumps(chart_config)
        except Exception as e:
            return f"Failed to generate visualization config: {str(e)}"

    def execute(self, user_query: str) -> str:
        """Coordinate query routing and execution with strict source isolation."""
        from app.ai.router import FastIntentRouter

        if user_query in self._memory_cache:
            logger.info(f"[ORCHESTRATOR] Returning in-memory response for: '{user_query}'")
            return self._memory_cache[user_query]

        route = FastIntentRouter.classify(user_query)
        intent = route.get("intent", "STRUCTURED_DATA_QUERY")
        logger.info(f"[ORCHESTRATOR] Classified query: '{user_query}' -> Intent: {intent}")

        # 1. Document Knowledge Queries -> RAG ONLY (No SQL)
        if intent == "DOCUMENT_KNOWLEDGE_QUERY":
            logger.info(f"[ORCHESTRATOR] Executing RAG document search ONLY for intent {intent}")
            res = self._run_rag_search(user_query)
            if res:
                self._memory_cache[user_query] = res
            return res

        # 2. Structured Business Data & Analytics Queries -> SQL ONLY (No RAG fallback)
        if intent in {"STRUCTURED_DATA_QUERY", "ANALYTICS_QUERY"}:
            logger.info(f"[ORCHESTRATOR] Executing Business SQL query ONLY for intent {intent}")
            res_str = self._run_db_query(user_query)
            if "DATABASE QUERY ERROR" in res_str or "DATABASE QUERY FAILURE" in res_str:
                final_answer = "Data unavailable: I could not retrieve the requested information from the business database."
            else:
                final_answer = res_str
            if final_answer:
                self._memory_cache[user_query] = final_answer
            return final_answer

        # 3. Hybrid / General Queries -> Executor loop
        try:
            if self.executor:
                response = self.executor.invoke({"input": user_query})
                final_answer = response.get("output", "").strip()
            else:
                final_answer = self._run_db_query(user_query)
            if final_answer:
                self._memory_cache[user_query] = final_answer
            return final_answer
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Execution error: {str(e)}")
            return f"Data unavailable: I could not retrieve the requested information from the business database."

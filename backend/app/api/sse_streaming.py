"""
CLARIUS Backend - SSE Analytics Streaming

This module implements Server-Sent Events (SSE) streaming for natural language query execution,
displaying live updates of progress stages and returning chart options (ADR-006).
Refactored to use consolidated SQLService, AnalyticsService, and memory utilities.
"""

import json
import asyncio
import logging
from typing import Optional
import duckdb
from fastapi import APIRouter, Depends, Query
from sse_starlette.sse import EventSourceResponse

from app.infrastructure.database import get_db
from app.ai.services.sql_service import SQLService
from app.ai.services.analytics_service import AnalyticsService
from app.ai.shared.memory_utils import memory_manager, ContextResolver
from app.ai.shared.prompt_builder import PromptBuilder
from app.ai.shared.response_formatter import ResponseFormatter

router = APIRouter(prefix="/analytics/stream", tags=["analytics"])

logger = logging.getLogger("clarius.analytics.stream")

@router.get("")
async def stream_query_results(
    query_text: str = Query(..., alias="q"),
    conversation_id: Optional[str] = Query(None, alias="conversation_id"),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """Convert natural language to SQL with real-time SSE stage execution updates and persistent context resolution."""
    
    async def event_generator():
        from app.ai.router import FastIntentRouter
        from app.ai.agents.core.rag_agent import DocumentRetrievalAgent
        from app.ai.llm.client import ollama_client
        
        session = memory_manager.get_session(conversation_id)
        
        # 1. Conversation Context Resolver
        context_resolution = ContextResolver.resolve_context(query_text, session)
        effective_query = context_resolution["resolved_query"]
        logger.info(f"SSE session [{session.conversation_id}] query: '{query_text}' -> resolved: '{effective_query}'")

        # 2. Classify Intent
        route = FastIntentRouter.classify(effective_query)
        intent = route["intent"]
        
        # 3. Handle Conversation
        if intent == "CONVERSATION":
            resp_text = route.get("response", "Hello! How can I assist with your business data today?")
            session.record_turn(user_query=query_text, intent=intent, response_text=resp_text)
            yield {
                "event": "completed",
                "data": json.dumps({
                    "generated_sql": "",
                    "explanation": resp_text,
                    "columns": [],
                    "results": [],
                    "chart_spec": "{}"
                })
            }
            return

        # 4. Handle UI Actions
        if intent == "UI_ACTION":
            resp_text = f"Navigating to {route.get('ui_action').replace('navigate_', '')} screen..."
            session.record_turn(user_query=query_text, intent=intent, response_text=resp_text)
            yield {
                "event": "completed",
                "data": json.dumps({
                    "generated_sql": "",
                    "explanation": resp_text,
                    "columns": [],
                    "results": [],
                    "chart_spec": "{}",
                    "ui_action": route.get("ui_action")
                })
            }
            return

        # 5. Handle Document Knowledge Queries (RAG)
        if intent == "DOCUMENT_KNOWLEDGE_QUERY":
            yield {
                "event": "stage",
                "data": json.dumps({"stage": "knowledge_retrieval", "message": "Searching company knowledge base..."})
            }
            await asyncio.sleep(0.2)
            
            rag_agent = DocumentRetrievalAgent()
            passages = rag_agent.retrieve_passages(effective_query)
            
            if not passages:
                no_doc_msg = "The requested information could not be found in the available company documents."
                session.record_turn(user_query=query_text, intent=intent, response_text=no_doc_msg)
                yield {
                    "event": "completed",
                    "data": json.dumps({
                        "generated_sql": "",
                        "explanation": no_doc_msg,
                        "columns": [],
                        "results": [],
                        "chart_spec": "{}"
                    })
                }
                return
                
            yield {
                "event": "stage",
                "data": json.dumps({"stage": "answer_synthesis", "message": "Synthesizing answer from retrieved documents..."})
            }
            await asyncio.sleep(0.2)
            
            context = "\n\n".join([f"Document: {p['metadata'].get('title', 'Policy')}\nContent: {p['content']}" for p in passages])
            prompt = PromptBuilder.build_rag_prompt(effective_query, context)
            explanation = ollama_client.generate(prompt=prompt)
            session.record_turn(user_query=query_text, intent=intent, response_text=explanation, documents=passages)
            
            yield {
                "event": "completed",
                "data": json.dumps({
                    "generated_sql": "",
                    "explanation": explanation,
                    "columns": [],
                    "results": [],
                    "chart_spec": "{}"
                })
            }
            return

        # 6. Handle Hybrid Queries
        if intent == "HYBRID_BUSINESS_QUERY":
            yield {
                "event": "stage",
                "data": json.dumps({"stage": "schema_discovery", "message": "Executing hybrid data and policy checks..."})
            }
            await asyncio.sleep(0.2)
            
            sql_service = SQLService(db_conn=db)
            sql_res = sql_service.process_query(effective_query, session.get_formatted_memory_prompt())
            records = sql_res.get("data", [])
            sql = sql_res.get("sql", "")

            rag_agent = DocumentRetrievalAgent()
            passages = rag_agent.retrieve_passages(effective_query)
            
            yield {
                "event": "stage",
                "data": json.dumps({"stage": "answer_synthesis", "message": "Merging database records and policy documents..."})
            }
            await asyncio.sleep(0.2)
            
            db_context = str(records[:10]) if records else "No structured data matched."
            policy_context = "\n\n".join([f"Document: {p['metadata'].get('title', 'Policy')}\nContent: {p['content']}" for p in passages]) if passages else "No policy documents matched."
            
            prompt = PromptBuilder.build_hybrid_prompt(effective_query, db_context, policy_context)
            explanation = ollama_client.generate(prompt=prompt)
            columns = list(records[0].keys()) if records else []
            
            analytics_service = AnalyticsService()
            viz_eval = analytics_service.evaluate_visualization(effective_query, intent, records, columns)
            chart_config = analytics_service.generate_chart_config(effective_query, sql, records) if viz_eval["should_generate_chart"] else {}

            session.record_turn(
                user_query=query_text,
                intent=intent,
                response_text=explanation,
                sql=sql,
                results=records,
                chart_config=chart_config,
                documents=passages
            )

            yield {
                "event": "completed",
                "data": json.dumps({
                    "generated_sql": sql,
                    "explanation": explanation,
                    "columns": columns,
                    "results": records[:100],
                    "chart_spec": json.dumps(chart_config) if chart_config else "{}"
                })
            }
            return

        # 7. Default Structured Data & Analytics Queries
        yield {
            "event": "stage",
            "data": json.dumps({"stage": "schema_discovery", "message": "Analyzing database schemas..."})
        }
        await asyncio.sleep(0.2)
        
        sql_service = SQLService(db_conn=db)
        schema_context = sql_service.discover_schemas()
        
        if not schema_context:
            yield {
                "event": "error",
                "data": json.dumps({"message": "No database tables found. Please import some data first."})
            }
            return

        yield {
            "event": "stage",
            "data": json.dumps({"stage": "sql_generation", "message": "Generating DuckDB SQL query..."})
        }
        await asyncio.sleep(0.2)
        
        sql_res = sql_service.process_query(effective_query, session.get_formatted_memory_prompt())
        if not sql_res.get("success", False):
            yield {
                "event": "error",
                "data": json.dumps({"message": f"Query execution failed: {sql_res.get('error')}"})
            }
            return

        sql = sql_res.get("sql", "")
        records = sql_res.get("data", [])
        columns = list(records[0].keys()) if records else []

        analytics_service = AnalyticsService()
        viz_eval = analytics_service.evaluate_visualization(effective_query, intent, records, columns)
        
        chart_config = {}
        if viz_eval["should_generate_chart"]:
            yield {
                "event": "stage",
                "data": json.dumps({"stage": "chart_generation", "message": "Generating ECharts visualization options..."})
            }
            await asyncio.sleep(0.2)
            chart_config = analytics_service.generate_chart_config(effective_query, sql, records)

        explanation = analytics_service.explain_analytics(effective_query, sql, records, intent)

        session.record_turn(
            user_query=query_text,
            intent=intent,
            response_text=explanation,
            sql=sql,
            results=records,
            chart_config=chart_config
        )

        yield {
            "event": "completed",
            "data": json.dumps({
                "generated_sql": sql,
                "explanation": explanation,
                "columns": columns,
                "results": records[:100],
                "chart_spec": json.dumps(chart_config) if chart_config else "{}"
            })
        }

    return EventSourceResponse(event_generator())

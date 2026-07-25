"""
CLARIUS Backend - SSE Analytics Streaming

This module implements Server-Sent Events (SSE) streaming for natural language query execution,
displaying live updates of progress stages and returning chart options (ADR-006).
"""

import json
import asyncio
import logging
import duckdb
from fastapi import APIRouter, Depends, Query
from sse_starlette.sse import EventSourceResponse

from app.infrastructure.database import get_db
from app.ai.agents.core.sql_agent import SQLAgent
from app.ai.agents.core.analytics_agent import AnalyticsAgent

router = APIRouter(prefix="/analytics/stream", tags=["analytics"])

logger = logging.getLogger("clarius.analytics.stream")

@router.get("")
async def stream_query_results(query_text: str = Query(..., alias="q"), db: duckdb.DuckDBPyConnection = Depends(get_db)):
    """Convert natural language to SQL with real-time SSE stage execution updates."""
    
    async def event_generator():
        from app.ai.router import FastIntentRouter
        from app.ai.agents.core.rag_agent import DocumentRetrievalAgent
        from app.ai.agents.core.communication_agent import CommunicationAgent
        from app.ai.llm.client import ollama_client
        
        # 1. Classify Intent
        route = FastIntentRouter.classify(query_text)
        intent = route["intent"]
        
        # 2. Handle Conversation
        if intent == "CONVERSATION":
            yield {
                "event": "completed",
                "data": json.dumps({
                    "generated_sql": "",
                    "explanation": route.get("response", "Hello!"),
                    "columns": [],
                    "results": [],
                    "chart_spec": "{}"
                })
            }
            return

        # 3. Handle UI Actions
        if intent == "UI_ACTION":
            yield {
                "event": "completed",
                "data": json.dumps({
                    "generated_sql": "",
                    "explanation": f"Navigating to {route.get('ui_action').replace('navigate_', '')} screen...",
                    "columns": [],
                    "results": [],
                    "chart_spec": "{}",
                    "ui_action": route.get("ui_action")
                })
            }
            return

        # 4. Handle Document Knowledge Queries (RAG)
        if intent == "DOCUMENT_KNOWLEDGE_QUERY":
            yield {
                "event": "stage",
                "data": json.dumps({"stage": "knowledge_retrieval", "message": "Searching company knowledge base..."})
            }
            await asyncio.sleep(0.5)
            
            rag_agent = DocumentRetrievalAgent()
            passages = rag_agent.retrieve_passages(query_text)
            
            if not passages:
                yield {
                    "event": "completed",
                    "data": json.dumps({
                        "generated_sql": "",
                        "explanation": "The requested information could not be found in the available company documents.",
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
            await asyncio.sleep(0.5)
            
            context = "\n\n".join([f"Document: {p['metadata'].get('title', 'Policy')}\nContent: {p['content']}" for p in passages])
            prompt = (
                f"You are CLARIUS. Answer the user query based ONLY on the provided document references:\n\n"
                f"Context:\n{context}\n\n"
                f"Question: {query_text}"
            )
            explanation = ollama_client.generate(prompt=prompt)
            
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

        # 5. Handle Hybrid Queries
        if intent == "HYBRID_BUSINESS_QUERY":
            yield {
                "event": "stage",
                "data": json.dumps({"stage": "schema_discovery", "message": "Executing hybrid data and policy checks..."})
            }
            await asyncio.sleep(0.5)
            
            sql_agent = SQLAgent(db_conn=db)
            schema_context = sql_agent.discover_schemas()
            
            # DB part
            records = []
            sql = ""
            if schema_context:
                try:
                    final_query = sql_agent.reformulate_query(query_text)
                    sql = sql_agent.generate_sql(final_query, schema_context)
                    sql = sql_agent.fix_column_names(sql)
                    sql = sql_agent.fix_date_and_year_queries(sql, final_query)
                    records = sql_agent.execute_query(sql)
                except Exception:
                    pass

            # RAG part
            rag_agent = DocumentRetrievalAgent()
            passages = rag_agent.retrieve_passages(query_text)
            
            yield {
                "event": "stage",
                "data": json.dumps({"stage": "answer_synthesis", "message": "Merging database records and policy documents..."})
            }
            await asyncio.sleep(0.5)
            
            db_context = str(records[:10]) if records else "No structured data matched."
            policy_context = "\n\n".join([f"Document: {p['metadata'].get('title', 'Policy')}\nContent: {p['content']}" for p in passages]) if passages else "No policy documents matched."
            
            prompt = (
                f"You are CLARIUS. Answer the user query using the business database results and policy rules.\n"
                f"Clearly state the data-derived facts, the policy rules, and your business interpretation.\n\n"
                f"Database Records:\n{db_context}\n\n"
                f"Company Policies:\n{policy_context}\n\n"
                f"Question: {query_text}"
            )
            explanation = ollama_client.generate(prompt=prompt)
            columns = list(records[0].keys()) if records else []
            
            yield {
                "event": "completed",
                "data": json.dumps({
                    "generated_sql": sql,
                    "explanation": explanation,
                    "columns": columns,
                    "results": records[:100],
                    "chart_spec": "{}"
                })
            }
            return

        # 6. Default Structured Data & Analytics Queries
        yield {
            "event": "stage",
            "data": json.dumps({"stage": "schema_discovery", "message": "Analyzing database schemas..."})
        }
        await asyncio.sleep(0.5)
        
        sql_agent = SQLAgent(db_conn=db)
        schema_context = sql_agent.discover_schemas()
        
        if not schema_context:
            yield {
                "event": "error",
                "data": json.dumps({"message": "No database tables found. Please import some data first."})
            }
            return

        cached_sql = None
        try:
            cached = db.execute(
                "SELECT generated_sql FROM queries WHERE query_text = ? AND status = 'success' ORDER BY created_at DESC LIMIT 1",
                (query_text,)
            ).fetchone()
            if cached:
                cached_sql = cached[0]
        except Exception:
            pass

        if cached_sql:
            sql = cached_sql
            logger.info(f"SSE Reusing cached SQL: {sql}")
        else:
            yield {
                "event": "stage",
                "data": json.dumps({"stage": "sql_generation", "message": "Generating DuckDB SQL query..."})
            }
            await asyncio.sleep(0.5)
            
            try:
                final_query = sql_agent.reformulate_query(query_text)
                sql = sql_agent.generate_sql(final_query, schema_context)
                sql = sql_agent.fix_column_names(sql)
                sql = sql_agent.fix_date_and_year_queries(sql, final_query)
                logger.info(f"SSE Generated SQL (after fixes): {sql}")
            except Exception as e:
                yield {
                    "event": "error",
                    "data": json.dumps({"message": f"SQL translation failed: {str(e)}"})
                }
                return

        yield {
            "event": "stage",
            "data": json.dumps({"stage": "sql_execution", "message": "Executing SQL query against DuckDB..."})
        }
        await asyncio.sleep(0.5)
        
        try:
            is_safe, error_msg = sql_agent.validate_sql_safety(sql)
            if not is_safe:
                yield {
                    "event": "error",
                    "data": json.dumps({"message": error_msg})
                }
                return
                
            db.execute(f"EXPLAIN {sql}")
            records = sql_agent.execute_query(sql)
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"message": f"Database execution failed: {str(e)}"})
            }
            return

        yield {
            "event": "stage",
            "data": json.dumps({"stage": "chart_generation", "message": "Generating ECharts visualization options..."})
        }
        await asyncio.sleep(0.5)
        
        viz_agent = AnalyticsAgent()
        chart_config = viz_agent.generate_chart_config(query_text, sql, records)

        columns = list(records[0].keys()) if records else []
        comm_agent = CommunicationAgent()
        
        if intent == "ANALYTICS_QUERY":
            # Synthesize analytics reasoning using Qwen
            prompt = (
                f"You are CLARIUS. Explain these analytical findings in a concise business format (Finding, Evidence, Possible Cause, Recommended Action):\n\n"
                f"Query: {query_text}\n"
                f"SQL: {sql}\n"
                f"Records: {str(records[:10])}"
            )
            explanation = ollama_client.generate(prompt=prompt)
        else:
            explanation = comm_agent.format_analytics_explanation(query_text, sql, len(records))

        yield {
            "event": "completed",
            "data": json.dumps({
                "generated_sql": sql,
                "explanation": explanation,
                "columns": columns,
                "results": records[:100],
                "chart_spec": json.dumps(chart_config)
            })
        }

    return EventSourceResponse(event_generator())

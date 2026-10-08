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
from app.core.performance_logger import RequestTimer, set_current_timer

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
        timer = RequestTimer()
        set_current_timer(timer)
        timer.log("Request received")

        from app.ai.router import FastIntentRouter
        from app.ai.agents.core.rag_agent import DocumentRetrievalAgent
        from app.ai.llm.client import ollama_client
        
        session = memory_manager.get_session(conversation_id)
        
        # 1. Conversation Context Resolver
        timer.start_phase("Context resolution")
        context_resolution = ContextResolver.resolve_context(query_text, session)
        effective_query = context_resolution["resolved_query"]
        timer.end_phase("Context resolution", "Context resolution completed")
        logger.info(f"SSE session [{session.conversation_id}] query: '{query_text}' -> resolved: '{effective_query}'")

        # 2. Classify Intent
        timer.start_phase("Intent classification")
        route = FastIntentRouter.classify(effective_query)
        intent = route["intent"]
        sub_intent = route.get("sub_intent", "ENTITY_LOOKUP")
        timer.end_phase("Intent classification", "Intent classification completed")
        
        # 3. Handle Conversation
        if intent == "CONVERSATION":
            timer.log_skipped("RAG", "conversational intent")
            timer.log_skipped("Schema discovery", "conversational intent")
            timer.log_skipped("SQL generation", "conversational intent")
            timer.log_skipped("DuckDB query", "conversational intent")
            timer.log_skipped("Analytics", "conversational intent")
            
            resp_text = route.get("response", "Hello! How can I assist with your business data today?")
            timer.start_phase("Final response generation")
            session.record_turn(user_query=query_text, intent=intent, response_text=resp_text)
            persist_sse_turn(db, session.conversation_id, query_text, resp_text, intent)
            timer.end_phase("Final response generation", "Final response generated")
            
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
            timer.log("Response sent")
            timer.print_summary()
            return

        # 4. Handle UI Actions
        if intent == "UI_ACTION":
            timer.log_skipped("RAG", "ui action intent")
            timer.log_skipped("Schema discovery", "ui action intent")
            timer.log_skipped("SQL generation", "ui action intent")
            timer.log_skipped("DuckDB query", "ui action intent")
            timer.log_skipped("Analytics", "ui action intent")
            
            resp_text = f"Navigating to {route.get('ui_action').replace('navigate_', '')} screen..."
            timer.start_phase("Final response generation")
            session.record_turn(user_query=query_text, intent=intent, response_text=resp_text)
            persist_sse_turn(db, session.conversation_id, query_text, resp_text, intent)
            timer.end_phase("Final response generation", "Final response generated")
            
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
            timer.log("Response sent")
            timer.print_summary()
            return

        # 5. Handle Document Knowledge Queries (RAG)
        if intent == "DOCUMENT_KNOWLEDGE_QUERY":
            timer.log_skipped("Schema discovery", "document knowledge query")
            timer.log_skipped("SQL generation", "document knowledge query")
            timer.log_skipped("DuckDB query", "document knowledge query")
            timer.log_skipped("Analytics", "document knowledge query")
            
            yield {
                "event": "stage",
                "data": json.dumps({"stage": "knowledge_retrieval", "message": "Searching company knowledge base..."})
            }
            
            rag_agent = DocumentRetrievalAgent()
            passages = rag_agent.retrieve_passages(effective_query)
            
            if not passages:
                no_doc_msg = (
                    "No relevant documents found in the knowledge base for your query. "
                    "Please upload your business policy documents (PDF, Word, or text files) "
                    "via the Business Knowledge section first."
                )
                timer.start_phase("Final response generation")
                session.record_turn(user_query=query_text, intent=intent, response_text=no_doc_msg)
                persist_sse_turn(db, session.conversation_id, query_text, no_doc_msg, intent)
                timer.end_phase("Final response generation", "Final response generated")
                
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
                timer.log("Response sent")
                timer.print_summary()
                return
                
            yield {
                "event": "stage",
                "data": json.dumps({"stage": "answer_synthesis", "message": "Synthesizing answer from retrieved documents..."})
            }
            
            timer.start_phase("Context construction")
            context = "\n\n".join([f"Document: {p['metadata'].get('title', 'Policy')}\nContent: {p['content']}" for p in passages])
            prompt = PromptBuilder.build_rag_prompt(effective_query, context)
            timer.end_phase("Context construction", "Context construction completed")
            
            timer.start_phase("RAG answer synthesis")
            explanation = ollama_client.generate(prompt=prompt, purpose="final response")
            timer.end_phase("RAG answer synthesis", "Final response generated", summary_key="Final response generation")
            
            timer.start_phase("Response persistence")
            session.record_turn(user_query=query_text, intent=intent, response_text=explanation, documents=passages)
            persist_sse_turn(db, session.conversation_id, query_text, explanation, intent)
            timer.end_phase("Response persistence", record_summary=False)
            
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
            timer.log("Response sent")
            timer.print_summary()
            return

        # 6. Handle Hybrid Queries
        if intent == "HYBRID_BUSINESS_QUERY":
            yield {
                "event": "stage",
                "data": json.dumps({"stage": "schema_discovery", "message": "Executing hybrid data and policy checks..."})
            }
            
            sql_service = SQLService(db_conn=db)
            sql_res = sql_service.process_query(effective_query, session.get_formatted_memory_prompt())
            raw_records = sql_res.get("data", [])
            sql = sql_res.get("sql", "")

            timer.start_phase("Analytics")
            analytics_service = AnalyticsService()
            records = analytics_service.normalize_results(raw_records, sub_intent, effective_query)
            timer.end_phase("Analytics", "Analytics normalization completed")

            rag_agent = DocumentRetrievalAgent()
            passages = rag_agent.retrieve_passages(effective_query)
            
            yield {
                "event": "stage",
                "data": json.dumps({"stage": "answer_synthesis", "message": "Merging database records and policy documents..."})
            }
            
            timer.start_phase("Context construction")
            db_context = str(records[:10]) if records else "No structured data matched."
            policy_context = "\n\n".join([f"Document: {p['metadata'].get('title', 'Policy')}\nContent: {p['content']}" for p in passages]) if passages else "No policy documents matched."
            prompt = PromptBuilder.build_hybrid_prompt(effective_query, db_context, policy_context)
            timer.end_phase("Context construction", "Context construction completed")

            timer.start_phase("Hybrid answer synthesis")
            explanation = ollama_client.generate(prompt=prompt, purpose="final response")
            timer.end_phase("Hybrid answer synthesis", "Final response generated", summary_key="Final response generation")
            
            columns = list(records[0].keys()) if records else []
            
            timer.start_phase("Visualization decision")
            viz_eval = analytics_service.evaluate_visualization(effective_query, intent, records, columns, sub_intent=sub_intent)
            chart_config = analytics_service.generate_chart_config(effective_query, sql, records) if viz_eval["should_generate_chart"] else {}
            timer.end_phase("Visualization decision", "Visualization layout generated", summary_key="Analytics")

            timer.start_phase("Response persistence")
            session.record_turn(
                user_query=query_text,
                intent=intent,
                response_text=explanation,
                sql=sql,
                results=records,
                chart_config=chart_config,
                documents=passages
            )
            persist_sse_turn(db, session.conversation_id, query_text, explanation, intent, sql, chart_config, records=records, columns=columns)
            timer.end_phase("Response persistence", record_summary=False)

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
            timer.log("Response sent")
            timer.print_summary()
            return

        # 7. Default Structured Data & Analytics Queries
        timer.log_skipped("RAG", "structured data query")
        
        yield {
            "event": "stage",
            "data": json.dumps({"stage": "sql_generation", "message": "Generating DuckDB SQL query..."})
        }
        
        sql_service = SQLService(db_conn=db)
        mem_prompt = session.get_formatted_memory_prompt() if context_resolution.get("is_follow_up", False) else ""
        sql_res = sql_service.process_query(effective_query, mem_prompt)
        
        if not sql_res.get("success", False):
            err_msg = "Data unavailable: I could not retrieve the requested information from the business database."
            logger.warning(f"[SSE_STREAM] SQL query execution failed for '{effective_query}': {sql_res.get('error')}. Returning Data unavailable without RAG fallback.")
            persist_sse_turn(db, session.conversation_id, query_text, err_msg, intent)
            yield {
                "event": "completed",
                "data": json.dumps({
                    "generated_sql": "",
                    "explanation": err_msg,
                    "columns": [],
                    "results": [],
                    "chart_spec": "{}"
                })
            }
            timer.log("Response sent (Data unavailable)")
            timer.print_summary()
            return

        sql = sql_res.get("sql", "")
        raw_records = sql_res.get("data", [])

        timer.start_phase("Analytics")
        analytics_service = AnalyticsService()
        records = analytics_service.normalize_results(raw_records, sub_intent, effective_query)
        columns = list(records[0].keys()) if records else []

        viz_eval = analytics_service.evaluate_visualization(effective_query, intent, records, columns, sub_intent=sub_intent)
        
        chart_config = {}
        if viz_eval["should_generate_chart"]:
            yield {
                "event": "stage",
                "data": json.dumps({"stage": "chart_generation", "message": "Generating ECharts visualization options..."})
            }
            chart_config = analytics_service.generate_chart_config(effective_query, sql, records)

        explanation = analytics_service.explain_analytics(effective_query, sql, records, intent)
        timer.end_phase("Analytics", "Analytics completed")

        timer.start_phase("Final response generation")
        session.record_turn(
            user_query=query_text,
            intent=intent,
            response_text=explanation,
            sql=sql,
            results=records,
            chart_config=chart_config
        )

        persist_sse_turn(db, session.conversation_id, query_text, explanation, intent, sql, chart_config, records=records, columns=columns)
        
        # Persist to unified Business Memory Layer as an Analytical Artifact
        try:
            from app.application.memory.business_memory_service import business_memory_service
            import re
            tables_found = re.findall(r'(?:FROM|JOIN)\s+([a-zA-Z0-9_]+)', sql, re.IGNORECASE)
            cleaned_tables = list(set([t.lower() for t in tables_found if t.lower() not in ("select", "where", "group", "order", "having", "as", "on")]))
            
            # Record user correction if applicable
            lower_q = query_text.lower().strip()
            if lower_q.startswith(("no,", "no ", "actually,", "actually ", "correct that", "i meant ", "correction:")):
                business_memory_service.record_user_correction(
                    user_id="system",
                    workspace_id="default_workspace",
                    original_statement="previous context",
                    corrected_statement=query_text,
                    conversation_id=session.conversation_id
                )

            if records:
                business_memory_service.record_analytical_result(
                    user_id="system",
                    workspace_id="default_workspace",
                    conversation_id=session.conversation_id,
                    query=effective_query,
                    intent=intent,
                    sql=sql,
                    data=records[:50],
                    columns=columns,
                    chart_config=chart_config,
                    summary=explanation[:300] if explanation else "",
                    source_tables=cleaned_tables,
                )
        except Exception as bme:
            logger.warning(f"Business memory artifact recording notice: {bme}")
            
        timer.end_phase("Final response generation", "Final response generated")

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
        timer.log("Response sent")
        timer.print_summary()

    return EventSourceResponse(event_generator())


def persist_sse_turn(
    db,
    conversation_id: str,
    query_text: str,
    response_text: str,
    intent: str = "",
    sql: str = "",
    chart_config: dict = None,
    records: list = None,
    columns: list = None
):
    """Persist user and assistant turn messages directly to DuckDB conversations table."""
    try:
        cid = conversation_id if (conversation_id and conversation_id != "default_session") else "conv_default_session"
        from datetime import datetime
        import uuid
        now = datetime.utcnow()
        conv = db.execute("SELECT id, title FROM conversations WHERE id = ?", [cid]).fetchone()
        if not conv:
            from app.api.conversations import extract_auto_title
            title = extract_auto_title(query_text)
            db.execute("""
                INSERT INTO conversations (id, user_id, title, created_at, updated_at, last_message_at, pinned, archived, message_count, preview)
                VALUES (?, 'system', ?, ?, ?, ?, FALSE, FALSE, 0, ?)
            """, [cid, title, now, now, now, query_text[:80]])
        
        query_meta_str = json.dumps({"columns": columns or [], "rows": records[:50] if records else []}) if (records or columns) else None

        # User message
        db.execute("""
            INSERT INTO conversation_messages (id, conversation_id, role, content, created_at, intent, query_metadata, sql_metadata, visualization_metadata)
            VALUES (?, ?, 'user', ?, ?, ?, NULL, ?, ?)
        """, [f"msg_{uuid.uuid4().hex[:12]}", cid, query_text, now, intent, sql, json.dumps(chart_config) if chart_config else None])

        # Assistant message
        db.execute("""
            INSERT INTO conversation_messages (id, conversation_id, role, content, created_at, intent, query_metadata, sql_metadata, visualization_metadata)
            VALUES (?, ?, 'assistant', ?, ?, ?, ?, ?, ?)
        """, [f"msg_{uuid.uuid4().hex[:12]}", cid, response_text, now, intent, query_meta_str, sql, json.dumps(chart_config) if chart_config else None])

        preview = response_text[:80].strip() if response_text else query_text[:80].strip()
        db.execute("""
            UPDATE conversations 
            SET updated_at = ?, last_message_at = ?, message_count = message_count + 2, preview = ?
            WHERE id = ?
        """, [now, now, preview, cid])
        
        db.execute("CHECKPOINT;")
    except Exception as e:
        logger.error(f"Failed to persist SSE turn to DB: {e}")


"""
CLARIUS Backend - Conversation History API

Exposes REST endpoints for persistent enterprise conversation history,
search, pinning, archiving, message history retrieval, and memory synchronization.
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.infrastructure.database import get_db
from app.api.dependencies import get_current_user
from app.domain.entities import User
from app.ai.conversation_memory import memory_manager

router = APIRouter(prefix="/conversations", tags=["conversations"])


class ConversationPayload(BaseModel):
    title: Optional[str] = None


class ConversationPatchPayload(BaseModel):
    title: Optional[str] = None
    pinned: Optional[bool] = None
    archived: Optional[bool] = None


class MessagePayload(BaseModel):
    role: str
    content: str
    intent: Optional[str] = None
    query_metadata: Optional[Dict[str, Any]] = None
    sql_metadata: Optional[str] = None
    visualization_metadata: Optional[Dict[str, Any]] = None


def extract_auto_title(query: str) -> str:
    """Generate a clean concise conversation title from initial user query."""
    clean = query.strip()
    if not clean:
        return "New Conversation"
    # Take first line or up to 45 chars
    first_line = clean.split("\n")[0]
    if len(first_line) > 45:
        return first_line[:42].strip() + "..."
    return first_line.title()


@router.get("", response_model=List[Dict[str, Any]])
async def list_user_conversations(
    q: Optional[str] = Query(None, description="Search query string"),
    pinned: Optional[bool] = Query(None, description="Filter pinned conversations"),
    archived: bool = Query(False, description="Include archived conversations"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve persistent conversation history for the active user."""
    conditions = ["(user_id = ? OR user_id = 'system')"]
    params: List[Any] = [str(current_user.id)]

    if not archived:
        conditions.append("(archived = FALSE OR archived IS NULL)")
    
    if pinned is not None:
        conditions.append("pinned = ?")
        params.append(pinned)

    if q and q.strip():
        search_pattern = f"%{q.strip()}%"
        conditions.append("""(
            LOWER(title) LIKE LOWER(?) OR 
            LOWER(preview) LIKE LOWER(?) OR 
            id IN (
                SELECT conversation_id FROM conversation_messages 
                WHERE LOWER(content) LIKE LOWER(?)
            )
        )""")
        params.extend([search_pattern, search_pattern, search_pattern])

    where_clause = " AND ".join(conditions)
    query_sql = f"""
        SELECT id, user_id, title, created_at, updated_at, last_message_at, pinned, archived, message_count, preview
        FROM conversations
        WHERE {where_clause}
        ORDER BY pinned DESC, last_message_at DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    rows = db.execute(query_sql, params).fetchall()

    results = []
    for r in rows:
        results.append({
            "id": r[0],
            "user_id": r[1],
            "title": r[2] or "Untitled Conversation",
            "created_at": r[3].isoformat() if hasattr(r[3], "isoformat") else str(r[3]),
            "updated_at": r[4].isoformat() if hasattr(r[4], "isoformat") else str(r[4]),
            "last_message_at": r[5].isoformat() if hasattr(r[5], "isoformat") else str(r[5]),
            "pinned": bool(r[6]),
            "archived": bool(r[7]),
            "message_count": r[8] or 0,
            "preview": r[9] or ""
        })

    return results


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: Optional[ConversationPayload] = None,
    db: duckdb.DuckDBPyConnection = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new persistent conversation context."""
    conv_id = f"conv_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow()
    title = payload.title if (payload and payload.title) else "New Conversation"

    db.execute("""
        INSERT INTO conversations (id, user_id, title, created_at, updated_at, last_message_at, pinned, archived, message_count, preview)
        VALUES (?, ?, ?, ?, ?, ?, FALSE, FALSE, 0, '')
    """, [conv_id, current_user.id, title, now, now, now])

    return {
        "id": conv_id,
        "user_id": current_user.id,
        "title": title,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "last_message_at": now.isoformat(),
        "pinned": False,
        "archived": False,
        "message_count": 0,
        "preview": ""
    }


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    db: duckdb.DuckDBPyConnection = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch conversation details and message history, restoring context into memory manager."""
    user_str = str(current_user.id)
    conv = db.execute("""
        SELECT id, user_id, title, created_at, updated_at, last_message_at, pinned, archived, message_count, preview
        FROM conversations
        WHERE id = ? AND (user_id = ? OR user_id = 'system')
    """, [conversation_id, user_str]).fetchone()

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied.")

    msgs = db.execute("""
        SELECT id, conversation_id, role, content, created_at, intent, query_metadata, sql_metadata, visualization_metadata
        FROM conversation_messages
        WHERE conversation_id = ?
        ORDER BY created_at ASC
    """, [conversation_id]).fetchall()

    messages_list = []
    session = memory_manager.get_session(conversation_id)

    for m in msgs:
        msg_obj = {
            "id": m[0],
            "conversation_id": m[1],
            "role": m[2],
            "content": m[3],
            "created_at": m[4].isoformat() if hasattr(m[4], "isoformat") else str(m[4]),
            "intent": m[5],
            "query_metadata": m[6],
            "sql_metadata": m[7],
            "visualization_metadata": m[8]
        }
        messages_list.append(msg_obj)

        # Restore turn into session memory if role is user or assistant
        if m[2] == "user":
            session.last_query = m[3]
        elif m[2] == "assistant" and m[7]:
            session.last_sql = m[7]

    return {
        "id": conv[0],
        "user_id": conv[1],
        "title": conv[2] or "Untitled Conversation",
        "created_at": conv[3].isoformat() if hasattr(conv[3], "isoformat") else str(conv[3]),
        "updated_at": conv[4].isoformat() if hasattr(conv[4], "isoformat") else str(conv[4]),
        "last_message_at": conv[5].isoformat() if hasattr(conv[5], "isoformat") else str(conv[5]),
        "pinned": bool(conv[6]),
        "archived": bool(conv[7]),
        "message_count": conv[8] or len(messages_list),
        "preview": conv[9] or "",
        "messages": messages_list
    }


@router.patch("/{conversation_id}")
async def patch_conversation(
    conversation_id: str,
    payload: ConversationPatchPayload,
    db: duckdb.DuckDBPyConnection = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update conversation title, pinned status, or archived status."""
    user_str = str(current_user.id)
    conv = db.execute("SELECT id FROM conversations WHERE id = ? AND (user_id = ? OR user_id = 'system')", [conversation_id, user_str]).fetchone()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    updates = []
    params = []

    if payload.title is not None:
        updates.append("title = ?")
        params.append(payload.title.strip())

    if payload.pinned is not None:
        updates.append("pinned = ?")
        params.append(payload.pinned)

    if payload.archived is not None:
        updates.append("archived = ?")
        params.append(payload.archived)

    if updates:
        updates.append("updated_at = ?")
        params.append(datetime.utcnow())
        params.append(conversation_id)
        
        sql = f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?"
        db.execute(sql, params)

    return {"status": "success", "conversation_id": conversation_id}


@router.post("/{conversation_id}/pin")
async def toggle_pin_conversation(
    conversation_id: str,
    pinned: Optional[bool] = Query(None),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Toggle or set pinned state of a conversation."""
    user_str = str(current_user.id)
    conv = db.execute("SELECT pinned FROM conversations WHERE id = ? AND (user_id = ? OR user_id = 'system')", [conversation_id, user_str]).fetchone()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    new_pinned = not conv[0] if pinned is None else pinned
    db.execute("UPDATE conversations SET pinned = ?, updated_at = ? WHERE id = ?", [new_pinned, datetime.utcnow(), conversation_id])

    return {"status": "success", "conversation_id": conversation_id, "pinned": new_pinned}


@router.post("/{conversation_id}/archive")
async def toggle_archive_conversation(
    conversation_id: str,
    archived: Optional[bool] = Query(None),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Toggle or set archived state of a conversation."""
    user_str = str(current_user.id)
    conv = db.execute("SELECT archived FROM conversations WHERE id = ? AND (user_id = ? OR user_id = 'system')", [conversation_id, user_str]).fetchone()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    new_archived = not conv[0] if archived is None else archived
    db.execute("UPDATE conversations SET archived = ?, updated_at = ? WHERE id = ?", [new_archived, datetime.utcnow(), conversation_id])

    return {"status": "success", "conversation_id": conversation_id, "archived": new_archived}


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: duckdb.DuckDBPyConnection = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Permanently delete a conversation and its associated messages."""
    user_str = str(current_user.id)
    conv = db.execute("SELECT id FROM conversations WHERE id = ? AND (user_id = ? OR user_id = 'system')", [conversation_id, user_str]).fetchone()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    db.execute("DELETE FROM conversation_messages WHERE conversation_id = ?", [conversation_id])
    db.execute("DELETE FROM conversations WHERE id = ?", [conversation_id])
    memory_manager.clear_session(conversation_id)

    return {"status": "success", "deleted_conversation_id": conversation_id}


@router.post("/{conversation_id}/messages")
async def add_conversation_message(
    conversation_id: str,
    payload: MessagePayload,
    db: duckdb.DuckDBPyConnection = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Append a message turn to a conversation and auto-update title & preview."""
    now = datetime.utcnow()
    msg_id = f"msg_{uuid.uuid4().hex[:12]}"

    user_str = str(current_user.id)
    conv = db.execute("SELECT id, title, message_count FROM conversations WHERE id = ? AND (user_id = ? OR user_id = 'system')", [conversation_id, user_str]).fetchone()
    
    if not conv:
        auto_title = extract_auto_title(payload.content) if payload.role == "user" else "New Conversation"
        db.execute("""
            INSERT INTO conversations (id, user_id, title, created_at, updated_at, last_message_at, pinned, archived, message_count, preview)
            VALUES (?, ?, ?, ?, ?, ?, FALSE, FALSE, 0, ?)
        """, [conversation_id, user_str, auto_title, now, now, now, payload.content[:60]])
        conv_title = auto_title
    else:
        conv_title = conv[1]

    db.execute("""
        INSERT INTO conversation_messages (id, conversation_id, role, content, created_at, intent, query_metadata, sql_metadata, visualization_metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        msg_id, conversation_id, payload.role, payload.content, now,
        payload.intent, str(payload.query_metadata) if payload.query_metadata else None,
        payload.sql_metadata, str(payload.visualization_metadata) if payload.visualization_metadata else None
    ])

    new_title = conv_title
    if (conv_title == "New Conversation" or not conv_title) and payload.role == "user":
        new_title = extract_auto_title(payload.content)

    preview_snippet = payload.content[:80].strip()
    db.execute("""
        UPDATE conversations 
        SET title = ?, updated_at = ?, last_message_at = ?, message_count = message_count + 1, preview = ?
        WHERE id = ?
    """, [new_title, now, now, preview_snippet, conversation_id])

    return {
        "id": msg_id,
        "conversation_id": conversation_id,
        "role": payload.role,
        "content": payload.content,
        "created_at": now.isoformat(),
        "conversation_title": new_title
    }

"""
CLARIUS Backend - Document & RAG Service

This service implements text chunking, ChromaDB vector indexing, document categorization,
and semantic similarity searches (ADR-005).
"""

import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from app.domain.repositories import IDocumentRepository
from app.infrastructure.knowledge import knowledge_manager
from app.modules.documents.application.ocr_service import ocr_service
from app.modules.documents.application.document_classifier import (
    classify_document, normalize_category_id, CATEGORY_DEFINITIONS
)

logger = logging.getLogger("clarius.documents.service")


class DocumentService:
    """Manages document catalog, automated categorization, and vector store indexations (P1.1)."""
    
    def __init__(self, doc_repo: IDocumentRepository):
        self.doc_repo = doc_repo
        self.ocr = ocr_service

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into sentence/paragraph-aware overlapping chunks of defined size."""
        if not text or not text.strip():
            return ["Empty Document"]
        
        # Split into logical paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

        chunks = []
        current_chunk = ""

        for p in paragraphs:
            if len(current_chunk) + len(p) + 2 <= chunk_size:
                current_chunk = f"{current_chunk}\n\n{p}".strip()
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                if len(p) > chunk_size:
                    # Paragraph itself is too long, split with overlapping window
                    start = 0
                    while start < len(p):
                        end = start + chunk_size
                        chunks.append(p[start:end])
                        start += chunk_size - overlap
                    current_chunk = ""
                else:
                    current_chunk = p

        if current_chunk:
            chunks.append(current_chunk)

        return chunks if chunks else [text]

    async def ingest_document(
        self,
        file_path: Path,
        doc_type: str = "auto",
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract text, automatically or manually classify, chunk, index in ChromaDB,
        and write structured metadata record to DuckDB repository.
        """
        # 1. Parse and extract text
        extracted_text = self.ocr.extract_text(file_path)
        doc_title = title or file_path.name
        
        # 2. Automated classification or normalization
        raw_type = (doc_type or "auto").strip().lower()
        if raw_type in ("auto", "detect", "auto-detect", "", "none"):
            final_type, confidence, rationale = classify_document(
                title=doc_title,
                content=extracted_text,
                filename=file_path.name
            )
            auto_detected = True
        else:
            final_type = normalize_category_id(raw_type)
            confidence = 1.0
            rationale = "Manually assigned by user during upload"
            auto_detected = False

        cat_info = CATEGORY_DEFINITIONS.get(final_type, CATEGORY_DEFINITIONS["policy"])
        category_name = cat_info["name"]

        # 3. Dynamic keywords and summary
        clean_words = [w.strip(".,;:()[]{}").title() for w in (doc_title + " " + extracted_text[:400]).split() if len(w) > 4]
        unique_keywords = list(dict.fromkeys(clean_words))[:6]
        word_count = len(extracted_text.split())
        est_pages = max(1, round(word_count / 350))

        # 4. Ingest metadata to repository
        doc_id = str(uuid.uuid4())
        file_size_bytes = file_path.stat().st_size if file_path.exists() else len(extracted_text.encode('utf-8'))
        
        meta_dict = {
            "file_size": file_size_bytes,
            "file_path": str(file_path),
            "category_name": category_name,
            "auto_detected": auto_detected,
            "classification_confidence": confidence,
            "classification_rationale": rationale,
            "word_count": word_count,
            "page_count": est_pages,
            "summary": f"{category_name} document '{doc_title}' containing {word_count} words ({est_pages} pages) indexed into ChromaDB knowledge base."
        }
        
        self.doc_repo.save_document(
            doc_id=doc_id,
            title=doc_title,
            content=extracted_text,
            doc_type=final_type,
            metadata_dict=meta_dict,
            embedding_id=doc_id
        )
        
        # 5. Chunk text and index in ChromaDB
        chunks = self.chunk_text(extracted_text)
        try:
            collection = knowledge_manager.create_collection_if_not_exists("clarius_documents")
            ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
            metadatas = [
                {
                    "doc_id": doc_id,
                    "title": doc_title,
                    "doc_type": final_type,
                    "category": category_name,
                    "chunk_index": i
                }
                for i in range(len(chunks))
            ]
            
            collection.add(
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )
        except Exception as e:
            logger.warning(f"ChromaDB indexing encountered a non-fatal warning: {str(e)}")
        
        logger.info(f"Ingested document '{doc_title}' -> '{final_type}' ({category_name}). Chunks: {len(chunks)}.")
        
        return {
            "id": doc_id,
            "title": doc_title,
            "doc_type": final_type,
            "category_name": category_name,
            "file_size": file_size_bytes,
            "chunks_count": len(chunks),
            "confidence": confidence,
            "auto_detected": auto_detected,
            "summary": meta_dict["summary"]
        }

    def search_similar_chunks(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Perform semantic similarity search on documents in ChromaDB."""
        collection = knowledge_manager.create_collection_if_not_exists("clarius_documents")
        
        results = collection.query(
            query_texts=[query],
            n_results=limit
        )
        
        formatted_results = []
        seen = set()
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metadatas = results["metadatas"][0] if "metadatas" in results else []
            distances = results["distances"][0] if "distances" in results else []
            
            for i in range(len(docs)):
                content = docs[i]
                meta = metadatas[i] if i < len(metadatas) else {}
                score = distances[i] if i < len(distances) else 0.0
                
                title = meta.get("title", "") if isinstance(meta, dict) else ""
                dedup_key = (title, content.strip())
                if dedup_key not in seen:
                    seen.add(dedup_key)
                    formatted_results.append({
                        "content": content,
                        "metadata": meta,
                        "score": score
                    })
                
        return formatted_results


async def seed_knowledge_documents(service: Optional[DocumentService] = None) -> None:
    """Automatically seed policy & SOP files from synthetic_micro_enterprise/data/knowledge if missing."""
    try:
        from app.infrastructure.database import db_manager
        from app.infrastructure.repositories import DuckDBDocumentRepository
        
        if service is None:
            repo = DuckDBDocumentRepository(db_manager)
            service = DocumentService(repo)
            conn = db_manager.get_connection()
        else:
            conn = service.doc_repo._get_connection()
            
        # Resolve project root dynamically
        curr = Path(__file__).resolve()
        base_dir = curr.parent
        for p in curr.parents:
            if (p / "synthetic_micro_enterprise").exists():
                base_dir = p
                break

        knowledge_dir = base_dir / "synthetic_micro_enterprise" / "data" / "knowledge"
        
        if not knowledge_dir.exists():
            return

        existing_rows = conn.execute("SELECT title FROM documents").fetchall()
        existing_titles = {r[0].lower().strip() for r in existing_rows}
        
        for file_path in knowledge_dir.glob("*.txt"):
            title = file_path.stem.replace("_", " ").title()
            if title.lower().strip() not in existing_titles:
                logger.info(f"Seeding knowledge document '{title}' from {file_path}")
                await service.ingest_document(file_path=file_path, doc_type="auto", title=title)
                existing_titles.add(title.lower().strip())
    except Exception as e:
        logger.warning(f"Seed knowledge documents notice: {e}")

"""
CLARIUS Backend - Document & RAG Service

This service implements text chunking, ChromaDB vector indexing, and similarity searches (ADR-005).
"""

import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.domain.repositories import IDocumentRepository
from app.infrastructure.knowledge import knowledge_manager
from app.modules.documents.application.ocr_service import ocr_service

logger = logging.getLogger("clarius.documents.service")

class DocumentService:
    """Manages document catalog and vector store indexations using repositories (P1.1)."""
    
    def __init__(self, doc_repo: IDocumentRepository):
        self.doc_repo = doc_repo
        self.ocr = ocr_service

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks of defined size."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks

    async def ingest_document(self, file_path: Path, doc_type: str, title: Optional[str] = None) -> str:
        """Extract text, chunk it, index in ChromaDB, and write metadata record to repository."""
        # 1. Parse and extract text
        extracted_text = self.ocr.extract_text(file_path)
        
        # 2. Ingest metadata to repository
        doc_id = str(uuid.uuid4())
        doc_title = title or file_path.name
        
        meta_dict = {
            "file_size": file_path.stat().st_size if file_path.exists() else 0,
            "file_path": str(file_path)
        }
        
        self.doc_repo.save_document(
            doc_id=doc_id,
            title=doc_title,
            content=extracted_text,
            doc_type=doc_type,
            metadata_dict=meta_dict,
            embedding_id=doc_id
        )
        
        # 3. Chunk text
        chunks = self.chunk_text(extracted_text)
        
        # 4. Store chunks in ChromaDB Knowledge collection
        collection = knowledge_manager.create_collection_if_not_exists("clarius_documents")
        
        ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"doc_id": doc_id, "title": doc_title, "chunk_index": i} for i in range(len(chunks))]
        
        collection.add(
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        
        logger.info(f"Ingested document {doc_title} successfully. Chunk count: {len(chunks)}.")
        return doc_id

    def search_similar_chunks(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
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

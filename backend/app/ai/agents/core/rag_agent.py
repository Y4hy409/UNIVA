"""
CLARIUS Backend - Document Retrieval Agent (RAG)

This agent matches query contexts against indexed documents using ChromaDB vector lookups (P1.3).
"""

import logging
from typing import List, Dict, Any
from app.infrastructure.knowledge import knowledge_manager

logger = logging.getLogger("clarius.ai.agents.rag")

class DocumentRetrievalAgent:
    """Performs semantic similarity searches to retrieve RAG matching passages."""

    def __init__(self, collection_name: str = "clarius_documents"):
        self.collection_name = collection_name

    def retrieve_passages(self, query_text: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Retrieve similarity chunks matching query_text from ChromaDB."""
        try:
            collection = knowledge_manager.create_collection_if_not_exists(self.collection_name)
            results = collection.query(
                query_texts=[query_text],
                n_results=limit
            )
            
            passages = []
            if results and "documents" in results and results["documents"]:
                docs = results["documents"][0]
                metadatas = results["metadatas"][0] if "metadatas" in results else []
                distances = results["distances"][0] if "distances" in results else []
                
                for i in range(len(docs)):
                    passages.append({
                        "content": docs[i],
                        "metadata": metadatas[i] if i < len(metadatas) else {},
                        "distance": distances[i] if i < len(distances) else 0.0
                    })
            return passages
        except Exception as e:
            logger.error(f"RAG Retrieval Agent failed: {str(e)}")
            return []

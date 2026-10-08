import logging
import re
from typing import List, Dict, Any, Optional
from app.infrastructure.knowledge import knowledge_manager
from app.core.performance_logger import get_current_timer

logger = logging.getLogger("clarius.ai.agents.rag")

# Maximum distance to accept a passage as relevant.
_RELEVANCE_THRESHOLD = 1.75

KNOWN_DOC_TITLES = [
    "Sales Policy", "Return Policy", "Credit Policy", "Discount Policy",
    "Inventory Policy", "Procurement Policy", "Payment Terms",
    "Branch Operations", "Company Profile"
]

class DocumentRetrievalAgent:
    """Performs semantic similarity searches to retrieve RAG matching passages with title filtering."""

    def __init__(self, collection_name: str = "clarius_documents"):
        self.collection_name = collection_name

    def _detect_explicit_target_title(self, query_text: str) -> Optional[str]:
        """Detect if the user query explicitly refers to a specific document name or title."""
        q_lower = query_text.lower()
        for title in KNOWN_DOC_TITLES:
            if title.lower() in q_lower:
                return title
        
        # Check for filename patterns (e.g. sales_policy.txt, company_profile.pdf)
        match = re.search(r'([a-zA-Z0-9_\-]+\.(?:txt|pdf|docx|doc|csv))', q_lower)
        if match:
            raw_fn = match.group(1)
            stem = raw_fn.split('.')[0].replace('_', ' ').replace('-', ' ').title()
            return stem
            
        return None

    def retrieve_passages(self, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve similarity chunks matching query_text from ChromaDB."""
        timer = get_current_timer()
        explicit_title = self._detect_explicit_target_title(query_text)
        if explicit_title:
            logger.info(f"[RAG] Explicit target document detected in query: '{explicit_title}'")

        try:
            collection = knowledge_manager.create_collection_if_not_exists(self.collection_name)

            count = collection.count()
            if isinstance(count, int) and count == 0:
                logger.info("RAG: document collection is empty — skipping retrieval.")
                if timer:
                    timer.log("RAG document collection is empty")
                return []

            # Retrieve larger candidate pool for reranking/filtering
            fetch_limit = min(max(limit * 3, 10), count) if isinstance(count, int) else limit * 3

            if timer:
                timer.start_phase("ChromaDB retrieval")
            
            results = collection.query(
                query_texts=[query_text],
                n_results=fetch_limit
            )
            
            if timer:
                timer.end_phase("ChromaDB retrieval", "ChromaDB retrieval completed")

            passages = []
            if results and "documents" in results and results["documents"]:
                docs = results["documents"][0]
                metadatas = results["metadatas"][0] if "metadatas" in results else []
                distances = results["distances"][0] if "distances" in results else []

                for i in range(len(docs)):
                    distance = distances[i] if i < len(distances) else 999.0
                    meta = metadatas[i] if i < len(metadatas) else {}
                    doc_title = meta.get("title", "") if isinstance(meta, dict) else ""
                    
                    if distance > _RELEVANCE_THRESHOLD:
                        logger.info(f"RAG: skipping passage '{doc_title}' — distance {distance:.4f} > threshold {_RELEVANCE_THRESHOLD}")
                        continue
                        
                    passages.append({
                        "content": docs[i],
                        "metadata": meta,
                        "distance": distance,
                        "title": doc_title
                    })

            if not passages:
                logger.info(f"RAG: no relevant passages found for query '{query_text}'")
                return []

            # Perform title preference filtering/reranking if explicit title requested
            if explicit_title:
                matching_passages = [
                    p for p in passages 
                    if explicit_title.lower() in p["title"].lower() or p["title"].lower() in explicit_title.lower()
                ]
                if matching_passages:
                    logger.info(f"[RAG] Found {len(matching_passages)} passages matching explicit target '{explicit_title}'. Discarding unrelated document passages.")
                    passages = matching_passages

            # Sort by vector distance and return top `limit` passages
            passages.sort(key=lambda x: x["distance"])
            final_passages = passages[:limit]

            retrieved_titles = list(dict.fromkeys([p["title"] for p in final_passages]))
            logger.info(f"[RAG] Final retrieved documents: {retrieved_titles} ({len(final_passages)} passages)")

            return final_passages
        except Exception as e:
            logger.error(f"RAG Retrieval Agent failed: {str(e)}")
            return []


"""
CLARIUS Backend - Knowledge Layer Infrastructure

This module handles connection management and vector indexing for ChromaDB,
which acts as our vector store and semantic search provider.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import chromadb
from app.core.config import settings

class KnowledgeManager:
    """Manager for ChromaDB persistent store."""
    
    def __init__(self, persist_directory: Optional[Path] = None):
        self.persist_directory = persist_directory or settings.CHROMADB_PATH
        # Ensure path exists
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.client = None

    def get_client(self) -> chromadb.ClientAPI:
        """Retrieve or initialize the ChromaDB client."""
        if self.client is None:
            self.client = chromadb.CloudClient(
                api_key='ck-5vZ3NdcfqenK75JrUQi59k8FUSf2HBSm5QuwA9nzJpkq',
                tenant='e3fc503b-adc1-4455-bc48-3e3398d0aaeb',
                database='CLARIUS'
            )
        return self.client

    def create_collection_if_not_exists(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        """Create a collection or get it if it already exists."""
        client = self.get_client()
        return client.get_or_create_collection(name=name, metadata=metadata)

    def heartbeat(self) -> bool:
        """Check if connection to ChromaDB is alive."""
        try:
            client = self.get_client()
            client.heartbeat()
            return True
        except Exception:
            return False


# Global instance
knowledge_manager = KnowledgeManager()

def get_knowledge_client() -> chromadb.ClientAPI:
    """FastAPI Dependency for vector store client."""
    return knowledge_manager.get_client()

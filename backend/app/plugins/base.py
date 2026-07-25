"""
CLARIUS Backend - Plugin Interface Contracts

This module defines base class protocols and schemas for plugins (P2).
"""

from typing import Dict, Any, List, Optional, AsyncIterator
from pydantic import BaseModel
from datetime import datetime

class ConnectionResult(BaseModel):
    success: bool
    error: Optional[str] = None


class SourceSchema(BaseModel):
    tables: List[str]
    details: Dict[str, Any]


class SyncResult(BaseModel):
    success: bool
    records_synced: int
    error: Optional[str] = None


class IPlugin:
    """Base class for all CLARIUS pluggable components."""
    
    def __init__(self, manifest: Any):
        self.manifest = manifest

    async def initialize(self) -> None:
        """Lifecycle hook called when plugin gets loaded."""
        pass

    async def shutdown(self) -> None:
        """Lifecycle hook called on system termination."""
        pass


class IDataConnector(IPlugin):
    """Protocol defining general data synchronization layers."""

    async def test_connection(self, config: Dict[str, Any]) -> ConnectionResult:
        """Verify host or credential settings connection success."""
        raise NotImplementedError

    async def discover_schema(self, config: Dict[str, Any]) -> SourceSchema:
        """Retrieve structure schema definition details."""
        raise NotImplementedError


class IERPConnector(IDataConnector):
    """Protocol defining specialized Enterprise Resource Planning sync interfaces."""

    async def get_entities(self) -> List[str]:
        """List tables or ledger categories supported by the connector."""
        raise NotImplementedError

    async def sync_entity(self, entity: str, config: Dict[str, Any], since: Optional[datetime] = None) -> SyncResult:
        """Pull transactional details from the target ERP service."""
        raise NotImplementedError

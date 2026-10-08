"""
CLARIUS Backend - ERPNext Connector
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from app.plugins.base import IERPConnector, ConnectionResult, SourceSchema, SyncResult

class ERPNextConnector(IERPConnector):
    """ERPNext connector integration implementing IERPConnector."""

    async def test_connection(self, config: Dict[str, Any]) -> ConnectionResult:
        if not config.get("url"):
            return ConnectionResult(success=False, error="URL connection settings is missing.")
        return ConnectionResult(success=True)

    async def discover_schema(self, config: Dict[str, Any]) -> SourceSchema:
        return SourceSchema(
            tables=["customers", "items", "sales_orders"],
            details={"api_version": "v12"}
        )

    async def get_entities(self) -> List[str]:
        return ["customers", "items", "sales_orders"]

    async def sync_entity(self, entity: str, config: Dict[str, Any], since: Optional[datetime] = None) -> SyncResult:
        if entity not in await self.get_entities():
            return SyncResult(success=False, records_synced=0, error=f"Unknown entity: {entity}")
        return SyncResult(success=True, records_synced=12)

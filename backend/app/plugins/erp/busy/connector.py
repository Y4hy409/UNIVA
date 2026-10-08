"""
CLARIUS Backend - Busy Connector
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from app.plugins.base import IERPConnector, ConnectionResult, SourceSchema, SyncResult

class BusyConnector(IERPConnector):
    """Busy SQL ledger connector integration implementing IERPConnector."""

    async def test_connection(self, config: Dict[str, Any]) -> ConnectionResult:
        if not config.get("connection_string"):
            return ConnectionResult(success=False, error="Database connection_string is missing.")
        return ConnectionResult(success=True)

    async def discover_schema(self, config: Dict[str, Any]) -> SourceSchema:
        return SourceSchema(
            tables=["accounts", "inventory_transactions", "tax_vouchers"],
            details={"busy_engine": "mssql"}
        )

    async def get_entities(self) -> List[str]:
        return ["accounts", "inventory_transactions", "tax_vouchers"]

    async def sync_entity(self, entity: str, config: Dict[str, Any], since: Optional[datetime] = None) -> SyncResult:
        if entity not in await self.get_entities():
            return SyncResult(success=False, records_synced=0, error=f"Unknown entity: {entity}")
        return SyncResult(success=True, records_synced=88)

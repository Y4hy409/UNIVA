"""
CLARIUS Backend - Dashboards Service

This service manages creating, querying, and updating dashboard layouts and widgets (ADR-000).
"""

import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import duckdb

from app.domain.entities import Dashboard
from app.infrastructure.database import db_manager

class DashboardService:
    """Manages CRUD operations for dashboards and default templates."""
    
    def __init__(self, db_conn: Optional[duckdb.DuckDBPyConnection] = None):
        self.conn = db_conn or db_manager.get_connection()

    def list_dashboards(self) -> List[Dashboard]:
        """List all dashboards, creating default templates if none exist."""
        rows = self.conn.execute("SELECT * FROM dashboards").fetchall()
        
        if not rows:
            self._create_default_templates()
            rows = self.conn.execute("SELECT * FROM dashboards").fetchall()
            
        return [self._row_to_dashboard(r) for r in rows]

    def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """Fetch dashboard details by ID."""
        row = self.conn.execute("SELECT * FROM dashboards WHERE id = ?", [dashboard_id]).fetchone()
        if not row:
            return None
        return self._row_to_dashboard(row)

    def create_dashboard(self, name: str, description: str, owner_id: str, widgets: List[Dict[str, Any]], layout: Dict[str, Any]) -> Dashboard:
        """Create a new dashboard."""
        dash = Dashboard(
            id=uuid.uuid4(),
            name=name,
            description=description,
            owner_id=uuid.UUID(owner_id) if isinstance(owner_id, str) else owner_id,
            widgets=widgets,
            layout=layout,
            is_shared=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.conn.execute(
            """
            INSERT INTO dashboards (id, name, description, owner_id, widgets, layout, is_shared, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                str(dash.id), dash.name, dash.description, str(dash.owner_id),
                json.dumps(dash.widgets), json.dumps(dash.layout), dash.is_shared,
                dash.created_at, dash.updated_at
            ]
        )
        return dash

    def update_dashboard(self, dashboard_id: str, name: str, description: str, widgets: List[Dict[str, Any]], layout: Dict[str, Any]) -> Optional[Dashboard]:
        """Update dashboard details."""
        dash = self.get_dashboard(dashboard_id)
        if not dash:
            return None
            
        now = datetime.utcnow()
        self.conn.execute(
            """
            UPDATE dashboards 
            SET name = ?, description = ?, widgets = ?, layout = ?, updated_at = ?
            WHERE id = ?
            """,
            [name, description, json.dumps(widgets), json.dumps(layout), now, dashboard_id]
        )
        
        return self.get_dashboard(dashboard_id)

    def delete_dashboard(self, dashboard_id: str) -> bool:
        """Delete a dashboard by ID."""
        dash = self.get_dashboard(dashboard_id)
        if not dash:
            return False
            
        self.conn.execute("DELETE FROM dashboards WHERE id = ?", [dashboard_id])
        return True

    def _create_default_templates(self) -> None:
        """Bootstrap default KPI dashboards (Sales Overview, Stock)."""
        owner_id = str(uuid.uuid4())
        
        # 1. Sales Overview Template
        self.create_dashboard(
            name="Sales Overview",
            description="MSME standard sales metrics and trends template",
            owner_id=owner_id,
            widgets=[
                {
                    "title": "Total Revenue Trend",
                    "type": "chart",
                    "chart_options": {
                        "xAxis": {"type": "category", "data": ["Week 1", "Week 2", "Week 3", "Week 4"]},
                        "yAxis": {"type": "value"},
                        "series": [{"data": [12000, 19000, 15000, 22000], "type": "line"}]
                    }
                }
            ],
            layout={"cols": 2, "rows": 1}
        )

    def _row_to_dashboard(self, r) -> Dashboard:
        return Dashboard(
            id=uuid.UUID(r[0]),
            name=r[1],
            description=r[2],
            owner_id=uuid.UUID(r[3]),
            widgets=json.loads(r[4]) if r[4] else [],
            layout=json.loads(r[5]) if r[5] else {},
            is_shared=bool(r[6]),
            created_at=r[7],
            updated_at=r[8]
        )

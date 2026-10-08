"""
CLARIUS Backend - Dynamic Dashboard Intelligence Unit Tests

Tests dataset discovery, automated KPI calculations, data quality metrics,
and ECharts visualization generation over DuckDB business tables.
"""

import unittest
from datetime import datetime

from app.infrastructure.database import DatabaseManager
from app.modules.dashboards.application.dashboard_intelligence_service import DashboardIntelligenceService


class TestDynamicDashboardIntelligence(unittest.TestCase):

    def setUp(self):
        self.db_manager = DatabaseManager(db_path=":memory:")
        self.db_manager.initialize_schema()
        self.db = self.db_manager.get_connection()
        self.service = DashboardIntelligenceService(self.db)

    def test_empty_database_overview(self):
        """Confirm empty database returns zero fake data and clean empty state structure."""
        overview = self.service.get_overview()
        
        self.assertEqual(overview["summary"]["total_datasets"], 0)
        self.assertEqual(overview["summary"]["total_records"], 0)
        self.assertEqual(overview["datasets"], [])
        self.assertEqual(overview["kpis"], [])
        self.assertEqual(overview["visualizations"], [])

    def test_arbitrary_dataset_ingestion_and_dynamic_metrics(self):
        """Confirm ingesting an arbitrary CSV/table generates dynamic KPIs and ECharts without hardcoded names."""
        # Create arbitrary business table (e.g. sales_q1)
        self.db.execute("""
            CREATE TABLE sales_q1 (
                order_id VARCHAR,
                sale_date TIMESTAMP,
                region VARCHAR,
                amount DOUBLE,
                units BIGINT
            )
        """)

        # Insert sample rows
        self.db.execute("""
            INSERT INTO sales_q1 VALUES
            ('ORD_001', '2026-01-01 10:00:00', 'South', 1500.50, 10),
            ('ORD_002', '2026-01-02 11:30:00', 'North', 2300.00, 15),
            ('ORD_003', '2026-01-03 14:15:00', 'South', 1800.25, 12),
            ('ORD_004', '2026-01-04 16:45:00', 'West',  3100.00, 20)
        """)

        overview = self.service.get_overview()

        # 1. Summary checks
        self.assertEqual(overview["summary"]["total_datasets"], 1)
        self.assertEqual(overview["summary"]["total_records"], 4)
        self.assertEqual(overview["summary"]["average_quality_score"], 100.0)

        # 2. Dataset metadata checks
        self.assertEqual(len(overview["datasets"]), 1)
        dataset = overview["datasets"][0]
        self.assertEqual(dataset["name"], "sales_q1")
        self.assertEqual(dataset["business_name"], "Sales Q1")
        self.assertEqual(dataset["rows"], 4)
        self.assertEqual(dataset["columns"], 5)

        # 3. Dynamic KPIs checks
        kpi_labels = [k["label"] for k in overview["kpis"]]
        self.assertIn("Total Sales Q1", kpi_labels)
        self.assertIn("Total Amount", kpi_labels)
        self.assertIn("Average Amount", kpi_labels)

        # Verify numeric sum calculation
        amount_kpi = next(k for k in overview["kpis"] if k["label"] == "Total Amount")
        self.assertEqual(amount_kpi["value"], "$8,700.75")

        # 4. ECharts visualization checks
        self.assertIsNotNone(dataset["visualization"])
        viz = dataset["visualization"]
        self.assertEqual(viz["type"], "line")
        self.assertEqual(viz["title"], "Amount Trend Over Time")
        self.assertEqual(len(viz["chart_options"]["xAxis"]["data"]), 4)


if __name__ == '__main__':
    unittest.main()

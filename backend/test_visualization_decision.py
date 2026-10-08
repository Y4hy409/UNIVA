"""
CLARIUS Backend - Smart Visualization Decision Engine Unit Tests

Verifies that charts are generated only when genuinely useful (time-series,
top-N rankings, category comparisons, composition shares, explicit requests),
and never for simple list lookups, scalar metrics, or RAG responses.
"""

import unittest
from app.ai.services.analytics_service import AnalyticsService


class TestVisualizationDecisionEngine(unittest.TestCase):

    def setUp(self):
        self.service = AnalyticsService()

    def test_single_scalar_metrics_no_chart(self):
        """Scalar metrics ('What is today's revenue?') must return KPI_CARD/TEXT_ONLY without a chart."""
        records = [{"total_revenue": 150000.0}]
        res = self.service.evaluate_visualization("What is today's revenue?", "STRUCTURED_DATA_QUERY", records)
        
        self.assertFalse(res["should_generate_chart"])
        self.assertIn(res["decision"], {"KPI_CARD", "TEXT_ONLY"})

    def test_simple_table_lookups_no_chart(self):
        """Tabular list lookups ('Show customers in Chennai') must return TABLE_ONLY without a chart."""
        records = [
            {"id": "C01", "name": "Ahmad Enterprise", "city": "Chennai"},
            {"id": "C02", "name": "Bala Traders", "city": "Chennai"},
            {"id": "C03", "name": "Chandra Stores", "city": "Chennai"},
            {"id": "C04", "name": "Deepak Logistics", "city": "Chennai"},
            {"id": "C05", "name": "Elango Textiles", "city": "Chennai"}
        ]
        res = self.service.evaluate_visualization("Show customers in Chennai", "STRUCTURED_DATA_QUERY", records)
        
        self.assertFalse(res["should_generate_chart"])
        self.assertEqual(res["decision"], "TABLE_ONLY")

    def test_today_orders_no_chart(self):
        """Simple list of orders ('Show today's orders') must return TABLE_ONLY without a chart."""
        records = [
            {"order_id": "ORD-101", "customer": "Alpha Ltd", "amount": 450.0},
            {"order_id": "ORD-102", "customer": "Beta Corp", "amount": 890.0},
            {"order_id": "ORD-103", "customer": "Gamma Co", "amount": 120.0}
        ]
        res = self.service.evaluate_visualization("Show today's orders", "STRUCTURED_DATA_QUERY", records)
        
        self.assertFalse(res["should_generate_chart"])
        self.assertEqual(res["decision"], "TABLE_ONLY")

    def test_document_knowledge_rag_no_chart(self):
        """Document/RAG queries ('What is our leave policy?') must return TEXT_ONLY without a chart."""
        records = []
        res = self.service.evaluate_visualization("What is our leave policy?", "DOCUMENT_KNOWLEDGE_QUERY", records)
        
        self.assertFalse(res["should_generate_chart"])
        self.assertEqual(res["decision"], "TEXT_ONLY")

    def test_ranking_bar_chart(self):
        """Top-N ranking queries ('Show top 10 products by sales') must generate a BAR_CHART."""
        records = [
            {"product": "Widget A", "total_sales": 50000},
            {"product": "Widget B", "total_sales": 42000},
            {"product": "Widget C", "total_sales": 31000},
            {"product": "Widget D", "total_sales": 25000}
        ]
        res = self.service.evaluate_visualization("Show top 10 products by sales", "ANALYTICS_QUERY", records)
        
        self.assertTrue(res["should_generate_chart"])
        self.assertEqual(res["decision"], "BAR_CHART")

    def test_time_series_line_chart(self):
        """Temporal trend queries ('Show monthly sales') must generate a LINE_CHART."""
        records = [
            {"month": "2026-01", "sales": 120000},
            {"month": "2026-02", "sales": 135000},
            {"month": "2026-03", "sales": 150000}
        ]
        res = self.service.evaluate_visualization("Show monthly sales for this year", "ANALYTICS_QUERY", records)
        
        self.assertTrue(res["should_generate_chart"])
        self.assertEqual(res["decision"], "LINE_CHART")

    def test_comparison_bar_chart(self):
        """Regional comparison queries ('Compare Chennai and Bangalore sales') must generate a BAR_CHART."""
        records = [
            {"region": "Chennai", "revenue": 450000},
            {"region": "Bangalore", "revenue": 620000}
        ]
        res = self.service.evaluate_visualization("Compare Chennai and Bangalore sales", "ANALYTICS_QUERY", records)
        
        self.assertTrue(res["should_generate_chart"])
        self.assertEqual(res["decision"], "BAR_CHART")

    def test_composition_pie_chart(self):
        """Composition share queries ('Show revenue share by category') must generate a PIE_CHART."""
        records = [
            {"category": "Electronics", "share": 45.0},
            {"category": "Apparel", "share": 30.0},
            {"category": "Home", "share": 25.0}
        ]
        res = self.service.evaluate_visualization("Show revenue share by category", "ANALYTICS_QUERY", records)
        
        self.assertTrue(res["should_generate_chart"])
        self.assertEqual(res["decision"], "PIE_CHART")

    def test_correlation_scatter_plot(self):
        """Relationship queries ('Plot price against quantity sold') must generate a SCATTER plot."""
        records = [
            {"unit_price": 10.0, "quantity_sold": 500},
            {"unit_price": 25.0, "quantity_sold": 200},
            {"unit_price": 50.0, "quantity_sold": 80}
        ]
        res = self.service.evaluate_visualization("Plot price against quantity sold", "ANALYTICS_QUERY", records)
        
        self.assertTrue(res["should_generate_chart"])
        self.assertEqual(res["decision"], "SCATTER")

    def test_explicit_chart_keyword_overrides(self):
        """Explicit request ('Chart customers by city') forces chart generation."""
        records = [
            {"city": "Chennai", "customer_count": 45},
            {"city": "Mumbai", "customer_count": 60}
        ]
        res = self.service.evaluate_visualization("Chart customers by city", "STRUCTURED_DATA_QUERY", records)
        
        self.assertTrue(res["should_generate_chart"])
        self.assertEqual(res["decision"], "BAR_CHART")

    def test_followup_query_dynamic_re_evaluation(self):
        """Follow-up query ('Only Chennai') is re-evaluated dynamically and does not inherit previous chart."""
        records = [
            {"id": "C01", "name": "Ahmad Enterprise", "city": "Chennai"},
            {"id": "C02", "name": "Bala Traders", "city": "Chennai"}
        ]
        res = self.service.evaluate_visualization("Only Chennai", "STRUCTURED_DATA_QUERY", records)
        
        self.assertFalse(res["should_generate_chart"])
        self.assertEqual(res["decision"], "TABLE_ONLY")


if __name__ == '__main__':
    unittest.main()

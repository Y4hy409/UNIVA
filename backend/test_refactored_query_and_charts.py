"""
CLARIUS Backend - Master Prompt Refactor Unit Tests

Verifies:
1. Chart suitability (Lookup queries -> NO chart, trends/rankings -> chart).
2. Result deduplication (Entity lookups -> unique entities).
3. Semantic SQL validation (Incomplete WHERE clauses blocked pre-execution).
4. Filter preservation (e.g. location 'Chennai' included in prompt/SQL).
"""

import unittest
from unittest.mock import MagicMock, patch

from app.ai.router import FastIntentRouter
from app.ai.shared.prompt_builder import PromptBuilder
from app.ai.shared.sql_utils import SQLUtils
from app.ai.services.analytics_service import AnalyticsService
from app.infrastructure.sql_validator import SemanticQueryValidator


class TestRefactoredQueryAndCharts(unittest.TestCase):

    def setUp(self):
        self.analytics = AnalyticsService()

    def test_lookup_query_no_chart(self):
        """Lookup query 'medical stores in Chennai' must return NO chart (should_generate_chart = False)."""
        records = [
            {"store_name": "Apollo Pharmacy", "city": "Chennai"},
            {"store_name": "MedPlus", "city": "Chennai"}
        ]
        res = self.analytics.evaluate_visualization("fetch me medical stores in Chennai", "STRUCTURED_DATA_QUERY", records, sub_intent="ENTITY_LOOKUP")
        self.assertFalse(res["should_generate_chart"])
        self.assertEqual(res["decision"], "TABLE_ONLY")

    def test_result_deduplication(self):
        """Duplicate rows from raw join queries should be deduplicated for entity lookups."""
        raw_records = [
            {"store_name": "Apollo Pharmacy", "city": "Chennai"},
            {"store_name": "Apollo Pharmacy", "city": "Chennai"},
            {"store_name": "MedPlus", "city": "Chennai"},
            {"store_name": "MedPlus", "city": "Chennai"}
        ]
        normalized = self.analytics.normalize_results(raw_records, "ENTITY_LOOKUP", "fetch me medical stores in Chennai")
        self.assertEqual(len(normalized), 2)
        store_names = [r["store_name"] for r in normalized]
        self.assertIn("Apollo Pharmacy", store_names)
        self.assertIn("MedPlus", store_names)

    def test_redundant_filter_column_pruning(self):
        """Redundant city column ('Chennai') when user explicitly asked 'in Chennai' should be pruned if entity column exists."""
        raw_records = [
            {"store_name": "Apollo Pharmacy", "city": "Chennai"},
            {"store_name": "MedPlus", "city": "Chennai"}
        ]
        normalized = self.analytics.normalize_results(raw_records, "ENTITY_LOOKUP", "fetch me medical stores in Chennai")
        self.assertNotIn("city", normalized[0])
        self.assertIn("store_name", normalized[0])

    def test_incomplete_where_clause_blocked(self):
        """Incomplete SQL ending in 'WHERE' or 'WHERE LIMIT' must be caught pre-execution."""
        incomplete_sql_1 = "SELECT store_name FROM stores WHERE"
        is_valid_1, err_1 = SemanticQueryValidator.validate_semantic_sql(incomplete_sql_1, "stores in Chennai")
        self.assertFalse(is_valid_1)
        self.assertIn("Incomplete SQL", err_1)

        incomplete_sql_2 = "SELECT store_name FROM stores WHERE LIMIT 10"
        is_valid_2, err_2 = SemanticQueryValidator.validate_semantic_sql(incomplete_sql_2, "stores in Chennai")
        self.assertFalse(is_valid_2)
        self.assertIn("Incomplete SQL", err_2)

    def test_missing_requested_filter_blocked(self):
        """SQL missing requested filter ('Chennai') must fail semantic check."""
        unfiltered_sql = "SELECT store_name FROM stores;"
        is_valid, err = SemanticQueryValidator.validate_semantic_sql(unfiltered_sql, "stores in Chennai")
        self.assertFalse(is_valid)
        self.assertIn("Semantic filter missing", err)

    def test_valid_filter_sql_passes(self):
        """Valid SQL containing requested filter passes semantic check."""
        valid_sql = "SELECT DISTINCT store_name FROM stores WHERE location ILIKE '%Chennai%';"
        is_valid, err = SemanticQueryValidator.validate_semantic_sql(valid_sql, "stores in Chennai")
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_sub_intent_classification(self):
        """Test FastIntentRouter sub-intent classification."""
        route1 = FastIntentRouter.classify("fetch me medical stores in Chennai")
        self.assertEqual(route1["sub_intent"], "ENTITY_LOOKUP")

        route2 = FastIntentRouter.classify("show top 10 products by sales")
        self.assertEqual(route2["sub_intent"], "RANKING")

        route3 = FastIntentRouter.classify("monthly sales trend for 2026")
        self.assertEqual(route3["sub_intent"], "TREND")


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch, MagicMock
from app.ai.router import FastIntentRouter

class TestFastIntentRouter(unittest.TestCase):
    """Test suite for FastIntentRouter classification and routing rules."""

    def test_greeting_routing_no_llm(self):
        """Greetings should resolve as CONVERSATION and bypass LLM calls."""
        res_hi = FastIntentRouter.classify("hi")
        self.assertEqual(res_hi["intent"], "CONVERSATION")
        self.assertFalse(res_hi["requires_llm"])
        
        res_hello = FastIntentRouter.classify("hello")
        self.assertEqual(res_hello["intent"], "CONVERSATION")
        self.assertFalse(res_hello["requires_llm"])

    def test_thanks_routing_no_llm(self):
        """Thanks/acknowledgments should resolve as CONVERSATION and bypass LLM."""
        res = FastIntentRouter.classify("thanks")
        self.assertEqual(res["intent"], "CONVERSATION")
        self.assertFalse(res["requires_llm"])

    def test_ui_action_routing_no_llm(self):
        """UI navigation keywords should resolve as UI_ACTION and bypass LLM."""
        res = FastIntentRouter.classify("show dashboard")
        self.assertEqual(res["intent"], "UI_ACTION")
        self.assertEqual(res["ui_action"], "navigate_dashboard")
        self.assertFalse(res["requires_llm"])

        res_inv = FastIntentRouter.classify("go to inventory")
        self.assertEqual(res_inv["intent"], "UI_ACTION")
        self.assertEqual(res_inv["ui_action"], "navigate_inventory")

    def test_structured_query_routing(self):
        """Obvious database query queries should route to structured queries."""
        res = FastIntentRouter.classify("show sales figures for Laptop")
        self.assertEqual(res["intent"], "STRUCTURED_DATA_QUERY")
        self.assertTrue(res["requires_duckdb"])
        self.assertFalse(res["requires_chromadb"])

    def test_document_query_routing(self):
        """Obvious policy/document queries should route to documents."""
        res = FastIntentRouter.classify("what is our leave policy?")
        self.assertEqual(res["intent"], "DOCUMENT_KNOWLEDGE_QUERY")
        self.assertFalse(res["requires_duckdb"])
        self.assertTrue(res["requires_chromadb"])

    def test_hybrid_query_routing(self):
        """Queries referring to both database values and policies should route as hybrid."""
        res = FastIntentRouter.classify("Which customers exceeded their credit limit according to our credit policy?")
        self.assertEqual(res["intent"], "HYBRID_BUSINESS_QUERY")
        self.assertTrue(res["requires_duckdb"])
        self.assertTrue(res["requires_chromadb"])

    def test_analytics_query_routing(self):
        """Analytical 'why'/'compare' queries should route to analytics."""
        res = FastIntentRouter.classify("why did sales decline last month?")
        self.assertEqual(res["intent"], "ANALYTICS_QUERY")
        self.assertTrue(res["requires_duckdb"])

    @patch("app.ai.llm.client.ollama_client.generate")
    def test_llm_fallback_fallback(self, mock_generate):
        """Unknown or ambiguous queries should fall back to LLM intent classification."""
        mock_generate.return_value = '{"intent": "DOCUMENT_KNOWLEDGE_QUERY", "confidence": 0.88}'
        res = FastIntentRouter.classify("something extremely ambiguous and random")
        self.assertEqual(res["intent"], "DOCUMENT_KNOWLEDGE_QUERY")
        self.assertTrue(res["requires_chromadb"])
        mock_generate.assert_called_once()

if __name__ == "__main__":
    unittest.main()

import logging
import json
import re
from typing import Dict, Any, Optional
from app.ai.llm.client import ollama_client

logger = logging.getLogger("clarius.ai.router")

class FastIntentRouter:
    """
    Lightweight, extensible Intent Router.
    Implements a hybrid deterministic + LLM fallback classification strategy.
    """

    # Deterministic greetings & simple responses
    GREETINGS = {"hi", "hello", "hey", "hola", "greetings", "good morning", "good afternoon", "good evening"}
    THANKS = {"thanks", "thank you", "welcome", "awesome", "perfect"}

    # Keyword matrices
    DB_KEYWORDS = {
        "sales", "revenue", "inventory", "stock", "purchase", "customers", 
        "suppliers", "orders", "transactions", "profit", "expenses", "accounts", 
        "financial", "monthly", "quarterly", "yearly", "ledger", "invoice", "challan"
    }

    DOC_KEYWORDS = {
        "policy", "sop", "manual", "procedure", "guideline", "rules", 
        "documentation", "handbook", "contract", "terms", "policy handbook"
    }

    UI_KEYWORDS = {
        "show dashboard", "open dashboard", "go to inventory", "open reports", 
        "show sales page", "view branches", "show settings", "open settings",
        "navigate to", "open integration", "show data sources", "go to data sources"
    }

    ANALYTICS_KEYWORDS = {
        "why", "reason", "cause", "decline", "increase", "trend", "anomaly", 
        "underperforming", "performance", "compare", "growth", "prediction", "forecast"
    }

    @classmethod
    def classify(cls, query: str) -> Dict[str, Any]:
        """Classify user query and return routing decisions."""
        clean_q = query.strip().lower().rstrip("?.!")
        
        # 1. Conversation Classifier (Deterministic)
        if clean_q in cls.GREETINGS:
            return {
                "intent": "CONVERSATION",
                "confidence": 1.0,
                "requires_llm": False,
                "requires_duckdb": False,
                "requires_chromadb": False,
                "requires_ui_action": False,
                "response": "Hello! How can I help you analyze your business data today?"
            }
        if clean_q in cls.THANKS:
            return {
                "intent": "CONVERSATION",
                "confidence": 1.0,
                "requires_llm": False,
                "requires_duckdb": False,
                "requires_chromadb": False,
                "requires_ui_action": False,
                "response": "You're welcome."
            }

        # 2. UI Action Classifier (Deterministic)
        for keyword in cls.UI_KEYWORDS:
            if keyword in clean_q:
                # Resolve destination page
                dest = "dashboard"
                if "inventory" in clean_q:
                    dest = "inventory"
                elif "reports" in clean_q:
                    dest = "reports"
                elif "settings" in clean_q:
                    dest = "settings"
                elif "sources" in clean_q or "data sources" in clean_q:
                    dest = "sources"
                return {
                    "intent": "UI_ACTION",
                    "confidence": 1.0,
                    "requires_llm": False,
                    "requires_duckdb": False,
                    "requires_chromadb": False,
                    "requires_ui_action": True,
                    "ui_action": f"navigate_{dest}"
                }

        # Extract words for set operations
        words = set(re.findall(r"\w+", clean_q))

        # Check keyword intersections
        has_db = bool(words.intersection(cls.DB_KEYWORDS))
        has_doc = bool(words.intersection(cls.DOC_KEYWORDS))
        has_analytics = bool(words.intersection(cls.ANALYTICS_KEYWORDS))

        # 3. Hybrid Query Classifier (Deterministic)
        if has_db and has_doc:
            return {
                "intent": "HYBRID_BUSINESS_QUERY",
                "confidence": 0.9,
                "requires_llm": True,
                "requires_duckdb": True,
                "requires_chromadb": True,
                "requires_ui_action": False
            }

        # 4. Document Query Classifier (Deterministic)
        if has_doc and not has_db:
            return {
                "intent": "DOCUMENT_KNOWLEDGE_QUERY",
                "confidence": 0.9,
                "requires_llm": True,
                "requires_duckdb": False,
                "requires_chromadb": True,
                "requires_ui_action": False
            }

        # 5. Analytics Classifier (Deterministic)
        if has_analytics and has_db:
            return {
                "intent": "ANALYTICS_QUERY",
                "confidence": 0.85,
                "requires_llm": True,
                "requires_duckdb": True,
                "requires_chromadb": False,
                "requires_ui_action": False
            }

        # 6. Structured Query Classifier (Deterministic)
        if has_db and not has_analytics and not has_doc:
            return {
                "intent": "STRUCTURED_DATA_QUERY",
                "confidence": 0.9,
                "requires_llm": True,
                "requires_duckdb": True,
                "requires_chromadb": False,
                "requires_ui_action": False
            }

        # 7. LLM Fallback Classifier (Low Confidence/Ambiguous)
        logger.info(f"Deterministic routing uncertain for '{query}'. Invoking Qwen fallback classifier.")
        return cls._classify_via_llm(query)

    @classmethod
    def _classify_via_llm(cls, query: str) -> Dict[str, Any]:
        """Use local LLM to resolve ambiguous query intent."""
        system_prompt = (
            "You are the Fast Intent Router for CLARIUS. Classify the user query into exactly one category:\n"
            "Categories:\n"
            "- CONVERSATION: Simple greetings or thanks.\n"
            "- UI_ACTION: Commands to navigate screens/dashboards.\n"
            "- STRUCTURED_DATA_QUERY: Asking for numerical database lookups.\n"
            "- DOCUMENT_KNOWLEDGE_QUERY: Asking about policies, SOPs, or handbooks.\n"
            "- HYBRID_BUSINESS_QUERY: Requires both DB figures and policy rules.\n"
            "- ANALYTICS_QUERY: Requests trends, root-cause, decline or increase explanations.\n"
            "- UNKNOWN: Ambiguous inputs.\n\n"
            "Return ONLY a raw JSON block with fields: 'intent' and 'confidence'."
        )
        
        try:
            raw_response = ollama_client.generate(prompt=query, system_prompt=system_prompt)
            # Find JSON block
            json_match = re.search(r"\{.*?\}", raw_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                intent = data.get("intent", "UNKNOWN").upper()
                confidence = float(data.get("confidence", 0.5))
                
                requires_llm = intent not in {"CONVERSATION", "UI_ACTION"}
                requires_duckdb = intent in {"STRUCTURED_DATA_QUERY", "HYBRID_BUSINESS_QUERY", "ANALYTICS_QUERY"}
                requires_chromadb = intent in {"DOCUMENT_KNOWLEDGE_QUERY", "HYBRID_BUSINESS_QUERY"}
                
                return {
                    "intent": intent,
                    "confidence": confidence,
                    "requires_llm": requires_llm,
                    "requires_duckdb": requires_duckdb,
                    "requires_chromadb": requires_chromadb,
                    "requires_ui_action": intent == "UI_ACTION"
                }
        except Exception as e:
            logger.error(f"LLM Fallback classification failed: {str(e)}")
            
        # Safe fallback
        return {
            "intent": "UNKNOWN",
            "confidence": 0.0,
            "requires_llm": True,
            "requires_duckdb": True,
            "requires_chromadb": True,
            "requires_ui_action": False
        }

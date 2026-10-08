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
        "sales", "sale", "sell", "sold", "selling", "revenue", "inventory", "stock", "purchase", "purchases",
        "customer", "customers", "supplier", "suppliers", "order", "orders", "transaction", "transactions",
        "profit", "expenses", "expense", "account", "accounts", "financial", "monthly", "quarterly", "yearly",
        "quarter", "q1", "q2", "q3", "q4", "ledger", "invoice", "invoices", "challan", "product", "products",
        "item", "items", "unit", "units", "quantity", "amount", "price", "cost", "discount", "discounts",
        "rebate", "rebates", "delivery", "deliveries", "receipt", "receipts", "return", "returns", "credit",
        "margin", "margins", "growth", "buyer", "rep", "salesperson", "vendor", "vendors", "branch", "branches",
        "store", "stores", "employee", "employees", "performance", "billing", "bill", "bills", "paid", "unpaid",
        "overdue", "due", "sku", "skus", "brand", "brands", "category", "categories"
    }

    DOC_KEYWORDS = {
        "policy", "sop", "manual", "procedure", "guideline", "rules", 
        "documentation", "handbook", "contract", "terms", "policy handbook",
        "ifsc", "gstin", "pan", "cin", "bank", "profile", "handbook", "address"
    }

    DOC_PHRASES = [
        "ifsc", "ifsc code", "bank account", "bank details", "swift code", "micr",
        "gstin", "pan number", "company profile", "company address", "registered address",
        "company info", "our address", "our phone", "our email", "our website",
        "our contact", "our bank", "bank name", "account number", "account details"
    ]

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

        # Check keyword & phrase intersections
        has_doc = bool(words.intersection(cls.DOC_KEYWORDS)) or any(phrase in clean_q for phrase in cls.DOC_PHRASES)
        has_db = bool(words.intersection(cls.DB_KEYWORDS))
        has_analytics = bool(words.intersection(cls.ANALYTICS_KEYWORDS))

        # If query matches company profile / document phrases (e.g. "ifsc code"), prioritize document knowledge over DB
        if any(phrase in clean_q for phrase in cls.DOC_PHRASES):
            has_db = False

        # Check if query is asking for policy documents (e.g. "return policy", "credit policy") without explicit numerical metrics
        has_data_metrics = any(kw in clean_q for kw in [
            "how much", "how many", "total", "sum", "average", "avg", "count", "exceeded", "limit",
            "revenue figure", "sales figure", "amount", "figures", "records", "transaction", "transactions",
            "units", "quantity", "profit margin", "quarterly sales", "monthly sales", "highest", "lowest", "top "
        ])

        # 3. Hybrid Query Classifier (Deterministic)
        if has_db and has_doc and has_data_metrics:
            return {
                "intent": "HYBRID_BUSINESS_QUERY",
                "sub_intent": cls.resolve_sub_intent(clean_q, "HYBRID_BUSINESS_QUERY"),
                "confidence": 0.9,
                "requires_llm": True,
                "requires_duckdb": True,
                "requires_chromadb": True,
                "requires_ui_action": False
            }

        # 4. Document Query Classifier (Deterministic)
        if has_doc and (not has_db or not has_data_metrics):
            return {
                "intent": "DOCUMENT_KNOWLEDGE_QUERY",
                "sub_intent": "DOCUMENT_RESPONSE",
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
                "sub_intent": cls.resolve_sub_intent(clean_q, "ANALYTICS_QUERY"),
                "confidence": 0.85,
                "requires_llm": True,
                "requires_duckdb": True,
                "requires_chromadb": False,
                "requires_ui_action": False
            }

        # 6. Structured Query Classifier (Deterministic)
        if has_db or has_data_metrics:
            return {
                "intent": "STRUCTURED_DATA_QUERY",
                "sub_intent": cls.resolve_sub_intent(clean_q, "STRUCTURED_DATA_QUERY"),
                "confidence": 0.9,
                "requires_llm": True,
                "requires_duckdb": True,
                "requires_chromadb": False,
                "requires_ui_action": False
            }

        # 7. LLM Fallback Classifier (Low Confidence/Ambiguous)
        logger.info(f"Deterministic routing uncertain for '{query}'. Invoking Qwen fallback classifier.")
        res = cls._classify_via_llm(query)
        if "sub_intent" not in res:
            res["sub_intent"] = cls.resolve_sub_intent(clean_q, res.get("intent", "STRUCTURED_DATA_QUERY"))
        return res

    @classmethod
    def resolve_sub_intent(cls, query: str, intent: str) -> str:
        """Dynamically resolve semantic sub-intent (ENTITY_LOOKUP, AGGREGATION, RANKING, TREND, RECORD_DETAIL, etc.)."""
        q_lower = query.strip().lower()

        if intent in {"CONVERSATION", "UI_ACTION"}:
            return "CONVERSATIONAL"
        if intent == "DOCUMENT_KNOWLEDGE_QUERY":
            return "DOCUMENT_RESPONSE"

        if any(kw in q_lower for kw in ["trend", "over time", "monthly", "yearly", "daily", "quarterly"]):
            return "TREND"
        if any(kw in q_lower for kw in ["top ", "best ", "worst ", "highest ", "lowest ", "ranking"]):
            return "RANKING"
        if any(kw in q_lower for kw in ["compare", "versus", "vs "]):
            return "COMPARISON"
        if any(kw in q_lower for kw in ["distribution", "breakdown", "proportion", "share"]):
            return "DISTRIBUTION"
        if any(kw in q_lower for kw in ["total", "sum", "average", "avg", "count", "how many", "revenue by", "sales by", "amount by"]):
            return "AGGREGATION"
        if any(kw in q_lower for kw in ["details of", "information for", "show detail", "invoice "]):
            return "RECORD_DETAIL"
        if any(kw in q_lower for kw in ["fetch", "find", "list", "show", "get", "which", "available", "where", "store", "customer", "supplier", "employee", "branch"]):
            return "ENTITY_LOOKUP"

        return "ENTITY_LOOKUP"

    @classmethod
    def _classify_via_llm(cls, query: str) -> Dict[str, Any]:
        """Use local LLM to resolve ambiguous query intent."""
        system_prompt = (
            "You are the Fast Intent Router for CLARIUS. Classify the user query into exactly one category:\n"
            "Categories:\n"
            "- CONVERSATION: Simple greetings or thanks.\n"
            "- UI_ACTION: Commands to navigate screens/dashboards.\n"
            "- STRUCTURED_DATA_QUERY: Asking for numerical database lookups, sales, product metrics, revenue, inventory.\n"
            "- DOCUMENT_KNOWLEDGE_QUERY: Asking about company policies, SOPs, rules, or handbooks.\n"
            "- HYBRID_BUSINESS_QUERY: Requires both DB figures and policy rules.\n"
            "- ANALYTICS_QUERY: Requests trends, root-cause, decline or increase explanations.\n"
            "- UNKNOWN: Ambiguous inputs.\n\n"
            "Return ONLY a raw JSON block with fields: 'intent' and 'confidence'."
        )
        
        try:
            raw_response = ollama_client.generate(prompt=query, system_prompt=system_prompt, purpose="intent classification")
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
            
        # Safe fallback: default to structured query if database keywords match, otherwise UNKNOWN without ChromaDB
        words = set(re.findall(r"\w+", query.lower()))
        has_db_words = bool(words.intersection(cls.DB_KEYWORDS))
        fallback_intent = "STRUCTURED_DATA_QUERY" if has_db_words else "UNKNOWN"
        return {
            "intent": fallback_intent,
            "confidence": 0.5 if has_db_words else 0.0,
            "requires_llm": True,
            "requires_duckdb": True,
            "requires_chromadb": False,
            "requires_ui_action": False
        }

"""
CLARIUS Backend - Document Classifier

This module automatically classifies uploaded company documents, policies, invoices,
contracts, technical manuals, and market research into canonical knowledge categories.
"""

import re
from typing import Dict, Any, Tuple, Optional

# Canonical Category Definitions
CATEGORY_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "hr": {
        "id": "hr",
        "name": "HR & Payroll Policies",
        "aliases": ["hr", "payroll", "human_resources", "people"],
        "description": "Employee guidelines, payroll structures, benefits, onboarding manuals",
        "icon": "users",
        "color": "from-blue-500 to-indigo-600",
        "keywords": [
            "hr", "human resource", "human resources", "payroll", "salary", "salaries", "wage", "wages",
            "employee", "employees", "employment", "staff", "workforce", "benefits", "onboarding",
            "handbook", "leave", "leaves", "vacation", "sick leave", "casual leave", "bonus", "bonuses",
            "compensation", "attendance", "recruitment", "recruiting", "hiring", "interview", "interviews",
            "performance review", "appraisal", "promotion", "termination", "resignation", "workplace",
            "code of conduct", "dress code", "maternity", "paternity", "health insurance", "medical allowance",
            "gratuity", "provident fund", "pf", "esi", "timesheet", "overtime", "perks", "relocation",
            "job description", "offer letter", "experience letter", "relieving letter", "probation"
        ]
    },
    "finance": {
        "id": "finance",
        "name": "Finance & Invoices",
        "aliases": ["finance", "financial", "invoices", "invoice", "accounting"],
        "description": "Quarterly balance sheets, audit reports, tax filings, vendor invoices",
        "icon": "file-spreadsheet",
        "color": "from-emerald-500 to-teal-600",
        "keywords": [
            "finance", "financial", "financials", "invoice", "invoices", "bill", "bills", "billing",
            "balance sheet", "audit", "audits", "auditing", "tax", "taxes", "taxation", "tax filing",
            "quarterly", "q1", "q2", "q3", "q4", "annual report", "fiscal year", "revenue", "expense",
            "expenses", "ledger", "general ledger", "accounting", "p&l", "profit and loss", "profit & loss",
            "ebitda", "gross margin", "net margin", "budget", "budgeting", "forecast", "cash flow",
            "receipt", "receipts", "vendor invoice", "customer invoice", "accounts payable", "accounts receivable",
            "vat", "gst", "tds", "depreciation", "amortization", "reconciliation", "bank statement",
            "payment receipt", "wire transfer", "purchase order", "po number", "credit note", "debit note"
        ]
    },
    "policy": {
        "id": "policy",
        "name": "Corporate Governance & Compliance",
        "aliases": ["policy", "policies", "governance", "compliance", "legal"],
        "description": "Security compliance, ISO standards, NDA templates, legal disclaimers",
        "icon": "shield",
        "color": "from-amber-500 to-orange-600",
        "keywords": [
            "governance", "corporate governance", "compliance", "security compliance", "iso", "iso 27001",
            "iso 9001", "iso 14001", "standard", "standards", "gdpr", "hipaa", "soc2", "soc 2",
            "privacy", "privacy policy", "disclaimer", "disclaimers", "legal disclaimer", "regulation",
            "regulatory", "whistleblower", "board of directors", "risk management", "policy", "policies",
            "statutory", "ethics", "anti-bribery", "anti-corruption", "sanctions", "data protection",
            "nda template", "confidentiality policy", "information security", "infosec", "acceptable use policy",
            "by-laws", "bylaws", "corporate charter", "compliance audit", "regulatory compliance"
        ]
    },
    "sop": {
        "id": "sop",
        "name": "Technical Manuals & Standard Operating Procedures",
        "aliases": ["sop", "manuals", "manual", "technical", "engineering", "specs"],
        "description": "Engineering specs, IT operations, API specs, hardware setup",
        "icon": "book-open",
        "color": "from-cyan-500 to-blue-600",
        "keywords": [
            "sop", "sops", "standard operating procedure", "operating procedure", "standard operating procedures",
            "manual", "manuals", "technical manual", "user manual", "guide", "user guide", "guidelines",
            "specification", "specifications", "specs", "architecture", "system architecture", "api", "apis",
            "endpoint", "endpoints", "hardware", "hardware setup", "setup guide", "installation",
            "engineering", "deployment", "deploying", "it operations", "infrastructure", "maintenance",
            "troubleshooting", "runbook", "playbook", "technical", "configuration", "system design",
            "codebase", "workflow", "protocol", "devops", "ci/cd", "network", "server setup", "database schema"
        ]
    },
    "contract": {
        "id": "contract",
        "name": "Vendor & Customer Contracts",
        "aliases": ["contract", "contracts", "agreement", "agreements"],
        "description": "Service level agreements, master supply agreements, NDAs",
        "icon": "file-text",
        "color": "from-purple-500 to-pink-600",
        "keywords": [
            "contract", "contracts", "agreement", "agreements", "sla", "service level agreement",
            "master supply agreement", "msa", "master service agreement", "nda", "non-disclosure agreement",
            "non disclosure agreement", "vendor agreement", "customer contract", "client agreement",
            "procurement", "lease agreement", "terms of service", "terms and conditions", "partnership agreement",
            "purchase agreement", "legal agreement", "statement of work", "sow", "subcontractor",
            "parties hereby agree", "effective date", "counterparts", "indemnification", "severability",
            "governing law", "jurisdiction", "termination clause", "confidentiality agreement"
        ]
    },
    "research": {
        "id": "research",
        "name": "Market & Product Research",
        "aliases": ["research", "market", "marketing", "product_research", "insights"],
        "description": "Competitive intelligence, user study reports, industry analysis",
        "icon": "compass",
        "color": "from-rose-500 to-red-600",
        "keywords": [
            "market", "markets", "market research", "research", "competitive intelligence", "competitive",
            "competitor", "competitors", "user study", "user research", "customer study", "customer research",
            "industry analysis", "industry", "analysis", "benchmark", "benchmarking", "survey", "surveys",
            "trends", "market trends", "product roadmap", "roadmap", "market share", "interview report",
            "persona", "personas", "tam", "sam", "som", "swot", "swot analysis", "insights",
            "market opportunity", "customer feedback", "user feedback", "focus group", "consumer sentiment",
            "market size", "growth rate", "cagr", "industry forecast", "competitive landscape"
        ]
    }
}


def normalize_category_id(cat_input: Optional[str]) -> str:
    """Normalize user input or legacy category ID to one of the 6 canonical IDs."""
    if not cat_input:
        return "policy"
    
    clean = cat_input.lower().strip().replace(" ", "_").replace("&", "").replace("-", "_")
    
    for canon_id, defs in CATEGORY_DEFINITIONS.items():
        if clean == canon_id or clean in defs["aliases"]:
            return canon_id
        if defs["name"].lower().replace(" ", "_") in clean or clean in defs["name"].lower().replace(" ", "_"):
            return canon_id
            
    return "policy"


def classify_document(title: str, content: str, filename: Optional[str] = None) -> Tuple[str, float, str]:
    """
    Classify a document into one of the 6 categories based on title, filename, and extracted content.
    Returns: (canonical_category_id, confidence_score, rationale)
    """
    text_to_analyze = f"{title or ''} {filename or ''} {content[:4000]}".lower()
    title_text = f"{title or ''} {filename or ''}".lower()
    
    scores: Dict[str, float] = {cat: 0.0 for cat in CATEGORY_DEFINITIONS}
    matched_terms: Dict[str, list] = {cat: [] for cat in CATEGORY_DEFINITIONS}
    
    for cat_id, cat_info in CATEGORY_DEFINITIONS.items():
        for kw in cat_info["keywords"]:
            # Title & filename matches are heavily weighted (5x)
            if re.search(r'\b' + re.escape(kw) + r'\b', title_text):
                scores[cat_id] += 5.0
                matched_terms[cat_id].append(f"title:{kw}")
            
            # Content matches
            count = len(re.findall(r'\b' + re.escape(kw) + r'\b', text_to_analyze))
            if count > 0:
                scores[cat_id] += min(count * 1.0, 10.0) # cap per keyword
                matched_terms[cat_id].append(kw)

    best_cat = max(scores, key=scores.get)
    max_score = scores[best_cat]
    
    if max_score > 0:
        total_score = sum(scores.values())
        confidence = min(0.99, round(max_score / (total_score + 0.01), 2))
        top_matches = ", ".join(matched_terms[best_cat][:4])
        rationale = f"Matched keywords ({top_matches}) with score {max_score:.1f}"
    else:
        # Default fallback
        best_cat = "policy"
        confidence = 0.60
        rationale = "Defaulted to Corporate Governance & Compliance (no strong keyword matches)"
        
    return best_cat, confidence, rationale

import re
from typing import List, Dict, Any, Optional

# Predefined standard categories with keyword heuristics
CATEGORY_KEYWORDS = {
    "Security & Compliance": [
        "security", "compliance", "soc", "iso", "hipaa", "gdpr", "audit", "encryption",
        "vulnerability", "penetration", "access control", "authentication", "sso", "mfa",
        "data protection", "privacy", "cve", "cyber"
    ],
    "Technical Architecture & Infrastructure": [
        "architecture", "infrastructure", "cloud", "aws", "azure", "gcp", "hosting",
        "database", "api", "integration", "scalability", "server", "docker", "kubernetes",
        "latency", "bandwidth", "devops", "ci/cd", "deployment"
    ],
    "Pricing & Commercials": [
        "pricing", "price", "cost", "commercial", "payment", "fee", "rate", "licensing",
        "license", "billing", "discount", "subscription", "contract", "terms"
    ],
    "Support & SLA": [
        "sla", "service level", "support", "maintenance", "ticket", "uptime", "downtime",
        "incident", "response time", "resolution time", "24/7", "business hours", "escalation"
    ],
    "Company & Experience": [
        "company", "experience", "reference", "case study", "customer", "client", "about us",
        "history", "founded", "qualification", "team", "organization", "staff", "management"
    ],
}


def classify_question(text: str) -> str:
    """
    Classify a question into standard RFP categories based on keyword frequency.
    Defaults to 'General' if no strong category signal is detected.
    """
    text_lower = text.lower()
    matched_scores: Dict[str, int] = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", text_lower))
        if score > 0:
            matched_scores[category] = score

    if not matched_scores:
        return "General"

    # Return category with highest match count
    return max(matched_scores.items(), key=lambda item: item[1])[0]

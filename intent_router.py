import re
import logging

logger = logging.getLogger(__name__)


# Keyword → weight pairs per intent.  Higher total weight wins.
_INTENT_KEYWORDS: dict[str, list[tuple[str, int]]] = {
    "dealer_ranking": [
        ("top dealers", 3), ("best customers", 3), ("highest sales", 3),
        ("loyal account", 2), ("largest", 2), ("who orders frequently", 2),
        ("key account", 2), ("important", 1), ("big spender", 2),
    ],
    "dormant_dealers": [
        ("dormant", 3), ("not placed", 3), ("not ordered", 3),
        ("has not placed an order", 3), ("inactive", 2),
        ("last 15", 2), ("last 30", 2), ("last 45", 2), ("last 60", 2),
        ("no order", 2), ("abandoned", 2),
    ],
    "slowing_dealers": [
        ("slowed down", 3), ("slowing", 3), ("weakening", 3),
        ("reduced ordering", 3), ("dropped", 2), ("declining", 2),
        ("used to buy", 3), ("buying less", 2),
    ],
    "status_follow_up": [
        ("problematic", 3), ("stuck", 3), ("status", 2),
        ("cancelled", 2), ("disputed", 2), ("on hold", 2),
        ("in process", 2), ("follow-up", 3), ("follow up", 3),
        ("non-completed", 3), ("blocked", 2),
    ],
    "territory_performance": [
        ("territory", 3), ("region", 3), ("state", 2),
        ("city", 2), ("country", 2), ("geography", 2),
    ],
    "product_analysis": [
        ("product line", 3), ("product lines", 3), ("product", 2),
        ("sell the most", 2), ("sold more", 2), ("strongest product", 2),
        ("weakest product", 2),
    ],
    "time_trend": [
        ("month", 2), ("quarter", 2), ("year", 1),
        ("peak buying", 3), ("cycle", 1), ("this month", 3),
        ("last month", 3), ("trend", 2), ("seasonal", 2),
    ],
    "contact_lookup": [
        ("contact", 3), ("phone", 3), ("call", 2),
        ("reach", 2), ("contact info", 3), ("phone number", 3),
        ("dealer info", 2), ("details for", 2),
    ],
}


class IntentRouter:
    """Classifies user queries into analytical intent groups using
    weighted keyword scoring with regex parameter extraction."""

    def __init__(self):
        self.keywords = _INTENT_KEYWORDS

    def route_intent(self, question: str) -> str:
        """Returns the highest-scoring intent for the given question."""
        q = question.lower()
        scores: dict[str, int] = {}

        for intent, pairs in self.keywords.items():
            total = sum(weight for kw, weight in pairs if kw in q)
            if total > 0:
                scores[intent] = total

        if not scores:
            logger.info("No keyword match for query — defaulting to dealer_ranking")
            return "dealer_ranking"

        best = max(scores, key=scores.get)  # type: ignore[arg-type]
        logger.info("Intent scores: %s → selected '%s'", scores, best)
        return best

    @staticmethod
    def extract_dormant_days(question: str, default: int = 15) -> int:
        """Pulls a numeric threshold from queries like 'last 30 days'."""
        m = re.search(r"(?:last|past|over)\s+(\d{1,3})\s*(?:days?)?", question.lower())
        if m:
            return int(m.group(1))
        return default

    @staticmethod
    def extract_dealer_name(question: str) -> str | None:
        """Tries to extract a dealer name from the user query.
        Looks for quoted names or names after 'for' / 'about'."""
        # Quoted name
        m = re.search(r'["\']([^"\']+)["\']', question)
        if m:
            return m.group(1).strip()
        # After "for" or "about"
        m = re.search(r"(?:for|about)\s+(.+?)(?:\?|$)", question, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return None

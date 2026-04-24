import re
import logging

logger = logging.getLogger(__name__)

# Keyword → weight pairs per intent family for BDO Assistant
_INTENT_KEYWORDS: dict[str, list[tuple[str, int]]] = {
    "contract": [
        ("contract", 3), ("sauda", 3), ("live", 2),
        ("pending quantity", 4), ("pending qty", 4), ("high pending", 4),
        ("expiring", 4), ("expiry", 4), ("aging", 4), ("near expiry", 4),
        ("days left", 2), ("validity", 2), ("how many contracts", 4),
        ("active contract", 4), ("all contracts", 3),
        ("urgent follow-up", 3), ("urgent followup", 3),
        ("close to expiry", 4), ("more quantity", 3),
    ],
    "dispatch": [
        ("delivery", 3), ("dispatch", 3), ("arriving", 3),
        ("open do", 4), ("receiving", 2), ("scheduled", 2),
        ("material arriving", 4), ("product arriving", 4),
        ("delivered today", 4), ("material today", 4),
        ("customer will receive", 4), ("receiving material", 3),
        ("call today to push", 4), ("push dispatch", 4),
        ("products should", 3), ("inform about today", 3),
    ],
    "new_business": [
        ("new sauda", 4), ("no business", 3),
        ("nudge", 2), ("new business", 3),
        ("not in open do", 3), ("not in pending", 3),
        ("create a new sauda", 4), ("call for new", 3),
    ],
    "dormant": [
        ("dormant", 5), ("inactive", 3), ("sleeping", 3), ("no order", 3),
        ("not ordering", 3), ("idle", 3), ("zero business", 3),
        ("master file but not", 4), ("in master but not", 4),
        ("no active sauda", 4),
    ],
    "active_dealers": [
        ("active dealer", 5), ("active customer", 4), ("who is active", 4),
        ("currently active", 4), ("active accounts", 4),
    ],
    "collection": [
        ("collection", 5), ("collected", 4), ("payment", 4), ("pending payment", 5),
        ("outstanding", 4), ("yet to be collected", 5), ("received revenue", 4),
        ("amount collected", 4), ("receivable", 3), ("follow up.*payment", 4),
    ],
    "pricing": [
        ("price", 3), ("rate", 3), ("guidance", 4), ("oil type", 2),
        ("mean", 3), ("median", 3), ("minimum", 3), ("maximum", 3),
        ("highest", 3), ("lowest", 3), ("average", 3),
        ("basic rate", 4), ("negotiation", 3),
        ("sunflower", 2), ("mustard", 2), ("soya", 2), ("palm", 2),
        ("vanaspati", 2), ("rasoi", 2), ("bib", 2),
        ("outlier", 5), ("outlier pricing", 5),
        ("signing new contract", 4), ("new contract", 3),
        ("rate range", 4), ("rate guidance", 5),
    ],
    "daily_actions": [
        ("actions", 3), ("top 5", 4), ("top five", 4),
        ("best actions", 4), ("5 tasks", 4), ("five tasks", 4),
        ("prioritized", 3), ("nba", 3), ("next best", 4),
        ("what should i do", 4), ("call today", 2),
        ("tasks for today", 4), ("actions for today", 4),
    ],
}

class IntentRouter:
    """Classifies user queries into BDO analytical intent families."""

    def __init__(self):
        self.keywords = _INTENT_KEYWORDS

    def route_intent(self, question: str) -> dict:
        """Returns the highest-scoring intent and extracted metadata."""
        q = question.lower()
        scores: dict[str, int] = {}

        for family, pairs in self.keywords.items():
            total = sum(weight for kw, weight in pairs if kw in q)
            if total > 0:
                scores[family] = total

        if not scores:
            logger.info("No keyword match for query — defaulting to contract")
            selected_family = "contract"
        else:
            selected_family = max(scores, key=scores.get)
            
        metadata = self._extract_metadata(q, selected_family)
        return {"family": selected_family, "metadata": metadata}

    def _extract_metadata(self, q: str, family: str) -> dict:
        metadata = {}
        
        # Extract oil type if pricing
        if family == "pricing":
            oil_match = re.search(r"(sunflower|mustard|soya|palm|rice|groundnut|vanaspati|rasoi)", q)
            if oil_match:
                metadata["oil_type"] = oil_match.group(1)
        
        # Extract subtypes
        if "expiring" in q or "expiry" in q or "near" in q or "close to" in q:
            metadata["subtype"] = "expiring"
        elif "aging" in q or "ageing" in q:
            metadata["subtype"] = "aging"
        elif "active" in q and family == "contract":
            metadata["subtype"] = "active"
        elif "today" in q and family == "dispatch":
            metadata["subtype"] = "today"
        elif "high" in q and "pending" in q:
            metadata["subtype"] = "high_pending"
        elif "pending" in q and "quantity" in q:
            metadata["subtype"] = "high_pending"
        elif "pending" in q and "qty" in q:
            metadata["subtype"] = "high_pending"
            
        return metadata

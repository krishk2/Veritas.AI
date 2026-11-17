from typing import List, Dict, Any, Tuple, Optional
from veritas.core.interfaces import ICredibilityEvaluator

class RuleBasedCredibilityEvaluator:
    """Configurable domain allowlist/blocklist credibility evaluator."""
    
    def __init__(
        self,
        trusted_domains: Optional[List[str]] = None,
        questionable_domains: Optional[List[str]] = None,
        trusted_bonus: float = 0.10,
        questionable_penalty: float = 0.20
    ):
        self.trusted_domains = trusted_domains or [
            "science-journal.org",
            "reuters.com",
            "bbc.com",
            "apnews.com",
            "nature.com",
            "who.int",
            "cdc.gov",
            "nih.gov"
        ]
        self.questionable_domains = questionable_domains or [
            "conspiracy-news.net",
            "clickbait.com",
            "infowars.com",
            "naturalnews.com"
        ]
        self.trusted_bonus = trusted_bonus
        self.questionable_penalty = questionable_penalty

    def evaluate(
        self,
        sources: List[Dict[str, Any]],
        base_confidence: float
    ) -> Tuple[float, List[Dict[str, Any]]]:
        score_adjustment = 0.0
        credibility_report = []

        for source in (sources or []):
            url = source.get("url", "")
            if not url:
                continue

            domain = url.split("//")[-1].split("/")[0].lower()
            status = "Neutral"

            if any(trusted in domain for trusted in self.trusted_domains):
                score_adjustment += self.trusted_bonus
                status = "Trusted"
            elif any(questionable in domain for questionable in self.questionable_domains):
                score_adjustment -= self.questionable_penalty
                status = "Questionable"

            credibility_report.append({
                "domain": domain,
                "url": url,
                "status": status
            })

        adjusted_confidence = min(max(base_confidence + score_adjustment, 0.0), 1.0)
        return adjusted_confidence, credibility_report

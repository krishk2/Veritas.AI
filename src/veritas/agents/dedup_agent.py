from typing import Dict, Any
from veritas.core.state import AgentState
from veritas.core.container import container

def dedup_agent(state: AgentState) -> Dict[str, Any]:
    """
    DedupAgent: Normalizes raw claim queries into canonical declarative statements,
    and queries the semantic index for recurring or pre-verified claims (similarity >= 0.85).
    """
    print("---DedupAgent---")
    raw_claim = state.get("claim", "")
    dedup_service = container.get_claim_dedup_service()

    # 1. Normalize claim to strip clickbait framing, hashtags, and interrogative noise
    canonical = dedup_service.normalize_claim(raw_claim)
    if not canonical:
        canonical = raw_claim

    print(f"Normalized claim: '{raw_claim}' -> '{canonical}'")

    # 2. Check semantic similarity index for past verified claims
    match = dedup_service.find_duplicate(canonical, threshold=0.85)

    if match:
        sim = match.get("similarity", 1.0)
        print(f"[CACHE HIT] Duplicate matched (Similarity: {sim}, Exact: {match.get('is_exact_match')}): '{match['canonical_claim']}'")
        
        result = {
            "canonical_claim": canonical,
            "is_duplicate": True,
            "duplicate_match": match,
            "verdict": match.get("verdict", "VERIFIED"),
            "confidence": match.get("confidence", 0.95),
            "adjusted_confidence": match.get("confidence", 0.95),
            "explanation": f"[⚡ Cache Hit - Verified Claim {match['record_id']}] {match.get('explanation', '')}",
            "is_duplicate_of": match["record_id"],
            "sources": match.get("sources", []),
            "evidence": match.get("evidence", [])
        }
        return result

    print("[NEW CLAIM] No prior duplicate found. Proceeding with fresh verification.")
    return {
        "canonical_claim": canonical,
        "is_duplicate": False,
        "duplicate_match": None
    }

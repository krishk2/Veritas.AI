import uuid
import logging
from typing import Dict, Any
from veritas.core.state import AgentState
from veritas.core.container import container

logger = logging.getLogger("veritas.ledger_agent")

def ledger_agent(state: AgentState) -> Dict[str, Any]:
    """
    LedgerAgent: Synchronously writes verification results via ILedgerRepository
    and syncs the Trace-the-Source graph via IGraphRepository.
    """
    print("---LedgerAgent: Dual-Layer Persistence---")
    
    claim = state["claim"]
    verdict = state.get("verdict", "UNCLEAR")
    raw_confidence = state.get("confidence", 0.0)
    adjusted_confidence = state.get("adjusted_confidence", raw_confidence)
    explanation = state.get("explanation", "No explanation provided.")
    evidence = state.get("evidence", [])
    credibility_report = state.get("credibility_report", [])
    sources = state.get("sources", [])
    has_image = bool(state.get("image_base64") or state.get("image_url"))
    
    # 1. Human-in-the-Loop review threshold check
    if adjusted_confidence < 0.65 or verdict == "UNCLEAR":
        status = "PENDING_HUMAN_REVIEW"
    else:
        status = "VERIFIED"
        
    canonical_claim = state.get("canonical_claim") or claim
    is_duplicate_of = state.get("is_duplicate_of")

    # If it is an indexed duplicate, bypass all database writes and re-embedding!
    if is_duplicate_of or state.get("is_duplicate"):
        print(f"  [CACHE FAST-PATH] Claim is a verified duplicate of {is_duplicate_of or 'cache'}. Zero DB/LLM calls.")
        return {
            "record_id": is_duplicate_of or state.get("record_id", "cached"),
            "status": status
        }

    record_id = state.get("record_id") or str(uuid.uuid4())

    # 2. Persist to Relational Truth Ledger via ILedgerRepository
    ledger_repo = container.get_ledger_repository()
    try:
        saved_record = ledger_repo.save_claim(
            claim=claim,
            verdict=verdict,
            confidence=raw_confidence,
            adjusted_confidence=adjusted_confidence,
            explanation=explanation,
            status=status,
            evidence=evidence,
            credibility_report=credibility_report,
            has_image=has_image,
            record_id=record_id,
            canonical_claim=canonical_claim,
            is_duplicate_of=is_duplicate_of
        )
        print(f"  [DB] Saved to Truth Ledger: ID={saved_record.id} Status={status}")
    except Exception as e:
        logger.error(f"Failed to persist claim to Relational DB: {e}")
        print(f"  [DB Error] {e}")

    # 3. Persist to Trace-the-Source Graph via IGraphRepository
    graph_repo = container.get_graph_repository()
    if not is_duplicate_of:
        try:
            neo4j_success = graph_repo.record_provenance(
                claim_id=record_id,
                claim=claim,
                verdict=verdict,
                confidence=adjusted_confidence,
                status=status,
                sources=sources,
                evidence=evidence,
                credibility_report=credibility_report
            )
            if neo4j_success:
                print(f"  [Neo4j] Provenance graph synced.")
            else:
                print(f"  [Neo4j] Graph sync bypassed (instance offline or credentials not set).")
        except Exception as e:
            logger.warning(f"Neo4j persistence bypassed: {e}")

    # 4. Index in Semantic Deduplication Engine with full sources & evidence hydration
    try:
        canonical_claim = state.get("canonical_claim") or claim
        dedup_service = container.get_claim_dedup_service()
        dedup_service.index_claim(
            record_id=record_id,
            canonical_claim=canonical_claim,
            verdict=verdict,
            confidence=adjusted_confidence,
            explanation=explanation,
            sources=sources,
            evidence=evidence
        )
    except Exception as e:
        logger.warning(f"Semantic claim indexing bypassed: {e}")

    return {
        "record_id": record_id,
        "status": status
    }
